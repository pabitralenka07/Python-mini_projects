"""Seed script populating Library Management System with clearly labeled fake demo data."""

from pathlib import Path

from projects.p04_library_management.repository import LibraryRepository
from projects.p04_library_management.service import LibraryService


def seed_database(service: LibraryService) -> None:
    print("Seeding database with clearly labeled fake demo data...")

    books = [
        ("978-0-FAKE-001", "[FAKE] The Pragmatic Pythonist", "Arthur Pendelton (Fictional)", 5),
        ("978-0-FAKE-002", "[FAKE] Algorithms in Wonderland", "Lewis Carroll Jr. (Fictional)", 3),
        ("978-0-FAKE-003", "[FAKE] Clean Architecture Chronicles", "Robert Martin (Simulated)", 2),
        ("978-0-FAKE-004", "[FAKE] Relational Design Patterns", "Edgar Codd (Simulated)", 4),
    ]

    book_ids: list[int] = []
    for isbn, title, author, copies in books:
        try:
            b = service.add_book(isbn, title, author, copies)
            book_ids.append(b.id)
            print(f"  Added fake book: {b.title} (ID {b.id})")
        except Exception as e:
            print(f"  Skipped book '{title}': {e}")

    members = [
        ("MEM-901", "[FAKE] Alice Wonder", "alice.fake@example.com", 3),
        ("MEM-902", "[FAKE] Bob Builder", "bob.fake@example.com", 2),
        ("MEM-903", "[FAKE] Charlie Chaplin", "charlie.fake@example.com", 3),
    ]

    member_ids: list[int] = []
    for code, name, email, limit in members:
        try:
            m = service.register_member(code, name, email, limit)
            member_ids.append(m.id)
            print(f"  Added fake member: {m.name} (ID {m.id})")
        except Exception as e:
            print(f"  Skipped member '{name}': {e}")

    if book_ids and member_ids:
        try:
            loan_id = service.issue_book(book_ids[0], member_ids[0])
            print(f"  Demo loan: Book {book_ids[0]} -> Member {member_ids[0]} (Loan {loan_id})")
        except Exception as e:
            print(f"  Skipped demo loan: {e}")

    print("Seeding complete!\n")


if __name__ == "__main__":
    db_path = Path(__file__).resolve().parent / "data" / "library.db"
    repo = LibraryRepository.from_path(db_path)
    svc = LibraryService(repo)
    seed_database(svc)
