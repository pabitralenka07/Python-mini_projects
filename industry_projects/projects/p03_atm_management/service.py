"""Service layer for ATM Management System reusing BankService and scrypt PIN security.

IMPORTANT NOTICE:
This module is strictly an educational simulation of an automated teller machine (ATM)
PIN verification and withdrawal workflow. It is NOT secure production authentication.
Real automated teller systems utilize certified Hardware Security Modules (HSMs),
EMV chip cryptography, PIN block encryption (ISO 9564), and bank network switches.
"""

from datetime import datetime, timedelta

from common.clock import Clock, SystemClock
from common.money import cents_to_display
from common.security import hash_secret, is_locked, verify_secret
from projects.p02_bank_management.models import TransactionRecord
from projects.p02_bank_management.service import BankService
from projects.p03_atm_management.models import ATMCard, CashDispenseResult
from projects.p03_atm_management.repository import ATMRepository


class ATMError(Exception):
    """Base exception for ATM domain errors."""

    pass


class CardNotFoundError(ATMError):
    """Raised when an unrecognized card number is inserted."""

    pass


class CardBlockedError(ATMError):
    """Raised when card has been permanently blocked or temporarily locked."""

    pass


class InvalidPINError(ATMError):
    """Raised when an incorrect PIN is entered."""

    pass


class DailyLimitExceededError(ATMError):
    """Raised when withdrawal causes cumulative daily total to exceed quota."""

    pass


class DenominationError(ATMError):
    """Raised when requested amount cannot be dispensed with available banknote values."""

    pass


def calculate_banknotes(amount_cents: int) -> CashDispenseResult:
    """Greedy algorithm decomposing an integer cent amount into $100, $50, $20, and $10 notes."""
    if amount_cents % 1000 != 0:
        raise DenominationError("ATM can only dispense cash in multiples of $10.00.")

    remaining = amount_cents

    n100 = remaining // 10000
    remaining %= 10000

    n50 = remaining // 5000
    remaining %= 5000

    n20 = remaining // 2000
    remaining %= 2000

    n10 = remaining // 1000
    remaining %= 1000

    return CashDispenseResult(
        total_cents=amount_cents,
        notes_100=n100,
        notes_50=n50,
        notes_20=n20,
        notes_10=n10,
    )


