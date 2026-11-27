"""Database management with foreign keys, integrity checks, and corruption recovery."""

import datetime
import shutil
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path

SQLITE_HEADER = b"SQLite format 3\x00"


class DatabaseError(Exception):
    """Base exception for database failures."""

    pass


class DatabaseCorruptionError(DatabaseError):
    """Raised when a database file is corrupt, truncated, or unrecoverable."""

    pass


class DatabaseVersionMismatchError(DatabaseError):
    """Raised when the database schema user_version does not match expected version."""

    pass


def check_db_file_integrity(db_path: Path) -> tuple[bool, str]:
    """Inspect database file header and run PRAGMA quick_check."""
    if not db_path.exists():
        return False, "File does not exist"

    if db_path.stat().st_size < 100:
        return False, (
            f"File is truncated ({db_path.stat().st_size} bytes, minimum header is 100 bytes)"
        )

    try:
        with open(db_path, "rb") as f:
            header = f.read(16)
            if header != SQLITE_HEADER:
                return False, f"Invalid SQLite header: {header!r}"
    except OSError as err:
        return False, f"Cannot read file: {err}"

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("PRAGMA quick_check;")
        rows = cursor.fetchall()
        if not rows or rows[0][0] != "ok":
            return False, f"PRAGMA quick_check reported errors: {rows}"
        return True, "ok"
    except (sqlite3.Error, OSError) as err:
        return False, f"Integrity check exception: {err}"
    finally:
        if conn is not None:
            conn.close()


def create_backup_file(source_db_path: Path, target_bak_path: Path) -> None:
    """Safely back up a database using sqlite3 backup API."""
    src_conn = sqlite3.connect(str(source_db_path))
    target_bak_path.parent.mkdir(parents=True, exist_ok=True)
    temp_bak_path = target_bak_path.with_suffix(".tmp_bak")
    dst_conn = sqlite3.connect(str(temp_bak_path))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        temp_bak_path.replace(target_bak_path)
    except (sqlite3.Error, OSError) as err:
        if temp_bak_path.exists():
            temp_bak_path.unlink()
        raise DatabaseError(f"Backup failed: {err}") from err
    finally:
        with suppress(sqlite3.Error):
            src_conn.close()
        with suppress(sqlite3.Error):
            dst_conn.close()


class DatabaseManager:
    """Manages SQLite connections, migrations, PRAGMAs, and corruption safeguards."""

    def __init__(
        self,
        db_path: Path | str,
        schema_sql: str,
        expected_user_version: int,
        auto_restore_backup: bool = True,
    ) -> None:
        self.is_memory = str(db_path) == ":memory:"
        self.db_path = Path(db_path) if not self.is_memory else Path(":memory:")
        self.bak_path = self.db_path.with_suffix(".bak") if not self.is_memory else Path(":memory:")
        self.schema_sql = schema_sql
        self.expected_user_version = expected_user_version
        self.auto_restore_backup = auto_restore_backup
        self._memory_conn: sqlite3.Connection | None = None

        self._initialize_or_verify()

    def _initialize_or_verify(self) -> None:
        """Perform opening ceremony: integrity check or initialization."""
        if self.is_memory:
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")
            with self._memory_conn:
                self._memory_conn.executescript(self.schema_sql)
                self._memory_conn.execute(f"PRAGMA user_version = {self.expected_user_version};")
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.db_path.exists():
            self._create_fresh_db()
            return

        is_intact, reason = check_db_file_integrity(self.db_path)
        version_valid = False

        if is_intact:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cur = conn.cursor()
                cur.execute("PRAGMA user_version;")
                actual_version = cur.fetchone()[0]
                if actual_version == self.expected_user_version:
                    version_valid = True
                else:
                    reason = (
                        f"Schema version mismatch: expected {self.expected_user_version}, "
                        f"found {actual_version}"
                    )
            finally:
                conn.close()

        if not is_intact or not version_valid:
            self._handle_corruption(reason)
            return

        with suppress(DatabaseError, sqlite3.Error, OSError):
            self.backup()

    def _create_fresh_db(self) -> None:
        """Create a fresh database with the configured schema and user_version."""
        conn = self.connect()
        try:
            with conn:
                conn.executescript(self.schema_sql)
                conn.execute(f"PRAGMA user_version = {self.expected_user_version};")
        finally:
            conn.close()

        if not self.is_memory:
            self.backup()

    def backup(self) -> None:
        """Create or update database backup using sqlite3 backup API."""
        if self.is_memory:
            return
        is_intact, reason = check_db_file_integrity(self.db_path)
        if not is_intact:
            raise DatabaseCorruptionError(f"Cannot backup corrupted database: {reason}")
        create_backup_file(self.db_path, self.bak_path)

    def _handle_corruption(self, reason: str) -> None:
        """Move corrupted DB aside as .corrupt, validate .bak, and optionally restore."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        corrupt_path = self.db_path.with_name(f"{self.db_path.stem}_{timestamp}.corrupt")

        try:
            shutil.move(str(self.db_path), str(corrupt_path))
        except OSError as err:
            raise DatabaseCorruptionError(
                f"Database corrupted ({reason}), and failed to move to {corrupt_path}: {err}"
            ) from err

        if not self.bak_path.exists():
            raise DatabaseCorruptionError(
                f"Database corrupted ({reason}). Moved corrupt file to {corrupt_path.name}. "
                "No backup file (.bak) found to restore from."
            )

        bak_intact, bak_reason = check_db_file_integrity(self.bak_path)
        if not bak_intact:
            bak_name = f"{self.bak_path.stem}_{timestamp}.corrupt_bak"
            corrupt_bak_path = self.bak_path.with_name(bak_name)
            shutil.move(str(self.bak_path), str(corrupt_bak_path))
            raise DatabaseCorruptionError(
                f"Both active database and backup are invalid! "
                f"Database corrupt: {reason} (moved to {corrupt_path.name}). "
                f"Backup corrupt: {bak_reason} (moved to {corrupt_bak_path.name}). "
                "Manual data recovery required."
            )

        if self.auto_restore_backup:
            shutil.copy2(str(self.bak_path), str(self.db_path))
            restored_conn = self.connect()
            restored_conn.close()
        else:
            raise DatabaseCorruptionError(
                f"Database corrupt ({reason}). Moved to {corrupt_path.name}. "
                f"Valid backup available at {self.bak_path.name}. Automatic restoration disabled."
            )

    def connect(self) -> sqlite3.Connection:
        """Create or return SQLite connection with foreign keys enabled and row_factory set."""
        if self.is_memory and self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an active connection."""
        conn = self.connect()
        try:
            yield conn
        finally:
            if not self.is_memory:
                conn.close()
