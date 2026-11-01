"""Seed script populating Contact Management System with clearly labeled fake demo data."""

from pathlib import Path

from projects.p01_contact_management.repository import ContactRepository
from projects.p01_contact_management.service import ContactService


def seed_database(service: ContactService) -> None:
    print("Seeding contacts database with clearly labeled fake demo data...")

    fake_contacts = [
        (
            "[FAKE] Sherlock Holmes",
            "+1-555-0101",
            "sherlock.fake@bakerstreet.example",
            "221B Baker St",
        ),
        ("[FAKE] John Watson", "+1-555-0102", "john.watson.fake@example.com", "221B Baker St"),
        ("[FAKE] Irene Adler", "+1-555-0103", "irene.adler.fake@example.com", "Briony Lodge"),
        ("[FAKE] Mycroft Holmes", "+1-555-0104", "mycroft.fake@diogenes.example", "Pall Mall"),
    ]

    for name, phone, email, address in fake_contacts:
        try:
            c = service.add_contact(name, phone, email, address)
            print(f"  Added demo contact: {c.name} (ID {c.id})")
        except Exception as e:
            print(f"  Skipped contact '{name}': {e}")

    print("Contact seeding complete!\n")


if __name__ == "__main__":
    db_path = Path(__file__).resolve().parent / "data" / "contacts.db"
    repo = ContactRepository.from_path(db_path)
    svc = ContactService(repo)
    seed_database(svc)
