"""Seed script populating ATM Management System with clearly labeled fake demo cards."""

from pathlib import Path

from projects.p02_bank_management.repository import BankRepository
from projects.p02_bank_management.service import BankService
from projects.p03_atm_management.repository import ATMRepository
from projects.p03_atm_management.service import ATMService


def seed_database(atm_service: ATMService, bank_service: BankService) -> None:
    print("Seeding ATM database with clearly labeled fake demo cards...")

    demo_email = "atm.user.fake@example.com"
    demo_card_num = "4000-1234-5678-9010"
    demo_pin = "1234"

    try:
        cust = bank_service.register_customer("[FAKE] ATM Demo User", demo_email)
        assert cust.id is not None
        acc = bank_service.open_account(cust.id, "SAVINGS", initial_deposit_cents=250000)
        print(f"  Created bank account: {acc.account_number} ($2,500.00)")
        card = atm_service.issue_card(demo_card_num, acc.account_number, demo_pin)
        print(f"  Issued demo card: {card.card_number} (PIN: {demo_pin})")
    except Exception as e:
        print(f"  Skipped demo card ({demo_card_num}): {e}")

    print("ATM seeding complete!\n")


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent / "data"
    b_repo = BankRepository.from_path(data_dir / "bank.db")
    b_svc = BankService(b_repo)

    a_repo = ATMRepository.from_path(data_dir / "atm.db")
    a_svc = ATMService(a_repo, b_svc)
    seed_database(a_svc, b_svc)
