"""Service layer for Bank Management System enforcing banking rules and transactions."""

import secrets

from common.clock import Clock, SystemClock
from projects.p02_bank_management.models import (
    Account,
    CurrentAccount,
    Customer,
    SavingsAccount,
    TransactionRecord,
)
from projects.p02_bank_management.repository import BankRepository


class BankError(Exception):
    """Base exception for banking business errors."""

    pass


class CustomerNotFoundError(BankError):
    """Raised when customer does not exist."""

    pass


class AccountNotFoundError(BankError):
    """Raised when account does not exist."""

    pass


class AccountClosedError(BankError):
    """Raised when trying to transact on a closed account."""

    pass


class InsufficientFundsError(BankError):
    """Raised when an account cannot satisfy a withdrawal or transfer."""

    pass


class SameAccountTransferError(BankError):
    """Raised when source and destination of a transfer are identical."""

    pass


class InvalidAmountError(BankError):
    """Raised when amount is negative, zero, or non-finite."""

    pass


class BankService:
    """Coordinates customer onboarding, account lifecycle, and financial transactions."""

    def __init__(self, repository: BankRepository, clock: Clock | None = None) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()

    def _get_timestamp(self) -> str:
        return self.clock.now_iso()


    def register_customer(self, name: str, email: str) -> Customer:
        name_clean = name.strip()
        email_clean = email.strip().lower()
        if not name_clean:
            raise BankError("Customer name cannot be empty.")
        if "@" not in email_clean or "." not in email_clean:
            raise BankError(f"Invalid customer email '{email_clean}'.")

        existing = self.repo.get_customer_by_email(email_clean)
        if existing:
            raise BankError(f"Customer with email '{email_clean}' already exists.")

        created_at = self._get_timestamp()
        customer = Customer(name=name_clean, email=email_clean, created_at=created_at)
        return self.repo.add_customer(customer)

    def list_customers(self) -> list[Customer]:
        return self.repo.list_customers()


    def open_account(
        self, customer_id: int, account_type: str, initial_deposit_cents: int = 0
    ) -> Account:
        customer = self.repo.get_customer_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(f"Customer ID {customer_id} does not exist.")

        acc_type_norm = account_type.strip().upper()
        if acc_type_norm not in ("SAVINGS", "CURRENT"):
            raise BankError("Account type must be either 'SAVINGS' or 'CURRENT'.")

        if initial_deposit_cents < 0:
            raise InvalidAmountError("Initial deposit cannot be negative.")

        prefix = "SAV" if acc_type_norm == "SAVINGS" else "CUR"
        rand_suffix = f"{secrets.randbelow(900000) + 100000}"
        account_number = f"{prefix}-{rand_suffix}"

        created_at = self._get_timestamp()

        account: Account
        if acc_type_norm == "SAVINGS":
            min_bal = 5000
            if initial_deposit_cents < min_bal:
                raise BankError(
                    f"Savings accounts require an initial deposit of at least "
                    f"${min_bal / 100:.2f} (minimum balance)."
                )
            account = SavingsAccount(
                account_number=account_number,
                customer_id=customer_id,
                balance_cents=0,
                minimum_balance_cents=min_bal,
                status="ACTIVE",
                created_at=created_at,
            )
        else:
            overdraft = 50000
            account = CurrentAccount(
                account_number=account_number,
                customer_id=customer_id,
                balance_cents=0,
                overdraft_limit_cents=overdraft,
                status="ACTIVE",
                created_at=created_at,
            )

        self.repo.add_account(account)

        if initial_deposit_cents > 0:
            final_bal = self.repo.execute_deposit(account_number, initial_deposit_cents, created_at)
            account.balance_cents = final_bal

        return account

    def close_account(self, account_number: str) -> None:
        account = self.get_account(account_number)
        if account.status == "CLOSED":
            raise AccountClosedError(f"Account {account_number} is already closed.")

        if account.balance_cents != 0:
            dollars = account.balance_cents / 100
            raise BankError(
                f"Cannot close account with non-zero balance (${dollars:.2f}). "
                "Please withdraw or settle all funds first."
            )

        self.repo.update_account_status(account_number, "CLOSED")

    def get_account(self, account_number: str) -> Account:
        account = self.repo.get_account(account_number)
        if not account:
            raise AccountNotFoundError(f"Account '{account_number}' not found.")
        return account

    def list_all_accounts(self) -> list[Account]:
        return self.repo.list_all_accounts()

    def list_accounts_for_customer(self, customer_id: int) -> list[Account]:
        return self.repo.list_accounts_for_customer(customer_id)


    def deposit(self, account_number: str, amount_cents: int) -> int:
        if amount_cents <= 0:
            raise InvalidAmountError("Deposit amount must be positive.")

        account = self.get_account(account_number)
        if account.status != "ACTIVE":
            raise AccountClosedError(f"Cannot deposit into closed account {account_number}.")

        timestamp = self._get_timestamp()
        return self.repo.execute_deposit(account_number, amount_cents, timestamp)

    def withdraw(self, account_number: str, amount_cents: int) -> int:
        if amount_cents <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")

        account = self.get_account(account_number)
        if account.status != "ACTIVE":
            raise AccountClosedError(f"Cannot withdraw from closed account {account_number}.")

        try:
            account.validate_withdrawal(amount_cents)
        except ValueError as err:
            raise InsufficientFundsError(str(err)) from err

        timestamp = self._get_timestamp()
        return self.repo.execute_withdrawal(account_number, amount_cents, timestamp)

    def transfer(self, source_acc: str, dest_acc: str, amount_cents: int) -> tuple[int, int]:
        source_clean = source_acc.strip()
        dest_clean = dest_acc.strip()

        if source_clean == dest_clean:
            raise SameAccountTransferError("Cannot transfer funds to the same account.")

        if amount_cents <= 0:
            raise InvalidAmountError("Transfer amount must be positive.")

        src = self.get_account(source_clean)
        dst = self.get_account(dest_clean)

        if src.status != "ACTIVE":
            raise AccountClosedError(f"Source account {source_clean} is closed.")
        if dst.status != "ACTIVE":
            raise AccountClosedError(f"Destination account {dest_clean} is closed.")

        try:
            src.validate_withdrawal(amount_cents)
        except ValueError as err:
            raise InsufficientFundsError(str(err)) from err

        timestamp = self._get_timestamp()
        return self.repo.execute_atomic_transfer(
            source_acc=source_clean,
            dest_acc=dest_clean,
            amount_cents=amount_cents,
            timestamp=timestamp,
        )

    def get_statement(self, account_number: str) -> list[TransactionRecord]:
        _ = self.get_account(account_number)
        return self.repo.list_transactions(account_number)