class ATMService:
    """Orchestrates ATM card sessions, PIN security, and cash dispensing.

    Delegates ledger and balance management directly to BankService.
    """

    def __init__(
        self,
        atm_repository: ATMRepository,
        bank_service: BankService,
        clock: Clock | None = None,
        daily_limit_cents: int = 100000,  # $1,000.00 daily limit
        max_pin_attempts: int = 3,
        lockout_minutes: int = 15,
    ) -> None:
        self.repo = atm_repository
        self.bank = bank_service
        self.clock = clock if clock is not None else SystemClock()
        self.daily_limit_cents = daily_limit_cents
        self.max_pin_attempts = max_pin_attempts
        self.lockout_minutes = lockout_minutes

    def issue_card(self, card_number: str, account_number: str, pin: str) -> ATMCard:
        """Issue an educational ATM card with scrypt PIN hash and salt."""
        # Verify account exists in Bank
        _ = self.bank.get_account(account_number)

        pin_clean = pin.strip()
        if len(pin_clean) != 4 or not pin_clean.isdigit():
            raise ATMError("PIN must be exactly 4 numeric digits.")

        pin_hash, salt = hash_secret(pin_clean)
        card = ATMCard(
            card_number=card_number.strip(),
            account_number=account_number.strip(),
            pin_hash=pin_hash,
            salt=salt,
        )
        self.repo.add_card(card)
        return card

    def authenticate(self, card_number: str, pin: str) -> ATMCard:
        """Verify card and PIN against scrypt hash with account lockout tracking."""
        card = self.repo.get_card(card_number)
        if not card:
            raise CardNotFoundError(f"Card '{card_number}' not recognized.")

        if card.status == "BLOCKED":
            raise CardBlockedError("Card is permanently blocked. Contact customer support.")

        now_iso = self.clock.now_iso()
        if is_locked(card.locked_until, now_iso):
            raise CardBlockedError(
                f"Card is temporarily locked due to repeated incorrect PIN entries. "
                f"Locked until: {card.locked_until}."
            )

        if not verify_secret(pin, card.salt, card.pin_hash):
            attempts = card.failed_attempts + 1
            if attempts >= self.max_pin_attempts:
                # Lock card for lockout_minutes
                dt_now = datetime.fromisoformat(now_iso)
                locked_until = (dt_now + timedelta(minutes=self.lockout_minutes)).isoformat()
                self.repo.record_failed_attempt(card.card_number, attempts, locked_until)
                raise CardBlockedError(
                    f"Maximum PIN attempts exceeded ({self.max_pin_attempts}). "
                    f"Card locked for {self.lockout_minutes} minutes."
                )
            else:
                self.repo.record_failed_attempt(card.card_number, attempts, None)
                remaining = self.max_pin_attempts - attempts
                raise InvalidPINError(
                    f"Incorrect PIN. {remaining} attempt(s) remaining before card lockout."
                )

        # PIN is correct; reset failed attempts
        if card.failed_attempts > 0 or card.locked_until is not None:
            self.repo.reset_failed_attempts(card.card_number)

        return card

    def get_balance(self, card_number: str) -> int:
        card = self.repo.get_card(card_number)
        if not card:
            raise CardNotFoundError(f"Card '{card_number}' not found.")
        return self.bank.get_account(card.account_number).balance_cents

    def withdraw_cash(self, card_number: str, amount_cents: int) -> CashDispenseResult:
        """Process ATM withdrawal with banknotes, daily quota, and Bank debit."""
        card = self.repo.get_card(card_number)
        if not card:
            raise CardNotFoundError(f"Card '{card_number}' not found.")

        # 1. Banknote denomination decomposition
        dispense_result = calculate_banknotes(amount_cents)

        # 2. Daily limit enforcement
        today = self.clock.today_iso()
        already_withdrawn = self.repo.get_daily_withdrawn_cents(card.card_number, today)
        if already_withdrawn + amount_cents > self.daily_limit_cents:
            limit_str = cents_to_display(self.daily_limit_cents)
            used_str = cents_to_display(already_withdrawn)
            avail_str = cents_to_display(self.daily_limit_cents - already_withdrawn)
            raise DailyLimitExceededError(
                f"Daily withdrawal limit is {limit_str} (used: {used_str}). "
                f"Maximum remaining today: {avail_str}."
            )

        # 3. Delegate debit to Bank service (enforces balance/overdraft rules)
        self.bank.withdraw(card.account_number, amount_cents)

        # 4. Record daily ATM usage
        self.repo.record_daily_withdrawal(card.card_number, today, amount_cents)

        return dispense_result

    def deposit_cash(self, card_number: str, amount_cents: int) -> int:
        card = self.repo.get_card(card_number)
        if not card:
            raise CardNotFoundError(f"Card '{card_number}' not found.")
        return self.bank.deposit(card.account_number, amount_cents)

    def change_pin(self, card_number: str, old_pin: str, new_pin: str) -> None:
        card = self.authenticate(card_number, old_pin)

        new_pin_clean = new_pin.strip()
        if len(new_pin_clean) != 4 or not new_pin_clean.isdigit():
            raise ATMError("New PIN must be exactly 4 numeric digits.")

        if new_pin_clean == old_pin.strip():
            raise ATMError("New PIN cannot be identical to the current PIN.")

        new_hash, new_salt = hash_secret(new_pin_clean)
        self.repo.update_pin(card.card_number, new_hash, new_salt)

    def get_mini_statement(self, card_number: str, limit: int = 5) -> list[TransactionRecord]:
        card = self.repo.get_card(card_number)
        if not card:
            raise CardNotFoundError(f"Card '{card_number}' not found.")
        all_tx = self.bank.get_statement(card.account_number)
        return all_tx[-limit:]
