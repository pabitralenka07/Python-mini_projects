"""Repository for ATM cards and daily withdrawal tracking."""

from pathlib import Path

from common.db import DatabaseManager
from projects.p03_atm_management.models import ATMCard

ATM_SCHEMA = """
CREATE TABLE IF NOT EXISTS atm_cards (
    card_number TEXT PRIMARY KEY,
    account_number TEXT NOT NULL,
    pin_hash BLOB NOT NULL,
    salt BLOB NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'BLOCKED'))
);

CREATE TABLE IF NOT EXISTS daily_atm_withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_number TEXT NOT NULL REFERENCES atm_cards(card_number) ON DELETE RESTRICT,
    withdrawal_date TEXT NOT NULL, -- YYYY-MM-DD
    total_amount_cents INTEGER NOT NULL DEFAULT 0,
    UNIQUE(card_number, withdrawal_date)
);

CREATE INDEX IF NOT EXISTS idx_atm_cards_acc ON atm_cards(account_number);
"""


class ATMRepository:
    """Manages SQLite operations for ATM cards and daily withdrawal limits."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "ATMRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=ATM_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    def add_card(self, card: ATMCard) -> None:
        query = """
            INSERT INTO atm_cards (
                card_number, account_number, pin_hash, salt, failed_attempts,
                locked_until, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(
                query,
                (
                    card.card_number,
                    card.account_number,
                    card.pin_hash,
                    card.salt,
                    card.failed_attempts,
                    card.locked_until,
                    card.status,
                ),
            )

    def get_card(self, card_number: str) -> ATMCard | None:
        query = """
            SELECT card_number, account_number, pin_hash, salt, failed_attempts,
                   locked_until, status
            FROM atm_cards
            WHERE card_number = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (card_number.strip(),)).fetchone()
            if not row:
                return None
            return ATMCard(
                card_number=row["card_number"],
                account_number=row["account_number"],
                pin_hash=row["pin_hash"],
                salt=row["salt"],
                failed_attempts=row["failed_attempts"],
                locked_until=row["locked_until"],
                status=row["status"],
            )

    def update_pin(self, card_number: str, new_hash: bytes, new_salt: bytes) -> None:
        query = "UPDATE atm_cards SET pin_hash = ?, salt = ? WHERE card_number = ?;"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (new_hash, new_salt, card_number))

    def record_failed_attempt(
        self, card_number: str, attempts: int, locked_until: str | None = None
    ) -> None:
        query = """
            UPDATE atm_cards
            SET failed_attempts = ?, locked_until = ?
            WHERE card_number = ?;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (attempts, locked_until, card_number))

    def reset_failed_attempts(self, card_number: str) -> None:
        query = (
            "UPDATE atm_cards SET failed_attempts = 0, locked_until = NULL WHERE card_number = ?;"
        )
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (card_number,))

    def block_card(self, card_number: str) -> None:
        query = "UPDATE atm_cards SET status = 'BLOCKED' WHERE card_number = ?;"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (card_number,))

    def get_daily_withdrawn_cents(self, card_number: str, date_iso: str) -> int:
        query = """
            SELECT total_amount_cents
            FROM daily_atm_withdrawals
            WHERE card_number = ? AND withdrawal_date = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (card_number, date_iso)).fetchone()
            if not row:
                return 0
            return int(row["total_amount_cents"])

    def record_daily_withdrawal(self, card_number: str, date_iso: str, amount_cents: int) -> None:
        query = """
            INSERT INTO daily_atm_withdrawals (card_number, withdrawal_date, total_amount_cents)
            VALUES (?, ?, ?)
            ON CONFLICT(card_number, withdrawal_date) DO UPDATE SET
                total_amount_cents = total_amount_cents + excluded.total_amount_cents;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (card_number, date_iso, amount_cents))
