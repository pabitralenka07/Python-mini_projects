"""CLI interface for Library Management System.

================================================================================
Concepts used:
1. Layered Architecture: The CLI never directly touches the database; it only
   communicates with LibraryService, keeping presentation separate from logic.
2. Clean Error Handling: Custom domain exceptions (e.g., BookUnavailableError)
   are caught gracefully to present user-friendly error banners.
3. Safe User Input: Wraps input to catch EOF (Ctrl+D) and KeyboardInterrupt,
   preventing abrupt Python crash tracebacks.
4. Tabular Text Output: Reusable table formatter dynamically structures data
   into neat, readable console columns.
================================================================================
"""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display
from common.tables import format_table
from projects.p04_library_management.repository import LibraryRepository
from projects.p04_library_management.service import (
    LibraryError,
    LibraryService,
)


def get_default_service() -> LibraryService:
    db_path = Path(__file__).resolve().parent / "data" / "library.db"
    repo = LibraryRepository.from_path(db_path)
    return LibraryService(repo)


def display_menu() -> None:
    print("\n" + "=" * 45)
    print("      LIBRARY MANAGEMENT SYSTEM (PILOT)      ")
    print("=" * 45)
    print(" 1. Add New Book")
    print(" 2. Search Books")
    print(" 3. List All Books")
    print(" 4. Register Member")
    print(" 5. List All Members")
    print(" 6. Issue Book (Borrow)")
    print(" 7. Return Book")
    print(" 8. View Active Loans")
    print(" 9. View Loan History")
    print(" 10. Delete Book")
    print(" 0. Exit")
    print("=" * 45)


def run_cli(service: LibraryService | None = None) -> None:
    if service is None:
        service = get_default_service()

    while True:
        try:
            display_menu()
            choice = prompt_int("Enter option (0-10)", min_val=0, max_val=10)
        except UserExitException:
            print("\nGoodbye! Exiting Library Management System.")
            break

        if choice == 0:
            print("\nGoodbye! Exiting Library Management System.")
            break

        try:
            if choice == 1:
                _handle_add_book(service)
            elif choice == 2:
                _handle_search_books(service)
            elif choice == 3:
                _handle_list_books(service)
            elif choice == 4:
                _handle_register_member(service)
            elif choice == 5:
                _handle_list_members(service)
            elif choice == 6:
                _handle_issue_book(service)
            elif choice == 7:
                _handle_return_book(service)
            elif choice == 8:
                _handle_list_loans(service, active_only=True)
            elif choice == 9:
                _handle_list_loans(service, active_only=False)
            elif choice == 10:
                _handle_delete_book(service)
        except UserExitException:
            print("\nReturning to main menu...")
        except LibraryError as err:
            print(f"\n[Library Error] {err}")
        except Exception as err:
            print(f"\n[Unexpected Error] An unexpected error occurred: {err}")


def _handle_add_book(service: LibraryService) -> None:
    print("\n--- Add New Book ---")
    isbn = safe_input("Enter ISBN: ")
    title = safe_input("Enter Title: ")
    author = safe_input("Enter Author: ")
    copies = prompt_int("Enter Total Copies", min_val=1, max_val=1000)

    book = service.add_book(isbn=isbn, title=title, author=author, total_copies=copies)
    print(f"\nSuccess: Book '{book.title}' cataloged with ID {book.id}!")


def _handle_search_books(service: LibraryService) -> None:
    print("\n--- Search Books ---")
    query = safe_input("Search term (Title, Author, or ISBN): ")
    books = service.search_books(query)

    headers = ["ID", "ISBN", "Title", "Author", "Total", "Available"]
    rows = [[b.id, b.isbn, b.title, b.author, b.total_copies, b.available_copies] for b in books]
    alignments = ["R", "L", "L", "L", "R", "R"]
    print(format_table(headers, rows, alignments))


def _handle_list_books(service: LibraryService) -> None:
    print("\n--- All Cataloged Books ---")
    books = service.list_books()
    headers = ["ID", "ISBN", "Title", "Author", "Total", "Available"]
    rows = [[b.id, b.isbn, b.title, b.author, b.total_copies, b.available_copies] for b in books]
    alignments = ["R", "L", "L", "L", "R", "R"]
    print(format_table(headers, rows, alignments))


def _handle_register_member(service: LibraryService) -> None:
    print("\n--- Register Member ---")
    code = safe_input("Enter Member Code (e.g., M001): ")
    name = safe_input("Enter Full Name: ")
    email = safe_input("Enter Email: ")
    limit = prompt_int("Borrow Limit", min_val=1, max_val=10, default=3)

    member = service.register_member(
        member_code=code, name=name, email=email, max_borrow_limit=limit
    )
    print(f"\nSuccess: Member '{member.name}' registered with ID {member.id}!")


def _handle_list_members(service: LibraryService) -> None:
    print("\n--- Registered Members ---")
    members = service.list_members()
    headers = ["ID", "Code", "Name", "Email", "Limit", "Joined"]
    rows = [
        [m.id, m.member_code, m.name, m.email, m.max_borrow_limit, m.created_at] for m in members
    ]
    alignments = ["R", "L", "L", "L", "R", "L"]
    print(format_table(headers, rows, alignments))


def _handle_issue_book(service: LibraryService) -> None:
    print("\n--- Issue Book (Borrow) ---")
    book_id = prompt_int("Enter Book ID", min_val=1)
    member_id = prompt_int("Enter Member ID", min_val=1)

    loan_id = service.issue_book(book_id=book_id, member_id=member_id)
    print(f"\nSuccess: Loan record created! Loan ID: {loan_id}. (Standard period: 14 days)")


def _handle_return_book(service: LibraryService) -> None:
    print("\n--- Return Book ---")
    loan_id = prompt_int("Enter Loan ID", min_val=1)
    overdue_days, fine_cents = service.return_book(loan_id)

    if overdue_days > 0:
        fine_display = cents_to_display(fine_cents)
        print(f"\nBook returned! Overdue by {overdue_days} days. Assessed Fine: {fine_display}.")
    else:
        print("\nBook returned on time! No fine assessed.")


def _handle_list_loans(service: LibraryService, active_only: bool) -> None:
    status_filter = "ACTIVE" if active_only else None
    title_label = "Active Loans" if active_only else "All Loans (History)"
    print(f"\n--- {title_label} ---")

    loans = service.list_loans(status=status_filter)
    headers = ["Loan ID", "Book Title", "Member", "Loan Date", "Due Date", "Status", "Fine"]
    rows = [
        [
            loan.loan_id,
            loan.book_title,
            f"{loan.member_name} ({loan.member_code})",
            loan.loan_date,
            loan.due_date,
            loan.status,
            cents_to_display(loan.fine_cents),
        ]
        for loan in loans
    ]
    alignments = ["R", "L", "L", "L", "L", "L", "R"]
    print(format_table(headers, rows, alignments))


def _handle_delete_book(service: LibraryService) -> None:
    print("\n--- Delete Book ---")
    book_id = prompt_int("Enter Book ID to delete", min_val=1)
    if not confirm_action(f"Are you sure you want to permanently delete Book ID {book_id}?"):
        print("Deletion cancelled.")
        return

    service.delete_book(book_id)
    print(f"\nSuccess: Book ID {book_id} deleted successfully.")
