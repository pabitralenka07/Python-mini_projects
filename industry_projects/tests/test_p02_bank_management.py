"""Tests for Project 02: Bank Management System.

Covers:
- Savings minimum balance and Current overdraft rules
- Deposit, withdrawal, and transaction statement verification
- Atomic transfer transactions and transaction rollback guarantees
- Closed account constraints
- CLI execution and clean EOF exit handling
"""

import subprocess
import sys
from pathlib import Path

import pytest

from common.clock import FrozenClock
from projects.p02_bank_management.models import CurrentAccount, SavingsAccount
from projects.p02_bank_management.repository import BankRepository
from projects.p02_bank_management.service import (
    AccountClosedError,
    BankError,
    BankService,
    InsufficientFundsError,
    SameAccountTransferError,
)


@pytest.fixture
def repo(tmp_path: Path) -> BankRepository:
    db_file = tmp_path / "test_bank.db"
    return BankRepository.from_path(db_file)


@pytest.fixture
def service(repo: BankRepository) -> BankService:
    clock = FrozenClock("2026-06-01T12:00:00+00:00")
    return BankService(repository=repo, clock=clock)


def test_customer_registration_and_account_opening(service: BankService) -> None:
    cust = service.register_customer("Bruce Wayne", "bruce@example.com")
    assert cust.id is not None

    # Savings requires at least $50.00 (5000 cents)
    with pytest.raises(BankError, match="minimum balance"):
        service.open_account(cust.id, "SAVINGS", initial_deposit_cents=2000)

    # Valid savings opening
    savings = service.open_account(cust.id, "SAVINGS", initial_deposit_cents=10000)
    assert isinstance(savings, SavingsAccount)
    assert savings.balance_cents == 10000

    # Valid current account opening
    current = service.open_account(cust.id, "CURRENT", initial_deposit_cents=0)
    assert isinstance(current, CurrentAccount)
    assert current.balance_cents == 0


def test_savings_minimum_balance_enforcement(service: BankService) -> None:
    cust = service.register_customer("Alice", "alice@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "SAVINGS", initial_deposit_cents=6000)  # $60.00
    assert acc.id if hasattr(acc, "id") else True

    # Withdraw $5.00 -> balance $55.00 (allowed)
    new_bal = service.withdraw(acc.account_number, 500)
    assert new_bal == 5500

    # Withdraw $10.00 -> would leave $45.00 < $50.00 (rejected!)
    with pytest.raises(InsufficientFundsError, match="minimum balance"):
        service.withdraw(acc.account_number, 1000)

    assert service.get_account(acc.account_number).balance_cents == 5500


def test_current_account_overdraft_allowance(service: BankService) -> None:
    cust = service.register_customer("Bob", "bob@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "CURRENT", initial_deposit_cents=10000)  # $100.00

    # Withdraw $200.00 -> balance -$100.00 (within $500.00 overdraft limit)
    new_bal = service.withdraw(acc.account_number, 20000)
    assert new_bal == -10000

    # Max drawable remaining is $400.00 (40000 cents). Attempt to withdraw $500.00 -> rejected!
    with pytest.raises(InsufficientFundsError, match="overdraft limit"):
        service.withdraw(acc.account_number, 50000)


def test_atomic_transfer_success(service: BankService) -> None:
    cust1 = service.register_customer("Sender", "sender@example.com")
    cust2 = service.register_customer("Receiver", "receiver@example.com")
    assert cust1.id is not None
    assert cust2.id is not None

    acc1 = service.open_account(cust1.id, "SAVINGS", initial_deposit_cents=20000)  # $200.00
    acc2 = service.open_account(cust2.id, "CURRENT", initial_deposit_cents=5000)  # $50.00

    # Transfer $50.00
    s_bal, d_bal = service.transfer(acc1.account_number, acc2.account_number, 5000)
    assert s_bal == 15000
    assert d_bal == 10000

    # Verify statement
    stmt1 = service.get_statement(acc1.account_number)
    assert len(stmt1) == 2  # DEPOSIT (initial) + TRANSFER_OUT
    assert stmt1[-1].transaction_type == "TRANSFER_OUT"

    stmt2 = service.get_statement(acc2.account_number)
    assert stmt2[-1].transaction_type == "TRANSFER_IN"


def test_same_account_transfer_rejected(service: BankService) -> None:
    cust = service.register_customer("Self", "self@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "SAVINGS", initial_deposit_cents=10000)

    with pytest.raises(SameAccountTransferError):
        service.transfer(acc.account_number, acc.account_number, 1000)


def test_transfer_atomic_rollback_on_failure(tmp_path: Path, service: BankService) -> None:
    """Verify that a failure in the middle of a transfer rolls back both accounts."""
    cust1 = service.register_customer("User1", "u1@example.com")
    cust2 = service.register_customer("User2", "u2@example.com")
    assert cust1.id is not None
    assert cust2.id is not None

    acc1 = service.open_account(cust1.id, "SAVINGS", initial_deposit_cents=10000)
    acc2 = service.open_account(cust2.id, "CURRENT", initial_deposit_cents=5000)

    # Intentionally trigger an error during execution of atomic transfer
    # by corrupting the second destination statement in the repository
    original_execute = service.repo.execute_atomic_transfer

    def failing_transfer(
        source_acc: str, dest_acc: str, amount_cents: int, timestamp: str
    ) -> tuple[int, int]:
        with service.repo.db.get_connection() as conn, conn:
            # Debit source
            conn.execute(
                "UPDATE accounts SET balance_cents = balance_cents - ? WHERE account_number = ?;",
                (amount_cents, source_acc),
            )
            # Simulated crash mid-transfer
            raise RuntimeError("Mid-transfer system failure!")

    service.repo.execute_atomic_transfer = failing_transfer  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="Mid-transfer"):
        service.transfer(acc1.account_number, acc2.account_number, 2000)

    # Restore original function
    service.repo.execute_atomic_transfer = original_execute  # type: ignore[method-assign]

    # Verify that source account balance was NOT modified (rolled back!)
    assert service.get_account(acc1.account_number).balance_cents == 10000
    assert service.get_account(acc2.account_number).balance_cents == 5000


def test_closed_account_operations(service: BankService) -> None:
    cust = service.register_customer("Closer", "closer@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "CURRENT", initial_deposit_cents=5000)

    # Cannot close with balance
    with pytest.raises(BankError, match="non-zero balance"):
        service.close_account(acc.account_number)

    # Withdraw all to zero
    service.withdraw(acc.account_number, 5000)
    service.close_account(acc.account_number)

    # Transactions on closed account must fail
    with pytest.raises(AccountClosedError):
        service.deposit(acc.account_number, 1000)

    with pytest.raises(AccountClosedError):
        service.withdraw(acc.account_number, 1000)


def test_cli_eof_clean_exit() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "projects.p02_bank_management"],
        cwd=root_dir,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Goodbye" in proc.stdout or "Exiting" in proc.stdout
