"""Tests for common.db module covering constraints, rollback, and corruption recovery."""

import sqlite3
from pathlib import Path

import pytest

from common.db import (
    DatabaseCorruptionError,
    DatabaseManager,
)

SAMPLE_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    balance INTEGER NOT NULL CHECK(balance >= 0)
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    message TEXT NOT NULL
);
"""


def test_in_memory_db_and_foreign_keys() -> None:
    db = DatabaseManager(":memory:", SAMPLE_SCHEMA, expected_user_version=1)
    with db.get_connection() as conn, conn:
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("alice", 100))

    with db.get_connection() as conn, pytest.raises(sqlite3.IntegrityError), conn:
        conn.execute("INSERT INTO logs (user_id, message) VALUES (?, ?);", (999, "invalid"))


def test_constraint_violations() -> None:
    db = DatabaseManager(":memory:", SAMPLE_SCHEMA, expected_user_version=1)
    with db.get_connection() as conn, conn:
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("alice", 100))

    with db.get_connection() as conn, pytest.raises(sqlite3.IntegrityError), conn:
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("alice", 200))

    with db.get_connection() as conn, pytest.raises(sqlite3.IntegrityError), conn:
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("bob", -50))


def test_transaction_rollback(tmp_path: Path) -> None:
    db_file = tmp_path / "test_trans.db"
    db = DatabaseManager(db_file, SAMPLE_SCHEMA, expected_user_version=1)

    with db.get_connection() as conn, conn:
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("alice", 100))
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("bob", 100))

    with (
        pytest.raises(ValueError, match="Intentional crash mid-transfer"),
        db.get_connection() as conn,
        conn,
    ):
        conn.execute("UPDATE users SET balance = balance - 50 WHERE username = 'alice';")
        raise ValueError("Intentional crash mid-transfer")

    with db.get_connection() as conn:
        rows = dict(conn.execute("SELECT username, balance FROM users;").fetchall())
        assert rows["alice"] == 100
        assert rows["bob"] == 100


def test_corruption_recovery_from_backup(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    db = DatabaseManager(db_file, SAMPLE_SCHEMA, expected_user_version=1)

    with db.get_connection() as conn, conn:
        conn.execute("INSERT INTO users (username, balance) VALUES (?, ?);", ("alice", 500))

    db.backup()
    bak_file = db_file.with_suffix(".bak")
    assert bak_file.exists()

    with open(db_file, "wb") as f:
        f.write(b"NOT A SQLITE FILE GARBAGE DATA 1234567890")

    db2 = DatabaseManager(db_file, SAMPLE_SCHEMA, expected_user_version=1, auto_restore_backup=True)
    with db2.get_connection() as conn:
        row = conn.execute(
            "SELECT username, balance FROM users WHERE username = 'alice';"
        ).fetchone()
        assert row is not None
        assert row["balance"] == 500

    corrupt_files = list(tmp_path.glob("*.corrupt"))
    assert len(corrupt_files) == 1


def test_both_files_corrupt_raises_error(tmp_path: Path) -> None:
    db_file = tmp_path / "double_corrupt.db"
    DatabaseManager(db_file, SAMPLE_SCHEMA, expected_user_version=1)
    bak_file = db_file.with_suffix(".bak")

    with open(db_file, "wb") as f:
        f.write(b"CORRUPT DB")
    with open(bak_file, "wb") as f:
        f.write(b"CORRUPT BAK")

    err_msg = "Both active database and backup are invalid"
    with pytest.raises(DatabaseCorruptionError, match=err_msg):
        DatabaseManager(db_file, SAMPLE_SCHEMA, expected_user_version=1)


def test_wrong_user_version_triggers_handling(tmp_path: Path) -> None:
    db_file = tmp_path / "wrong_ver.db"
    conn = sqlite3.connect(db_file)
    with conn:
        conn.executescript(SAMPLE_SCHEMA)
        conn.execute("PRAGMA user_version = 99;")
    conn.close()

    with pytest.raises(DatabaseCorruptionError, match="Schema version mismatch"):
        DatabaseManager(db_file, SAMPLE_SCHEMA, expected_user_version=1)
