"""Domain models and OOP Account hierarchy for Bank Management System."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Customer:
    """Represents a bank customer."""

    name: str
    email: str
    created_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Customer name cannot be empty.")
        if not self.email.strip() or "@" not in self.email:
            raise ValueError(f"Invalid email: '{self.email}'.")


@dataclass
class Account(ABC):
    """Abstract base account defining common ledger attributes and withdrawal contract."""

    account_number: str
    customer_id: int
    balance_cents: int
    status: str = "ACTIVE"
    created_at: str = ""

    @property
    @abstractmethod
    def account_type(self) -> str:
        """Return the string identifier of the account type."""
        ...

    @abstractmethod
    def validate_withdrawal(self, amount_cents: int) -> None:
        """Validate if withdrawal of amount_cents is permitted under account rules."""
        ...


@dataclass
class SavingsAccount(Account):
    """Savings account enforcing a mandatory minimum balance requirement."""

    minimum_balance_cents: int = 5000  # $50.00 minimum balance

    @property
    def account_type(self) -> str:
        return "SAVINGS"

    def validate_withdrawal(self, amount_cents: int) -> None:
        if amount_cents <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if self.balance_cents - amount_cents < self.minimum_balance_cents:
            min_dollars = self.minimum_balance_cents / 100
            curr_dollars = self.balance_cents / 100
            raise ValueError(
                f"Savings account requires minimum balance of ${min_dollars:.2f}. "
                f"Current balance: ${curr_dollars:.2f}."
            )


@dataclass
class CurrentAccount(Account):
    """Current (checking) account permitting overdraft up to a pre-approved limit."""

    overdraft_limit_cents: int = 50000  # $500.00 overdraft allowance

    @property
    def account_type(self) -> str:
        return "CURRENT"

    def validate_withdrawal(self, amount_cents: int) -> None:
        if amount_cents <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        max_drawable = self.balance_cents + self.overdraft_limit_cents
        if amount_cents > max_drawable:
            limit_dollars = self.overdraft_limit_cents / 100
            avail_dollars = max_drawable / 100
            raise ValueError(
                f"Exceeds overdraft limit (${limit_dollars:.2f}). "
                f"Maximum available to withdraw: ${avail_dollars:.2f}."
            )


@dataclass(frozen=True)
class TransactionRecord:
    """Immutable ledger entry recording an account operation."""

    account_number: str
    transaction_type: str  # DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT
    amount_cents: int
    balance_after_cents: int
    timestamp: str
    reference_account: str | None = None
    id: int | None = None
