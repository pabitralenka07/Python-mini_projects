"""CLI interface for ATM Management System.

================================================================================
Concepts used:
1. Reusing Shared Service Layers: Directly imports BankService and BankRepository
   rather than duplicating account ledger code, demonstrating code reuse.
2. Cryptographic Salting & Hashing: Educational scrypt hashing with per-user salt
   and constant-time comparison prevents timing attacks.
3. Denomination Dispensing: Greedy banknote partition algorithm decomposes
   requested withdrawal amounts into available physical currency bills.
4. Input Masking: Uses getpass to hide PIN characters during terminal entry.
================================================================================
"""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display, parse_money_to_cents
from common.security import prompt_password
from common.tables import format_table
from projects.p02_bank_management.repository import BankRepository
from projects.p02_bank_management.service import BankError, BankService
from projects.p03_atm_management.models import ATMCard
from projects.p03_atm_management.repository import ATMRepository
from projects.p03_atm_management.service import ATMError, ATMService


def get_default_service() -> ATMService:
    data_dir = Path(__file__).resolve().parent / "data"
    bank_db = data_dir / "bank.db"
    atm_db = data_dir / "atm.db"

    bank_repo = BankRepository.from_path(bank_db)
    bank_service = BankService(bank_repo)

    atm_repo = ATMRepository.from_path(atm_db)
    return ATMService(atm_repository=atm_repo, bank_service=bank_service)


def display_educational_banner() -> None:
    print("\n" + "=" * 55)
    print("      AUTOMATED TELLER MACHINE (ATM SIMULATION)      ")
    print("  [EDUCATIONAL SIMULATION ONLY - NOT PRODUCTION AUTH] ")
    print("=" * 55)


def display_session_menu(card: ATMCard) -> None:
    masked_card = (
        f"****-****-****-{card.card_number[-4:]}"
        if len(card.card_number) >= 4
        else card.card_number
    )
    print("\n" + "-" * 40)
    print(f" CARD INSERTED: {masked_card}")
    print("-" * 40)
    print(" 1. Check Balance")
    print(" 2. Withdraw Cash (Dispense Notes)")
    print(" 3. Deposit Cash")
    print(" 4. Mini Statement (Last 5 Transactions)")
    print(" 5. Change PIN")
    print(" 0. Eject Card / Finish Session")
    print("-" * 40)


def run_cli(service: ATMService | None = None) -> None:
    if service is None:
        service = get_default_service()

    display_educational_banner()

    while True:
        try:
            print("\nPlease insert your card to begin.")
            print("(Type 'exit' or 0 to quit)")
            card_num = safe_input("Enter Card Number: ")
            if card_num.lower() in ("exit", "quit", "0"):
                print("\nATM session terminated. Have a nice day!")
                break

            pin = prompt_password("Enter 4-Digit PIN: ")
            card = service.authenticate(card_num, pin)
            print("\nPIN Verified. Welcome to your account!")
            _run_card_session(service, card)

        except UserExitException:
            print("\nSession aborted. Ejecting card...")
            break
        except ATMError as err:
            print(f"\n[ATM Security Notice] {err}")
        except Exception as err:
            print(f"\n[System Error] {err}")


def _run_card_session(service: ATMService, card: ATMCard) -> None:
    while True:
        try:
            display_session_menu(card)
            choice = prompt_int("Select option (0-5)", min_val=0, max_val=5)
        except UserExitException:
            print("\nCard ejected. Thank you for banking with us!")
            break

        if choice == 0:
            print("\nCard ejected. Thank you for banking with us!")
            break

        try:
            if choice == 1:
                _handle_balance(service, card)
            elif choice == 2:
                _handle_withdraw(service, card)
            elif choice == 3:
                _handle_deposit(service, card)
            elif choice == 4:
                _handle_mini_statement(service, card)
            elif choice == 5:
                _handle_change_pin(service, card)
        except UserExitException:
            print("\nAction cancelled. Returning to ATM menu...")
        except (ATMError, BankError) as err:
            print(f"\n[Transaction Declined] {err}")
        except ValueError as err:
            print(f"\n[Invalid Input] {err}")


def _handle_balance(service: ATMService, card: ATMCard) -> None:
    bal_cents = service.get_balance(card.card_number)
    print(f"\nAvailable Balance: {cents_to_display(bal_cents)}")


def _handle_withdraw(service: ATMService, card: ATMCard) -> None:
    print("\n--- Cash Withdrawal ---")
    print("Available note denominations: $100, $50, $20, $10 (Multiples of $10 only)")
    amt_str = safe_input("Enter amount to withdraw (e.g. $80): ")
    cents = parse_money_to_cents(amt_str)

    dispense = service.withdraw_cash(card.card_number, cents)
    print("\n=== CASH DISPENSED ===")
    print(f"Total: {cents_to_display(dispense.total_cents)}")
    print(f"Banknotes: {dispense.summary()}")
    print("Please take your cash from the dispensing slot.")


def _handle_deposit(service: ATMService, card: ATMCard) -> None:
    print("\n--- Cash Deposit ---")
    amt_str = safe_input("Enter deposit amount: ")
    cents = parse_money_to_cents(amt_str)

    new_bal = service.deposit_cash(card.card_number, cents)
    print(f"\nDeposit Complete! Updated Balance: {cents_to_display(new_bal)}")


def _handle_mini_statement(service: ATMService, card: ATMCard) -> None:
    print("\n--- Mini Statement (Last 5 Transactions) ---")
    records = service.get_mini_statement(card.card_number, limit=5)
    headers = ["Type", "Amount", "Balance After", "Timestamp"]
    rows = [
        [
            r.transaction_type,
            cents_to_display(r.amount_cents),
            cents_to_display(r.balance_after_cents),
            r.timestamp,
        ]
        for r in records
    ]
    alignments = ["L", "R", "R", "L"]
    print(format_table(headers, rows, alignments))


def _handle_change_pin(service: ATMService, card: ATMCard) -> None:
    print("\n--- Change Card PIN ---")
    old_pin = prompt_password("Enter Current PIN: ")
    new_pin = prompt_password("Enter New 4-Digit PIN: ")
    confirm_pin = prompt_password("Confirm New 4-Digit PIN: ")

    if new_pin != confirm_pin:
        print("\nError: New PIN and Confirmation do not match.")
        return

    service.change_pin(card.card_number, old_pin, new_pin)
    print("\nSuccess: Your PIN has been successfully changed!")
