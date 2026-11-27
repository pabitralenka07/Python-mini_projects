"""Service layer for Library Management System encapsulating business logic."""

from datetime import date, timedelta

from common.clock import Clock, SystemClock
from projects.p04_library_management.models import Book, LoanDetail, Member
from projects.p04_library_management.repository import LibraryRepository


class LibraryError(Exception):
    """Base exception for library service business rule violations."""

    pass


class BookNotFoundError(LibraryError):
    """Raised when a requested book is not found."""

    pass


class MemberNotFoundError(LibraryError):
    """Raised when a requested member is not found."""

    pass


class BookUnavailableError(LibraryError):
    """Raised when no copies of the requested book are available for loan."""

    pass


class BorrowLimitExceededError(LibraryError):
    """Raised when a member has reached or exceeded their maximum loan limit."""

    pass


class ActiveLoanDeleteError(LibraryError):
    """Raised when attempting to delete a book that currently has active loans."""

    pass


class InvalidInputError(LibraryError):
    """Raised when input parameters fail domain validation rules."""

    pass


class LoanNotFoundError(LibraryError):
    """Raised when a requested loan record does not exist or is already returned."""

    pass


class LibraryService:
    """Orchestrates library domain logic, fine computations, and transactional workflows."""

    def __init__(
        self,
        repository: LibraryRepository,
        clock: Clock | None = None,
        loan_duration_days: int = 14,
        fine_cents_per_day: int = 50,
    ) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()
        self.loan_duration_days = loan_duration_days
        self.fine_cents_per_day = fine_cents_per_day


    def add_book(self, isbn: str, title: str, author: str, total_copies: int) -> Book:
        isbn = isbn.strip()
        title = title.strip()
        author = author.strip()

        if not isbn:
            raise InvalidInputError("ISBN cannot be empty.")
        if not title:
            raise InvalidInputError("Title cannot be empty.")
        if not author:
            raise InvalidInputError("Author cannot be empty.")
        if total_copies < 1:
            raise InvalidInputError("Total copies must be at least 1.")

        existing = self.repo.get_book_by_isbn(isbn)
        if existing is not None:
            raise InvalidInputError(f"A book with ISBN '{isbn}' is already cataloged.")

        book = Book(
            isbn=isbn,
            title=title,
            author=author,
            total_copies=total_copies,
            available_copies=total_copies,
        )
        return self.repo.add_book(book)

    def search_books(self, query: str) -> list[Book]:
        return self.repo.search_books(query)

    def list_books(self) -> list[Book]:
        return self.repo.list_books()

    def delete_book(self, book_id: int) -> None:
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise BookNotFoundError(f"Book with ID {book_id} not found.")

        active_loans = self.repo.get_active_loans_for_book(book_id)
        if active_loans:
            err = (
                f"Cannot delete book '{book.title}': "
                f"{len(active_loans)} copy/copies are actively on loan."
            )
            raise ActiveLoanDeleteError(err)

        self.repo.delete_book(book_id)


    def register_member(
        self, member_code: str, name: str, email: str, max_borrow_limit: int = 3
    ) -> Member:
        member_code = member_code.strip()
        name = name.strip()
        email = email.strip()

        if not member_code:
            raise InvalidInputError("Member code cannot be empty.")
        if not name:
            raise InvalidInputError("Name cannot be empty.")
        if "@" not in email or "." not in email:
            raise InvalidInputError(f"Invalid email address '{email}'.")
        if max_borrow_limit <= 0:
            raise InvalidInputError("Maximum borrow limit must be positive.")

        existing = self.repo.get_member_by_code(member_code)
        if existing is not None:
            raise InvalidInputError(f"Member code '{member_code}' already exists.")

        member = Member(
            member_code=member_code,
            name=name,
            email=email,
            max_borrow_limit=max_borrow_limit,
            created_at=self.clock.today_iso(),
        )
        return self.repo.add_member(member)

    def list_members(self) -> list[Member]:
        return self.repo.list_members()


    def issue_book(self, book_id: int, member_id: int) -> int:
        """Issue a book to a member, enforcing borrow limits and available inventory."""
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise BookNotFoundError(f"Book ID {book_id} does not exist.")

        if book.available_copies <= 0:
            raise BookUnavailableError(f"No copies of '{book.title}' are currently available.")

        member = self.repo.get_member_by_id(member_id)
        if not member:
            raise MemberNotFoundError(f"Member ID {member_id} does not exist.")

        active_count = self.repo.get_active_loans_count_for_member(member_id)
        if active_count >= member.max_borrow_limit:
            raise BorrowLimitExceededError(
                f"Member '{member.name}' has reached their borrow limit of "
                f"{member.max_borrow_limit} books."
            )

        loan_date = self.clock.today_iso()
        loan_dt = date.fromisoformat(loan_date)
        due_dt = loan_dt + timedelta(days=self.loan_duration_days)
        due_date = due_dt.isoformat()

        return self.repo.create_loan(
            book_id=book_id,
            member_id=member_id,
            loan_date=loan_date,
            due_date=due_date,
        )

    def return_book(self, loan_id: int) -> tuple[int, int]:
        """Process book return, calculate overdue days and fine, and restore copy."""
        loan = self.repo.get_loan_by_id(loan_id)
        if not loan:
            raise LoanNotFoundError(f"Loan ID {loan_id} not found.")

        if loan.status != "ACTIVE":
            raise LoanNotFoundError(f"Loan ID {loan_id} has already been returned.")

        return_date = self.clock.today_iso()
        return_dt = date.fromisoformat(return_date)
        due_dt = date.fromisoformat(loan.due_date)

        overdue_days = max(0, (return_dt - due_dt).days)
        fine_cents = overdue_days * self.fine_cents_per_day

        self.repo.return_loan(
            loan_id=loan_id,
            book_id=loan.book_id,
            return_date=return_date,
            fine_cents=fine_cents,
        )
        return overdue_days, fine_cents

    def list_loans(self, status: str | None = None) -> list[LoanDetail]:
        return self.repo.list_loans(status=status)
