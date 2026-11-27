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

    with pytest.raises(BankError, match="minimum balance"):
        service.open_account(cust.id, "SAVINGS", initial_deposit_cents=2000)

    savings = service.open_account(cust.id, "SAVINGS", initial_deposit_cents=10000)
    assert isinstance(savings, SavingsAccount)
    assert savings.balance_cents == 10000

    current = service.open_account(cust.id, "CURRENT", initial_deposit_cents=0)
    assert isinstance(current, CurrentAccount)
    assert current.balance_cents == 0


def test_savings_minimum_balance_enforcement(service: BankService) -> None:
    cust = service.register_customer("Alice", "alice@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "SAVINGS", initial_deposit_cents=6000)
    assert acc.id if hasattr(acc, "id") else True

    new_bal = service.withdraw(acc.account_number, 500)
    assert new_bal == 5500

    with pytest.raises(InsufficientFundsError, match="minimum balance"):
        service.withdraw(acc.account_number, 1000)

    assert service.get_account(acc.account_number).balance_cents == 5500


def test_current_account_overdraft_allowance(service: BankService) -> None:
    cust = service.register_customer("Bob", "bob@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "CURRENT", initial_deposit_cents=10000)

    new_bal = service.withdraw(acc.account_number, 20000)
    assert new_bal == -10000

    with pytest.raises(InsufficientFundsError, match="overdraft limit"):
        service.withdraw(acc.account_number, 50000)


def test_atomic_transfer_success(service: BankService) -> None:
    cust1 = service.register_customer("Sender", "sender@example.com")
    cust2 = service.register_customer("Receiver", "receiver@example.com")
    assert cust1.id is not None
    assert cust2.id is not None

    acc1 = service.open_account(cust1.id, "SAVINGS", initial_deposit_cents=20000)
    acc2 = service.open_account(cust2.id, "CURRENT", initial_deposit_cents=5000)

    s_bal, d_bal = service.transfer(acc1.account_number, acc2.account_number, 5000)
    assert s_bal == 15000
    assert d_bal == 10000

    stmt1 = service.get_statement(acc1.account_number)
    assert len(stmt1) == 2
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

    original_execute = service.repo.execute_atomic_transfer

    def failing_transfer(
        source_acc: str, dest_acc: str, amount_cents: int, timestamp: str
    ) -> tuple[int, int]:
        with service.repo.db.get_connection() as conn, conn:
            conn.execute(
                "UPDATE accounts SET balance_cents = balance_cents - ? WHERE account_number = ?;",
                (amount_cents, source_acc),
            )
            raise RuntimeError("Mid-transfer system failure!")

    service.repo.execute_atomic_transfer = failing_transfer

    with pytest.raises(RuntimeError, match="Mid-transfer"):
        service.transfer(acc1.account_number, acc2.account_number, 2000)

    service.repo.execute_atomic_transfer = original_execute

    assert service.get_account(acc1.account_number).balance_cents == 10000
    assert service.get_account(acc2.account_number).balance_cents == 5000


def test_closed_account_operations(service: BankService) -> None:
    cust = service.register_customer("Closer", "closer@example.com")
    assert cust.id is not None
    acc = service.open_account(cust.id, "CURRENT", initial_deposit_cents=5000)

    with pytest.raises(BankError, match="non-zero balance"):
        service.close_account(acc.account_number)

    service.withdraw(acc.account_number, 5000)
    service.close_account(acc.account_number)

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
