"""Seed script for Electricity Bill Management System with sample consumers and invoices."""

from pathlib import Path

from projects.p09_electricity_bill.repository import ElectricityRepository
from projects.p09_electricity_bill.service import (
    ElectricityService,
    NonMonotonicReadingError,
)


def seed_data(repo: ElectricityRepository | None = None) -> None:
    if repo is None:
        db_path = Path(__file__).resolve().parent / "data" / "electricity.db"
        repo = ElectricityRepository.from_path(db_path)

    service = ElectricityService(repo)
    print("Seeding Electricity Bill Management System...")

    consumers = service.list_consumers()
    c_map: dict[str, int] = {c.consumer_number: c.id for c in consumers if c.id is not None}

    if not c_map:
        c1 = service.register_consumer(
            consumer_number="CON-1001",
            name="Alice Walker",
            address="124 Elm Street, Springfield",
            meter_number="MTR-8801",
            tariff_category="RESIDENTIAL",
            initial_reading=100,
        )
        c2 = service.register_consumer(
            consumer_number="CON-1002",
            name="Bob Vance Refrigeration",
            address="450 Corporate Pkwy, Scranton",
            meter_number="MTR-8802",
            tariff_category="COMMERCIAL",
            initial_reading=500,
        )
        c3 = service.register_consumer(
            consumer_number="CON-1003",
            name="Carol Danvers",
            address="77 Sunset Blvd, Los Angeles",
            meter_number="MTR-8803",
            tariff_category="RESIDENTIAL",
            initial_reading=0,
        )
        if c1.id and c2.id and c3.id:
            c_map["CON-1001"] = c1.id
            c_map["CON-1002"] = c2.id
            c_map["CON-1003"] = c3.id
        print(" -> Registered consumers CON-1001, CON-1002, and CON-1003.")
    else:
        print(f" -> Consumers already exist ({len(c_map)} found).")

    bills = repo.list_all_bill_details()
    if not bills and "CON-1001" in c_map and "CON-1002" in c_map:
        try:
            b1 = service.generate_bill(c_map["CON-1001"], current_reading=350)
            if b1.id is not None:
                service.pay_bill(b1.id)
                print(f" -> Generated and settled Bill #{b1.bill_number} for Alice Walker.")

            b2 = service.generate_bill(c_map["CON-1002"], current_reading=850)
            print(f" -> Generated pending Bill #{b2.bill_number} for Bob Vance Refrigeration.")
        except NonMonotonicReadingError:
            pass
    else:
        print(f" -> Invoices already exist ({len(bills)} found).")

    print("Electricity Bill Management System seeding complete.")


if __name__ == "__main__":
    seed_data()
