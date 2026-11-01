"""Seed script populating Bank Management System with clearly labeled fake demo data."""

from pathlib import Path

from projects.p02_bank_management.repository import BankRepository
from projects.p02_bank_management.service import BankService


def seed_database(service: BankService) -> None:
    print("Seeding bank database with clearly labeled fake demo data...")

    fake_customers = [
        ("[FAKE] Bruce Wayne", "bruce.fake@waynecorp.example"),
        ("[FAKE] Clark Kent", "clark.fake@dailyplanet.example"),
        ("[FAKE] Diana Prince", "diana.fake@themyscira.example"),
    ]

    cust_ids: list[int] = []
    for name, email in fake_customers:
        try:
            c = service.register_customer(name, email)
            cust_ids.append(c.id)  # type: ignore[arg-type]
            print(f"  Added demo customer: {c.name} (ID {c.id})")
        except Exception as e:
            print(f"  Skipped customer '{name}': {e}")

    # Accounts
    if cust_ids:
        try:
            # Bruce: Savings with $5,000.00
            s_acc = service.open_account(cust_ids[0], "SAVINGS", initial_deposit_cents=500000)
            print(f"  Opened Savings: {s_acc.account_number} ($5,000.00)")

            # Clark: Current with $200.00
            c_acc = service.open_account(cust_ids[1], "CURRENT", initial_deposit_cents=20000)
            print(f"  Opened Current: {c_acc.account_number} ($200.00)")

            # Transfer demo: Bruce transfers $50.00 to Clark
            service.transfer(s_acc.account_number, c_acc.account_number, 5000)
            print(f"  Demo Transfer: $50.00 from {s_acc.account_number} to {c_acc.account_number}")
        except Exception as e:
            print(f"  Skipped demo transactions: {e}")

    print("Bank seeding complete!\n")


if __name__ == "__main__":
    db_path = Path(__file__).resolve().parent / "data" / "bank.db"
    repo = BankRepository.from_path(db_path)
    svc = BankService(repo)
    seed_database(svc)
