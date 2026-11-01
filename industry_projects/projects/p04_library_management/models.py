"""Data models and entities for the Library Management System."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    """Represents a cataloged book with copy inventory."""

    isbn: str
    title: str
    author: str
    total_copies: int
    available_copies: int
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.isbn.strip():
            raise ValueError("ISBN cannot be empty.")
        if not self.title.strip():
            raise ValueError("Title cannot be empty.")
        if not self.author.strip():
            raise ValueError("Author cannot be empty.")
        if self.total_copies < 0:
            raise ValueError("Total copies cannot be negative.")
        if self.available_copies < 0 or self.available_copies > self.total_copies:
            raise ValueError(
                f"Available copies ({self.available_copies}) must be between 0 "
                f"and total copies ({self.total_copies})."
            )


@dataclass(frozen=True)
class Member:
    """Represents a registered library member."""

    member_code: str
    name: str
    email: str
    max_borrow_limit: int = 3
    created_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.member_code.strip():
            raise ValueError("Member code cannot be empty.")
        if not self.name.strip():
            raise ValueError("Member name cannot be empty.")
        if "@" not in self.email or "." not in self.email:
            raise ValueError(f"Invalid email address: '{self.email}'.")
        if self.max_borrow_limit <= 0:
            raise ValueError("Borrow limit must be greater than zero.")


@dataclass(frozen=True)
class Loan:
    """Represents a book borrowing transaction."""

    book_id: int
    member_id: int
    loan_date: str
    due_date: str
    return_date: str | None = None
    fine_cents: int = 0
    status: str = "ACTIVE"
    id: int | None = None


@dataclass(frozen=True)
class LoanDetail:
    """Composite projection for displaying loan details with book and member information."""

    loan_id: int
    book_id: int
    book_title: str
    book_isbn: str
    member_id: int
    member_name: str
    member_code: str
    loan_date: str
    due_date: str
    return_date: str | None
    fine_cents: int
    status: str
