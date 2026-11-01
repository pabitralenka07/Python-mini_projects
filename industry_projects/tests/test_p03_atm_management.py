"""Tests for Project 03: ATM Management System.

Covers:
- Educational scrypt PIN hashing and constant-time verification
- Attempt limit lockout simulation
- Cash withdrawal with greedy banknote breakdown ($100, $50, $20, $10)
- Denomination validation (multiples of $10)
- Rolling daily withdrawal quota enforcement
- PIN changes and invalidation of old PIN
- Mini statement extraction from BankService
- CLI execution and clean EOF exit handling
"""

import subprocess
import sys
from pathlib import Path

import pytest

from common.clock import FrozenClock
from projects.p02_bank_management.repository import BankRepository
from projects.p02_bank_management.service import BankService
from projects.p03_atm_management.models import CashDispenseResult
from projects.p03_atm_management.repository import ATMRepository
from projects.p03_atm_management.service import (
    ATMError,
    ATMService,
    CardBlockedError,
    DailyLimitExceededError,
    DenominationError,
    InvalidPINError,
    calculate_banknotes,
)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock("2026-06-01T12:00:00+00:00")


@pytest.fixture
def bank_service(tmp_path: Path, clock: FrozenClock) -> BankService:
    db_file = tmp_path / "bank.db"
    repo = BankRepository.from_path(db_file)
    return BankService(repository=repo, clock=clock)


@pytest.fixture
def atm_service(tmp_path: Path, bank_service: BankService, clock: FrozenClock) -> ATMService:
    atm_db = tmp_path / "atm.db"
    repo = ATMRepository.from_path(atm_db)
    return ATMService(
        atm_repository=repo,
        bank_service=bank_service,
        clock=clock,
        daily_limit_cents=100000,  # $1,000.00
        max_pin_attempts=3,
        lockout_minutes=15,
    )


@pytest.fixture
def card_and_account(bank_service: BankService, atm_service: ATMService) -> tuple[str, str]:
    cust = bank_service.register_customer("ATM Customer", "atm@example.com")
    assert cust.id is not None
    acc = bank_service.open_account(cust.id, "SAVINGS", initial_deposit_cents=200000)  # $2,000.00
    card = atm_service.issue_card("1111-2222-3333-4444", acc.account_number, "4321")
    return card.card_number, acc.account_number


def test_banknote_dispenser_algorithm() -> None:
    # $180 -> one 100, one 50, one 20, one 10
    result = calculate_banknotes(18000)
    assert result == CashDispenseResult(
        total_cents=18000,
        notes_100=1,
        notes_50=1,
        notes_20=1,
        notes_10=1,
    )
    assert "1 x $100, 1 x $50, 1 x $20, 1 x $10" in result.summary()

    # Rejects non-multiples of $10
    with pytest.raises(DenominationError, match="multiples of \\$10\\.00"):
        calculate_banknotes(1550)  # $15.50


def test_authentication_success_and_failure(
    atm_service: ATMService, card_and_account: tuple[str, str]
) -> None:
    card_no, _ = card_and_account

    # Correct PIN
    card = atm_service.authenticate(card_no, "4321")
    assert card.card_number == card_no

    # Incorrect PIN
    with pytest.raises(InvalidPINError, match="Incorrect PIN"):
        atm_service.authenticate(card_no, "9999")


def test_lockout_after_max_attempts(
    atm_service: ATMService, card_and_account: tuple[str, str], clock: FrozenClock
) -> None:
    card_no, _ = card_and_account

    # Attempt 1
    with pytest.raises(InvalidPINError, match="2 attempt\\(s\\) remaining"):
        atm_service.authenticate(card_no, "0001")

    # Attempt 2
    with pytest.raises(InvalidPINError, match="1 attempt\\(s\\) remaining"):
        atm_service.authenticate(card_no, "0002")

    # Attempt 3 (triggers lockout)
    with pytest.raises(CardBlockedError, match="Card locked for 15 minutes"):
        atm_service.authenticate(card_no, "0003")

    # While locked, even the correct PIN is rejected
    with pytest.raises(CardBlockedError, match="temporarily locked"):
        atm_service.authenticate(card_no, "4321")

    # Advance clock by 16 minutes -> lockout expires, correct PIN succeeds
    clock.advance(minutes=16)
    card = atm_service.authenticate(card_no, "4321")
    assert card.card_number == card_no


def test_cash_withdrawal_and_daily_limit(
    atm_service: ATMService, card_and_account: tuple[str, str]
) -> None:
    card_no, _ = card_and_account

    # Initial balance $2,000.00
    assert atm_service.get_balance(card_no) == 200000

    # Withdraw $200.00 -> balance becomes $1,800.00
    dispense = atm_service.withdraw_cash(card_no, 20000)
    assert dispense.notes_100 == 2
    assert atm_service.get_balance(card_no) == 180000

    # Withdraw another $700.00 -> total today is $900.00 (within $1,000 limit)
    atm_service.withdraw_cash(card_no, 70000)
    assert atm_service.get_balance(card_no) == 110000

    # Attempting another $200.00 would make daily total $1,100.00 > $1,000.00 -> Rejected!
    with pytest.raises(DailyLimitExceededError, match="Daily withdrawal limit is \\$1,000\\.00"):
        atm_service.withdraw_cash(card_no, 20000)


def test_cash_deposit_and_mini_statement(
    atm_service: ATMService, card_and_account: tuple[str, str]
) -> None:
    card_no, _ = card_and_account

    # Deposit $300.00
    new_bal = atm_service.deposit_cash(card_no, 30000)
    assert new_bal == 230000

    # Mini statement should contain initial deposit and this deposit
    statement = atm_service.get_mini_statement(card_no, limit=5)
    assert len(statement) >= 2
    assert statement[-1].transaction_type == "DEPOSIT"
    assert statement[-1].amount_cents == 30000


def test_change_pin(atm_service: ATMService, card_and_account: tuple[str, str]) -> None:
    card_no, _ = card_and_account

    # Reject identical PIN
    with pytest.raises(ATMError, match="cannot be identical"):
        atm_service.change_pin(card_no, "4321", "4321")

    # Reject non-4-digit PIN
    with pytest.raises(ATMError, match="exactly 4 numeric digits"):
        atm_service.change_pin(card_no, "4321", "12345")

    # Successfully change PIN to "9876"
    atm_service.change_pin(card_no, "4321", "9876")

    # Old PIN now fails
    with pytest.raises(InvalidPINError):
        atm_service.authenticate(card_no, "4321")

    # New PIN succeeds
    card = atm_service.authenticate(card_no, "9876")
    assert card.card_number == card_no


def test_cli_eof_clean_exit() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "projects.p03_atm_management"],
        cwd=root_dir,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "terminated" in proc.stdout or "aborted" in proc.stdout
