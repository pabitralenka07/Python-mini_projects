"""Database repository for Bank Management System with atomic transfer transactions."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p02_bank_management.models import (
    Account,
    CurrentAccount,
    Customer,
    SavingsAccount,
    TransactionRecord,
)

BANK_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    email TEXT NOT NULL UNIQUE CHECK(email LIKE '%_@_%._%'),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_number TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    account_type TEXT NOT NULL CHECK(account_type IN ('SAVINGS', 'CURRENT')),
    balance_cents INTEGER NOT NULL,
    minimum_balance_cents INTEGER NOT NULL DEFAULT 0,
    overdraft_limit_cents INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'CLOSED')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL REFERENCES accounts(account_number) ON DELETE RESTRICT,
    transaction_type TEXT NOT NULL
        CHECK(transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT')),
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    balance_after_cents INTEGER NOT NULL,
    reference_account TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_acc ON transactions(account_number);
"""


class BankRepository:
    """Manages SQL operations for customers, accounts, and financial transactions."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "BankRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=BANK_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    # --- Customers ---

    def add_customer(self, customer: Customer) -> Customer:
        query = "INSERT INTO customers (name, email, created_at) VALUES (?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (customer.name, customer.email, customer.created_at))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for customer.")
            cust_id = int(cursor.lastrowid)

        return Customer(
            id=cust_id,
            name=customer.name,
            email=customer.email,
            created_at=customer.created_at,
        )

    def get_customer_by_id(self, customer_id: int) -> Customer | None:
        query = "SELECT id, name, email, created_at FROM customers WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (customer_id,)).fetchone()
            if not row:
                return None
            return Customer(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                created_at=row["created_at"],
            )

    def get_customer_by_email(self, email: str) -> Customer | None:
        query = "SELECT id, name, email, created_at FROM customers WHERE email = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (email.strip().lower(),)).fetchone()
            if not row:
                return None
            return Customer(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                created_at=row["created_at"],
            )

    def list_customers(self) -> list[Customer]:
        query = "SELECT id, name, email, created_at FROM customers ORDER BY id ASC;"
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Customer(
                    id=r["id"],
                    name=r["name"],
                    email=r["email"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # --- Accounts ---

    def add_account(self, account: Account) -> None:
        min_bal = getattr(account, "minimum_balance_cents", 0)
        overdraft = getattr(account, "overdraft_limit_cents", 0)
        query = """
            INSERT INTO accounts (
                account_number, customer_id, account_type, balance_cents,
                minimum_balance_cents, overdraft_limit_cents, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(
                query,
                (
                    account.account_number,
                    account.customer_id,
                    account.account_type,
                    account.balance_cents,
                    min_bal,
                    overdraft,
                    account.status,
                    account.created_at,
                ),
            )

    def get_account(self, account_number: str) -> Account | None:
        query = """
            SELECT
                account_number, customer_id, account_type, balance_cents,
                minimum_balance_cents, overdraft_limit_cents, status, created_at
            FROM accounts
            WHERE account_number = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (account_number.strip(),)).fetchone()
            if not row:
                return None

            acc_type = row["account_type"]
            if acc_type == "SAVINGS":
                return SavingsAccount(
                    account_number=row["account_number"],
                    customer_id=row["customer_id"],
                    balance_cents=row["balance_cents"],
                    minimum_balance_cents=row["minimum_balance_cents"],
                    status=row["status"],
                    created_at=row["created_at"],
                )
            else:
                return CurrentAccount(
                    account_number=row["account_number"],
                    customer_id=row["customer_id"],
                    balance_cents=row["balance_cents"],
                    overdraft_limit_cents=row["overdraft_limit_cents"],
                    status=row["status"],
                    created_at=row["created_at"],
                )

    def list_accounts_for_customer(self, customer_id: int) -> list[Account]:
        query = """
            SELECT
                account_number, customer_id, account_type, balance_cents,
                minimum_balance_cents, overdraft_limit_cents, status, created_at
            FROM accounts
            WHERE customer_id = ?
            ORDER BY account_number ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (customer_id,)).fetchall()
            accounts: list[Account] = []
            for r in rows:
                if r["account_type"] == "SAVINGS":
                    accounts.append(
                        SavingsAccount(
                            account_number=r["account_number"],
                            customer_id=r["customer_id"],
                            balance_cents=r["balance_cents"],
                            minimum_balance_cents=r["minimum_balance_cents"],
                            status=r["status"],
                            created_at=r["created_at"],
                        )
                    )
                else:
                    accounts.append(
                        CurrentAccount(
                            account_number=r["account_number"],
                            customer_id=r["customer_id"],
                            balance_cents=r["balance_cents"],
                            overdraft_limit_cents=r["overdraft_limit_cents"],
                            status=r["status"],
                            created_at=r["created_at"],
                        )
                    )
            return accounts

    def list_all_accounts(self) -> list[Account]:
        query = """
            SELECT
                account_number, customer_id, account_type, balance_cents,
                minimum_balance_cents, overdraft_limit_cents, status, created_at
            FROM accounts
            ORDER BY account_number ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            accounts: list[Account] = []
            for r in rows:
                if r["account_type"] == "SAVINGS":
                    accounts.append(
                        SavingsAccount(
                            account_number=r["account_number"],
                            customer_id=r["customer_id"],
                            balance_cents=r["balance_cents"],
                            minimum_balance_cents=r["minimum_balance_cents"],
                            status=r["status"],
                            created_at=r["created_at"],
                        )
                    )
                else:
                    accounts.append(
                        CurrentAccount(
                            account_number=r["account_number"],
                            customer_id=r["customer_id"],
                            balance_cents=r["balance_cents"],
                            overdraft_limit_cents=r["overdraft_limit_cents"],
                            status=r["status"],
                            created_at=r["created_at"],
                        )
                    )
            return accounts

    def update_account_status(self, account_number: str, new_status: str) -> None:
        query = "UPDATE accounts SET status = ? WHERE account_number = ?;"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (new_status, account_number))

    # --- Financial Operations & Atomic Transfer ---

    def execute_deposit(self, account_number: str, amount_cents: int, timestamp: str) -> int:
        """Atomically credit account and record DEPOSIT transaction."""
        with self.db.get_connection() as conn, conn:
            conn.execute(
                "UPDATE accounts SET balance_cents = balance_cents + ? WHERE account_number = ?;",
                (amount_cents, account_number),
            )
            row = conn.execute(
                "SELECT balance_cents FROM accounts WHERE account_number = ?;",
                (account_number,),
            ).fetchone()
            new_balance = int(row["balance_cents"])

            conn.execute(
                """
                INSERT INTO transactions (
                    account_number, transaction_type, amount_cents,
                    balance_after_cents, timestamp
                ) VALUES (?, 'DEPOSIT', ?, ?, ?);
                """,
                (account_number, amount_cents, new_balance, timestamp),
            )
            return new_balance

    def execute_withdrawal(self, account_number: str, amount_cents: int, timestamp: str) -> int:
        """Atomically debit account and record WITHDRAWAL transaction."""
        with self.db.get_connection() as conn, conn:
            conn.execute(
                "UPDATE accounts SET balance_cents = balance_cents - ? WHERE account_number = ?;",
                (amount_cents, account_number),
            )
            row = conn.execute(
                "SELECT balance_cents FROM accounts WHERE account_number = ?;",
                (account_number,),
            ).fetchone()
            new_balance = int(row["balance_cents"])

            conn.execute(
                """
                INSERT INTO transactions (
                    account_number, transaction_type, amount_cents,
                    balance_after_cents, timestamp
                ) VALUES (?, 'WITHDRAWAL', ?, ?, ?);
                """,
                (account_number, amount_cents, new_balance, timestamp),
            )
            return new_balance

    def execute_atomic_transfer(
        self,
        source_acc: str,
        dest_acc: str,
        amount_cents: int,
        timestamp: str,
    ) -> tuple[int, int]:
        """Execute a fund transfer as ONE atomic database transaction.

        Debits source, credits destination, and writes both TRANSFER_OUT and
        TRANSFER_IN records within a single transaction boundary.
        """
        with self.db.get_connection() as conn, conn:
            # 1. Debit source
            conn.execute(
                "UPDATE accounts SET balance_cents = balance_cents - ? WHERE account_number = ?;",
                (amount_cents, source_acc),
            )
            s_row = conn.execute(
                "SELECT balance_cents FROM accounts WHERE account_number = ?;",
                (source_acc,),
            ).fetchone()
            source_new_bal = int(s_row["balance_cents"])

            # 2. Record source transaction
            conn.execute(
                """
                INSERT INTO transactions (
                    account_number, transaction_type, amount_cents,
                    balance_after_cents, reference_account, timestamp
                ) VALUES (?, 'TRANSFER_OUT', ?, ?, ?, ?);
                """,
                (source_acc, amount_cents, source_new_bal, dest_acc, timestamp),
            )

            # 3. Credit destination
            conn.execute(
                "UPDATE accounts SET balance_cents = balance_cents + ? WHERE account_number = ?;",
                (amount_cents, dest_acc),
            )
            d_row = conn.execute(
                "SELECT balance_cents FROM accounts WHERE account_number = ?;",
                (dest_acc,),
            ).fetchone()
            dest_new_bal = int(d_row["balance_cents"])

            # 4. Record destination transaction
            conn.execute(
                """
                INSERT INTO transactions (
                    account_number, transaction_type, amount_cents,
                    balance_after_cents, reference_account, timestamp
                ) VALUES (?, 'TRANSFER_IN', ?, ?, ?, ?);
                """,
                (dest_acc, amount_cents, dest_new_bal, source_acc, timestamp),
            )

            return source_new_bal, dest_new_bal

    def list_transactions(self, account_number: str) -> list[TransactionRecord]:
        query = """
            SELECT
                id, account_number, transaction_type, amount_cents,
                balance_after_cents, reference_account, timestamp
            FROM transactions
            WHERE account_number = ?
            ORDER BY id ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (account_number,)).fetchall()
            return [
                TransactionRecord(
                    id=r["id"],
                    account_number=r["account_number"],
                    transaction_type=r["transaction_type"],
                    amount_cents=r["amount_cents"],
                    balance_after_cents=r["balance_after_cents"],
                    reference_account=r["reference_account"],
                    timestamp=r["timestamp"],
                )
                for r in rows
            ]
