"""Database repository for Library Management System with relational integrity."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p04_library_management.models import Book, Loan, LoanDetail, Member

LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    total_copies INTEGER NOT NULL CHECK(total_copies >= 0),
    available_copies INTEGER NOT NULL
        CHECK(available_copies >= 0 AND available_copies <= total_copies)
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    max_borrow_limit INTEGER NOT NULL DEFAULT 3 CHECK(max_borrow_limit > 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    loan_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT,
    fine_cents INTEGER NOT NULL DEFAULT 0 CHECK(fine_cents >= 0),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'RETURNED'))
);

CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
CREATE INDEX IF NOT EXISTS idx_members_code ON members(member_code);
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);
"""


class LibraryRepository:
    """Encapsulates all SQL persistence for books, members, and loans."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "LibraryRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=LIBRARY_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    # --- Books ---

    def add_book(self, book: Book) -> Book:
        query = """
            INSERT INTO books (isbn, title, author, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (book.isbn, book.title, book.author, book.total_copies, book.available_copies),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for new book.")
            book_id = int(cursor.lastrowid)
        return Book(
            id=book_id,
            isbn=book.isbn,
            title=book.title,
            author=book.author,
            total_copies=book.total_copies,
            available_copies=book.available_copies,
        )

    def get_book_by_id(self, book_id: int) -> Book | None:
        query = (
            "SELECT id, isbn, title, author, total_copies, available_copies "
            "FROM books WHERE id = ?;"
        )
        with self.db.get_connection() as conn:
            row = conn.execute(query, (book_id,)).fetchone()
            if not row:
                return None
            return Book(
                id=row["id"],
                isbn=row["isbn"],
                title=row["title"],
                author=row["author"],
                total_copies=row["total_copies"],
                available_copies=row["available_copies"],
            )

    def get_book_by_isbn(self, isbn: str) -> Book | None:
        query = (
            "SELECT id, isbn, title, author, total_copies, available_copies "
            "FROM books WHERE isbn = ?;"
        )
        with self.db.get_connection() as conn:
            row = conn.execute(query, (isbn.strip(),)).fetchone()
            if not row:
                return None
            return Book(
                id=row["id"],
                isbn=row["isbn"],
                title=row["title"],
                author=row["author"],
                total_copies=row["total_copies"],
                available_copies=row["available_copies"],
            )

    def search_books(self, search_term: str) -> list[Book]:
        pattern = f"%{search_term.strip()}%"
        query = """
            SELECT id, isbn, title, author, total_copies, available_copies
            FROM books
            WHERE isbn LIKE ? OR title LIKE ? OR author LIKE ?
            ORDER BY title ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (pattern, pattern, pattern)).fetchall()
            return [
                Book(
                    id=row["id"],
                    isbn=row["isbn"],
                    title=row["title"],
                    author=row["author"],
                    total_copies=row["total_copies"],
                    available_copies=row["available_copies"],
                )
                for row in rows
            ]

    def list_books(self) -> list[Book]:
        query = """
            SELECT id, isbn, title, author, total_copies, available_copies
            FROM books
            ORDER BY title ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Book(
                    id=row["id"],
                    isbn=row["isbn"],
                    title=row["title"],
                    author=row["author"],
                    total_copies=row["total_copies"],
                    available_copies=row["available_copies"],
                )
                for row in rows
            ]

    def update_book_copies(self, book_id: int, total_copies: int, available_copies: int) -> None:
        query = """
            UPDATE books
            SET total_copies = ?, available_copies = ?
            WHERE id = ?;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (total_copies, available_copies, book_id))

    def delete_book(self, book_id: int) -> None:
        query = "DELETE FROM books WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (book_id,))

    # --- Members ---

    def add_member(self, member: Member) -> Member:
        query = """
            INSERT INTO members (member_code, name, email, max_borrow_limit, created_at)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    member.member_code,
                    member.name,
                    member.email,
                    member.max_borrow_limit,
                    member.created_at,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for new member.")
            member_id = int(cursor.lastrowid)
        return Member(
            id=member_id,
            member_code=member.member_code,
            name=member.name,
            email=member.email,
            max_borrow_limit=member.max_borrow_limit,
            created_at=member.created_at,
        )

    def get_member_by_id(self, member_id: int) -> Member | None:
        query = """
            SELECT id, member_code, name, email, max_borrow_limit, created_at
            FROM members WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (member_id,)).fetchone()
            if not row:
                return None
            return Member(
                id=row["id"],
                member_code=row["member_code"],
                name=row["name"],
                email=row["email"],
                max_borrow_limit=row["max_borrow_limit"],
                created_at=row["created_at"],
            )

    def get_member_by_code(self, member_code: str) -> Member | None:
        query = """
            SELECT id, member_code, name, email, max_borrow_limit, created_at
            FROM members WHERE member_code = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (member_code.strip(),)).fetchone()
            if not row:
                return None
            return Member(
                id=row["id"],
                member_code=row["member_code"],
                name=row["name"],
                email=row["email"],
                max_borrow_limit=row["max_borrow_limit"],
                created_at=row["created_at"],
            )

    def list_members(self) -> list[Member]:
        query = """
            SELECT id, member_code, name, email, max_borrow_limit, created_at
            FROM members ORDER BY name ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Member(
                    id=row["id"],
                    member_code=row["member_code"],
                    name=row["name"],
                    email=row["email"],
                    max_borrow_limit=row["max_borrow_limit"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    # --- Loans ---

    def create_loan(self, book_id: int, member_id: int, loan_date: str, due_date: str) -> int:
        """Create a loan record and atomically decrement available copies."""
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                """
                INSERT INTO loans (book_id, member_id, loan_date, due_date, status)
                VALUES (?, ?, ?, ?, 'ACTIVE');
                """,
                (book_id, member_id, loan_date, due_date),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for new loan.")
            loan_id = int(cursor.lastrowid)
            conn.execute(
                """
                UPDATE books
                SET available_copies = available_copies - 1
                WHERE id = ?;
                """,
                (book_id,),
            )
            return loan_id

    def get_loan_by_id(self, loan_id: int) -> Loan | None:
        query = """
            SELECT id, book_id, member_id, loan_date, due_date, return_date, fine_cents, status
            FROM loans WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (loan_id,)).fetchone()
            if not row:
                return None
            return Loan(
                id=row["id"],
                book_id=row["book_id"],
                member_id=row["member_id"],
                loan_date=row["loan_date"],
                due_date=row["due_date"],
                return_date=row["return_date"],
                fine_cents=row["fine_cents"],
                status=row["status"],
            )

    def get_active_loans_count_for_member(self, member_id: int) -> int:
        query = "SELECT COUNT(*) FROM loans WHERE member_id = ? AND status = 'ACTIVE';"
        with self.db.get_connection() as conn:
            val = conn.execute(query, (member_id,)).fetchone()[0]
            return int(val)

    def get_active_loans_for_book(self, book_id: int) -> list[Loan]:
        query = """
            SELECT id, book_id, member_id, loan_date, due_date, return_date, fine_cents, status
            FROM loans
            WHERE book_id = ? AND status = 'ACTIVE';
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (book_id,)).fetchall()
            return [
                Loan(
                    id=row["id"],
                    book_id=row["book_id"],
                    member_id=row["member_id"],
                    loan_date=row["loan_date"],
                    due_date=row["due_date"],
                    return_date=row["return_date"],
                    fine_cents=row["fine_cents"],
                    status=row["status"],
                )
                for row in rows
            ]

    def return_loan(self, loan_id: int, book_id: int, return_date: str, fine_cents: int) -> None:
        """Mark loan returned, record fine, and increment available copies atomically."""
        with self.db.get_connection() as conn, conn:
            conn.execute(
                """
                UPDATE loans
                SET status = 'RETURNED', return_date = ?, fine_cents = ?
                WHERE id = ?;
                """,
                (return_date, fine_cents, loan_id),
            )
            conn.execute(
                """
                UPDATE books
                SET available_copies = available_copies + 1
                WHERE id = ?;
                """,
                (book_id,),
            )

    def list_loans(self, status: str | None = None) -> list[LoanDetail]:
        base_query = """
            SELECT
                l.id AS loan_id,
                b.id AS book_id,
                b.title AS book_title,
                b.isbn AS book_isbn,
                m.id AS member_id,
                m.name AS member_name,
                m.member_code AS member_code,
                l.loan_date,
                l.due_date,
                l.return_date,
                l.fine_cents,
                l.status
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN members m ON l.member_id = m.id
        """
        params: list[str] = []
        if status:
            base_query += " WHERE l.status = ?"
            params.append(status)
        base_query += " ORDER BY l.id DESC;"

        with self.db.get_connection() as conn:
            rows = conn.execute(base_query, params).fetchall()
            return [
                LoanDetail(
                    loan_id=row["loan_id"],
                    book_id=row["book_id"],
                    book_title=row["book_title"],
                    book_isbn=row["book_isbn"],
                    member_id=row["member_id"],
                    member_name=row["member_name"],
                    member_code=row["member_code"],
                    loan_date=row["loan_date"],
                    due_date=row["due_date"],
                    return_date=row["return_date"],
                    fine_cents=row["fine_cents"],
                    status=row["status"],
                )
                for row in rows
            ]
