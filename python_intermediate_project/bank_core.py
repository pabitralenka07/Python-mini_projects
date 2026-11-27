"""Core banking logic shared by the Bank Management and ATM apps."""
import hashlib
import hmac
import secrets

from common import AppError

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(
    acc_no INTEGER PRIMARY KEY AUTOINCREMENT,
    holder TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0 CHECK(balance >= 0),
    failed INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acc_no INTEGER NOT NULL REFERENCES accounts(acc_no),
    kind TEXT NOT NULL,
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    note TEXT,
    ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class BankError(AppError):
    pass


def hash_pin(pin, salt=None):
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_pin(pin, stored):
    salt = stored.split("$")[0]
    return hmac.compare_digest(hash_pin(pin, salt), stored)


class Bank:
    MAX_ATTEMPTS = 3

    def __init__(self, db):
        self.db = db

    def open_account(self, holder, pin, opening=0.0):
        holder = holder.strip()
        if not holder:
            raise BankError("Holder name is required")
        if not (pin.isdigit() and len(pin) == 4):
            raise BankError("PIN must be exactly 4 digits")
        if opening < 0:
            raise BankError("Opening deposit cannot be negative")
        acc = self.db.execute("INSERT INTO accounts(holder, pin_hash) VALUES(?,?)",
                              (holder, hash_pin(pin)))
        if opening:
            self.deposit(acc, opening, "Opening deposit")
        return acc

    def accounts(self):
        return self.db.query("SELECT acc_no, holder, balance, "
                             "CASE WHEN locked THEN 'Locked' ELSE 'Active' END AS status "
                             "FROM accounts ORDER BY acc_no")

    def balance(self, acc_no):
        row = self.db.one("SELECT balance FROM accounts WHERE acc_no=?", (acc_no,))
        if row is None:
            raise BankError("Account not found")
        return row["balance"]

    def unlock(self, acc_no):
        self.db.execute("UPDATE accounts SET locked=0, failed=0 WHERE acc_no=?", (acc_no,))

    def authenticate(self, acc_no, pin):
        row = self.db.one("SELECT * FROM accounts WHERE acc_no=?", (acc_no,))
        if row is None:
            raise BankError("Invalid account or PIN")
        if row["locked"]:
            raise BankError("Account is locked. Please contact the bank.")
        if verify_pin(pin, row["pin_hash"]):
            self.db.execute("UPDATE accounts SET failed=0 WHERE acc_no=?", (acc_no,))
            return row["holder"]
        failed = row["failed"] + 1
        locked = failed >= self.MAX_ATTEMPTS
        self.db.execute("UPDATE accounts SET failed=?, locked=? WHERE acc_no=?",
                        (failed, int(locked), acc_no))
        raise BankError("Invalid account or PIN - account locked" if locked else
                        f"Invalid account or PIN ({self.MAX_ATTEMPTS - failed} attempts left)")

    def change_pin(self, acc_no, old, new):
        self.authenticate(acc_no, old)
        if not (new.isdigit() and len(new) == 4):
            raise BankError("New PIN must be exactly 4 digits")
        self.db.execute("UPDATE accounts SET pin_hash=? WHERE acc_no=?", (hash_pin(new), acc_no))

    def _apply(self, acc_no, delta, kind, note):
        row = self.db.conn.execute("SELECT balance FROM accounts WHERE acc_no=?", (acc_no,)).fetchone()
        if row is None:
            raise BankError(f"Account {acc_no} not found")
        new = round(row["balance"] + delta, 2)
        if new < 0:
            raise BankError("Insufficient funds")
        self.db.conn.execute("UPDATE accounts SET balance=? WHERE acc_no=?", (new, acc_no))
        self.db.conn.execute(
            "INSERT INTO transactions(acc_no, kind, amount, balance_after, note) VALUES(?,?,?,?,?)",
            (acc_no, kind, abs(delta), new, note))
        return new

    @staticmethod
    def _check(amount):
        if amount <= 0:
            raise BankError("Amount must be greater than zero")

    def deposit(self, acc_no, amount, note="Deposit"):
        self._check(amount)
        with self.db.conn:
            return self._apply(acc_no, amount, "Deposit", note)

    def withdraw(self, acc_no, amount, kind="Withdrawal"):
        self._check(amount)
        with self.db.conn:
            return self._apply(acc_no, -amount, kind, "")

    def transfer(self, src, dst, amount):
        self._check(amount)
        if src == dst:
            raise BankError("Cannot transfer to the same account")
        with self.db.conn:
            new = self._apply(src, -amount, "Transfer Out", f"To {dst}")
            self._apply(dst, amount, "Transfer In", f"From {src}")
            return new

    def statement(self, acc_no, limit=25):
        return self.db.query(
            "SELECT ts, kind, amount, balance_after, COALESCE(note,'') FROM transactions "
            "WHERE acc_no=? ORDER BY id DESC LIMIT ?", (acc_no, limit))
