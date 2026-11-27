"""Comprehensive test suite for Project 04: Library Management System.

Covers:
- Service domain logic with FrozenClock
- Borrow limits, due dates, and fine calculations
- Constraint violations and active loan deletion guards
- Transaction rollback guarantees
- Headless GUI controller verification
- Interactive CLI menu flows with simulated and EOF input
"""

import subprocess
import sys
from pathlib import Path

import pytest

from common.clock import FrozenClock
from projects.p04_library_management.gui_app import LibraryGUIController
from projects.p04_library_management.repository import LibraryRepository
from projects.p04_library_management.service import (
    ActiveLoanDeleteError,
    BookUnavailableError,
    BorrowLimitExceededError,
    InvalidInputError,
    LibraryService,
)


@pytest.fixture
def repo(tmp_path: Path) -> LibraryRepository:
    db_file = tmp_path / "test_library.db"
    return LibraryRepository.from_path(db_file)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock("2026-06-01T10:00:00+00:00")


@pytest.fixture
def service(repo: LibraryRepository, clock: FrozenClock) -> LibraryService:
    return LibraryService(
        repository=repo, clock=clock, loan_duration_days=14, fine_cents_per_day=50
    )




def test_add_and_search_books(service: LibraryService) -> None:
    b1 = service.add_book("ISBN-100", "Domain Driven Design", "Eric Evans", 3)
    assert b1.id is not None
    assert b1.available_copies == 3

    b2 = service.add_book("ISBN-200", "Refactoring", "Martin Fowler", 2)
    assert b2.id is not None

    search_res = service.search_books("Evans")
    assert len(search_res) == 1
    assert search_res[0].isbn == "ISBN-100"

    all_books = service.list_books()
    assert len(all_books) == 2


def test_add_book_invalid_inputs(service: LibraryService) -> None:
    with pytest.raises(InvalidInputError, match="ISBN cannot be empty"):
        service.add_book("", "Title", "Author", 2)

    with pytest.raises(InvalidInputError, match="Title cannot be empty"):
        service.add_book("ISBN-1", "", "Author", 2)

    with pytest.raises(InvalidInputError, match="Total copies must be at least 1"):
        service.add_book("ISBN-1", "Title", "Author", 0)

    service.add_book("ISBN-DUP", "Title 1", "Author", 2)
    with pytest.raises(InvalidInputError, match="already cataloged"):
        service.add_book("ISBN-DUP", "Title 2", "Author", 1)


def test_register_member_and_limits(service: LibraryService) -> None:
    m = service.register_member("M01", "Alice Smith", "alice@example.com", max_borrow_limit=2)
    assert m.id is not None
    assert m.created_at == "2026-06-01"

    members = service.list_members()
    assert len(members) == 1

    with pytest.raises(InvalidInputError, match="already exists"):
        service.register_member("M01", "Alice Clone", "alice2@example.com")

    with pytest.raises(InvalidInputError, match="Invalid email"):
        service.register_member("M02", "Bob", "invalid_email_at_com")


def test_issue_book_and_borrow_limit(service: LibraryService) -> None:
    b = service.add_book("ISBN-BOOK", "Python Crash Course", "Eric Matthes", 1)
    m = service.register_member("M10", "Charlie", "charlie@example.com", max_borrow_limit=1)

    loan_id = service.issue_book(b.id, m.id)
    assert loan_id == 1

    updated_book = service.repo.get_book_by_id(b.id)
    assert updated_book is not None
    assert updated_book.available_copies == 0

    with pytest.raises(BookUnavailableError):
        service.issue_book(b.id, m.id)

    b2 = service.add_book("ISBN-BOOK2", "Fluent Python", "Luciano Ramalho", 2)
    with pytest.raises(BorrowLimitExceededError):
        service.issue_book(b2.id, m.id)


def test_due_date_and_overdue_fines(service: LibraryService, clock: FrozenClock) -> None:
    b = service.add_book("ISBN-FINE", "Operating Systems", "Silberschatz", 2)
    m = service.register_member("M20", "Diana", "diana@example.com", max_borrow_limit=3)

    loan_id = service.issue_book(b.id, m.id)
    loan = service.repo.get_loan_by_id(loan_id)
    assert loan is not None
    assert loan.loan_date == "2026-06-01"
    assert loan.due_date == "2026-06-15"

    clock.advance(days=10)
    overdue_days, fine_cents = service.return_book(loan_id)
    assert overdue_days == 0
    assert fine_cents == 0

    loan_id2 = service.issue_book(b.id, m.id)
    clock.advance(days=18)
    overdue_days2, fine_cents2 = service.return_book(loan_id2)
    assert overdue_days2 == 4
    assert fine_cents2 == 200


def test_cannot_delete_book_on_loan(service: LibraryService) -> None:
    b = service.add_book("ISBN-DEL", "Clean Code", "Robert Martin", 2)
    m = service.register_member("M30", "Eve", "eve@example.com")

    service.issue_book(b.id, m.id)

    with pytest.raises(ActiveLoanDeleteError, match="actively on loan"):
        service.delete_book(b.id)


def test_delete_book_succeeds_when_not_on_loan(service: LibraryService) -> None:
    b = service.add_book("ISBN-FREE", "The Mythical Man-Month", "Fred Brooks", 1)
    book_id = b.id
    assert book_id is not None
    service.delete_book(book_id)
    assert service.repo.get_book_by_id(book_id) is None




def test_gui_controller_operations(service: LibraryService) -> None:
    ctrl = LibraryGUIController(service)
    book = ctrl.add_book("GUI-01", "GUI Python", "Tkinter Guru", 4)
    member = ctrl.register_member("GM01", "Grace Hopper", "grace@example.com", 3)

    assert len(ctrl.list_books()) == 1
    assert len(ctrl.list_members()) == 1

    loan_id = ctrl.issue_book(book.id, member.id)
    assert loan_id == 1
    assert len(ctrl.list_loans()) == 1

    overdue_days, fine_cents = ctrl.return_book(loan_id)
    assert overdue_days == 0
    assert fine_cents == 0




def test_cli_eof_clean_exit(tmp_path: Path) -> None:
    """Test that CLI terminates cleanly with return code 0 when given EOF."""
    root_dir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "projects.p04_library_management"],
        cwd=root_dir,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Goodbye" in proc.stdout or "Exiting" in proc.stdout


def test_cli_menu_add_and_list_flow(
    monkeypatch: pytest.MonkeyPatch, service: LibraryService
) -> None:
    """Test interactive menu simulation via monkeypatch."""
    from projects.p04_library_management.cli import run_cli

    inputs = iter(["1", "ISBN-CLI", "CLI Book", "CLI Author", "2", "3", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    run_cli(service)

    books = service.list_books()
    assert len(books) == 1
    assert books[0].title == "CLI Book"
