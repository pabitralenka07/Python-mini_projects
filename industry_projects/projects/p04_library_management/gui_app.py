"""Level 2 Tkinter Graphical User Interface for Library Management System.

================================================================================
Concepts used:
1. Separation of Concerns: The GUI controller calls the identical LibraryService
   business methods used by the CLI, ensuring zero business logic duplication.
2. Event-Driven Architecture: Tkinter event loop handles button clicks, table
   selections, and tab navigation.
3. Headless Testability: LibraryGUIController operates independently of the UI
   display, allowing 100% automated test coverage without a virtual display.
================================================================================
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from common.money import cents_to_display
from projects.p04_library_management.models import Book, LoanDetail, Member
from projects.p04_library_management.repository import LibraryRepository
from projects.p04_library_management.service import (
    LibraryError,
    LibraryService,
)


class LibraryGUIController:
    """Controller mediating between UI widgets and the LibraryService layer."""

    def __init__(self, service: LibraryService) -> None:
        self.service = service

    def add_book(self, isbn: str, title: str, author: str, total_copies: int) -> Book:
        return self.service.add_book(isbn, title, author, total_copies)

    def list_books(self) -> list[Book]:
        return self.service.list_books()

    def search_books(self, query: str) -> list[Book]:
        return self.service.search_books(query)

    def delete_book(self, book_id: int) -> None:
        self.service.delete_book(book_id)

    def register_member(
        self, member_code: str, name: str, email: str, max_borrow_limit: int
    ) -> Member:
        return self.service.register_member(member_code, name, email, max_borrow_limit)

    def list_members(self) -> list[Member]:
        return self.service.list_members()

    def issue_book(self, book_id: int, member_id: int) -> int:
        return self.service.issue_book(book_id, member_id)

    def return_book(self, loan_id: int) -> tuple[int, int]:
        return self.service.return_book(loan_id)

    def list_loans(self, status: str | None = None) -> list[LoanDetail]:
        return self.service.list_loans(status=status)


class LibraryGUIApp:
    """Tkinter Desktop Window for the Library Management System."""

    def __init__(self, root: tk.Tk, controller: LibraryGUIController) -> None:
        self.root = root
        self.controller = controller
        self.root.title("Library Management System (Pilot)")
        self.root.geometry("880x600")

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Books
        self.books_tab = ttk.Frame(notebook)
        notebook.add(self.books_tab, text="Books Catalog")
        self._build_books_tab()

        # Tab 2: Members
        self.members_tab = ttk.Frame(notebook)
        notebook.add(self.members_tab, text="Members")
        self._build_members_tab()

        # Tab 3: Loans
        self.loans_tab = ttk.Frame(notebook)
        notebook.add(self.loans_tab, text="Loans & Returns")
        self._build_loans_tab()

    # --- Books Tab ---

    def _build_books_tab(self) -> None:
        top_frame = ttk.LabelFrame(self.books_tab, text="Add / Search Book")
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="ISBN:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_isbn = ttk.Entry(top_frame, width=15)
        self.entry_isbn.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(top_frame, text="Title:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_title = ttk.Entry(top_frame, width=20)
        self.entry_title.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(top_frame, text="Author:").grid(row=0, column=4, padx=5, pady=5)
        self.entry_author = ttk.Entry(top_frame, width=15)
        self.entry_author.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(top_frame, text="Copies:").grid(row=1, column=0, padx=5, pady=5)
        self.entry_copies = ttk.Entry(top_frame, width=10)
        self.entry_copies.insert(0, "1")
        self.entry_copies.grid(row=1, column=1, padx=5, pady=5)

        btn_add = ttk.Button(top_frame, text="Add Book", command=self._on_add_book)
        btn_add.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(top_frame, text="Search:").grid(row=1, column=4, padx=5, pady=5)
        self.entry_search = ttk.Entry(top_frame, width=15)
        self.entry_search.grid(row=1, column=5, padx=5, pady=5)
        btn_search = ttk.Button(top_frame, text="Find", command=self._on_search_books)
        btn_search.grid(row=1, column=6, padx=5, pady=5)

        # Treeview
        tree_frame = ttk.Frame(self.books_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("id", "isbn", "title", "author", "total", "available")
        self.books_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.books_tree.heading("id", text="ID")
        self.books_tree.heading("isbn", text="ISBN")
        self.books_tree.heading("title", text="Title")
        self.books_tree.heading("author", text="Author")
        self.books_tree.heading("total", text="Total")
        self.books_tree.heading("available", text="Available")

        self.books_tree.column("id", width=40, anchor=tk.CENTER)
        self.books_tree.column("isbn", width=120)
        self.books_tree.column("title", width=220)
        self.books_tree.column("author", width=160)
        self.books_tree.column("total", width=60, anchor=tk.CENTER)
        self.books_tree.column("available", width=70, anchor=tk.CENTER)
        self.books_tree.pack(fill=tk.BOTH, expand=True)

        btn_delete = ttk.Button(
            self.books_tab, text="Delete Selected Book", command=self._on_delete_book
        )
        btn_delete.pack(pady=5)

    def _on_add_book(self) -> None:
        isbn = self.entry_isbn.get().strip()
        title = self.entry_title.get().strip()
        author = self.entry_author.get().strip()
        try:
            copies = int(self.entry_copies.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Copies must be a positive integer.")
            return

        try:
            book = self.controller.add_book(isbn, title, author, copies)
            messagebox.showinfo("Success", f"Book '{book.title}' added successfully!")
            self.refresh_books()
            self.entry_isbn.delete(0, tk.END)
            self.entry_title.delete(0, tk.END)
            self.entry_author.delete(0, tk.END)
        except LibraryError as err:
            messagebox.showerror("Error", str(err))

    def _on_search_books(self) -> None:
        query = self.entry_search.get().strip()
        books = self.controller.search_books(query) if query else self.controller.list_books()
        self._populate_books_tree(books)

    def _on_delete_book(self) -> None:
        selected = self.books_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a book to delete.")
            return
        item = self.books_tree.item(selected[0])
        book_id = int(item["values"][0])
        title = item["values"][2]

        if not messagebox.askyesno("Confirm", f"Permanently delete '{title}' (ID {book_id})?"):
            return

        try:
            self.controller.delete_book(book_id)
            messagebox.showinfo("Success", f"Book '{title}' deleted.")
            self.refresh_books()
        except LibraryError as err:
            messagebox.showerror("Error", str(err))

    # --- Members Tab ---

    def _build_members_tab(self) -> None:
        form_frame = ttk.LabelFrame(self.members_tab, text="Register Member")
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="Code:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_member_code = ttk.Entry(form_frame, width=10)
        self.entry_member_code.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_member_name = ttk.Entry(form_frame, width=20)
        self.entry_member_name.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form_frame, text="Email:").grid(row=0, column=4, padx=5, pady=5)
        self.entry_member_email = ttk.Entry(form_frame, width=25)
        self.entry_member_email.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(form_frame, text="Limit:").grid(row=0, column=6, padx=5, pady=5)
        self.entry_member_limit = ttk.Entry(form_frame, width=5)
        self.entry_member_limit.insert(0, "3")
        self.entry_member_limit.grid(row=0, column=7, padx=5, pady=5)

        btn_reg = ttk.Button(form_frame, text="Register", command=self._on_register_member)
        btn_reg.grid(row=0, column=8, padx=10, pady=5)

        # Members Treeview
        columns = ("id", "code", "name", "email", "limit", "joined")
        self.members_tree = ttk.Treeview(self.members_tab, columns=columns, show="headings")
        self.members_tree.heading("id", text="ID")
        self.members_tree.heading("code", text="Member Code")
        self.members_tree.heading("name", text="Name")
        self.members_tree.heading("email", text="Email")
        self.members_tree.heading("limit", text="Borrow Limit")
        self.members_tree.heading("joined", text="Joined Date")

        self.members_tree.column("id", width=50, anchor=tk.CENTER)
        self.members_tree.column("code", width=100)
        self.members_tree.column("name", width=180)
        self.members_tree.column("email", width=200)
        self.members_tree.column("limit", width=80, anchor=tk.CENTER)
        self.members_tree.column("joined", width=100)
        self.members_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _on_register_member(self) -> None:
        code = self.entry_member_code.get().strip()
        name = self.entry_member_name.get().strip()
        email = self.entry_member_email.get().strip()
        try:
            limit = int(self.entry_member_limit.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Borrow limit must be an integer.")
            return

        try:
            member = self.controller.register_member(code, name, email, limit)
            messagebox.showinfo("Success", f"Member '{member.name}' registered!")
            self.refresh_members()
            self.entry_member_code.delete(0, tk.END)
            self.entry_member_name.delete(0, tk.END)
            self.entry_member_email.delete(0, tk.END)
        except LibraryError as err:
            messagebox.showerror("Error", str(err))

    # --- Loans Tab ---

    def _build_loans_tab(self) -> None:
        ops_frame = ttk.LabelFrame(self.loans_tab, text="Borrow / Return Actions")
        ops_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(ops_frame, text="Book ID:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_loan_book_id = ttk.Entry(ops_frame, width=8)
        self.entry_loan_book_id.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(ops_frame, text="Member ID:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_loan_member_id = ttk.Entry(ops_frame, width=8)
        self.entry_loan_member_id.grid(row=0, column=3, padx=5, pady=5)

        btn_issue = ttk.Button(ops_frame, text="Issue Book", command=self._on_issue_book)
        btn_issue.grid(row=0, column=4, padx=10, pady=5)

        ttk.Separator(ops_frame, orient=tk.VERTICAL).grid(row=0, column=5, sticky="ns", padx=10)

        btn_return = ttk.Button(
            ops_frame, text="Return Selected Loan", command=self._on_return_selected_loan
        )
        btn_return.grid(row=0, column=6, padx=10, pady=5)

        # Loans Treeview
        columns = ("id", "book", "member", "loan_date", "due_date", "return_date", "fine", "status")
        self.loans_tree = ttk.Treeview(self.loans_tab, columns=columns, show="headings")
        self.loans_tree.heading("id", text="Loan ID")
        self.loans_tree.heading("book", text="Book")
        self.loans_tree.heading("member", text="Member")
        self.loans_tree.heading("loan_date", text="Loan Date")
        self.loans_tree.heading("due_date", text="Due Date")
        self.loans_tree.heading("return_date", text="Return Date")
        self.loans_tree.heading("fine", text="Fine")
        self.loans_tree.heading("status", text="Status")

        self.loans_tree.column("id", width=60, anchor=tk.CENTER)
        self.loans_tree.column("book", width=180)
        self.loans_tree.column("member", width=160)
        self.loans_tree.column("loan_date", width=90)
        self.loans_tree.column("due_date", width=90)
        self.loans_tree.column("return_date", width=90)
        self.loans_tree.column("fine", width=70, anchor=tk.E)
        self.loans_tree.column("status", width=80, anchor=tk.CENTER)
        self.loans_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _on_issue_book(self) -> None:
        try:
            book_id = int(self.entry_loan_book_id.get().strip())
            member_id = int(self.entry_loan_member_id.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Book ID and Member ID must be valid integers.")
            return

        try:
            loan_id = self.controller.issue_book(book_id, member_id)
            messagebox.showinfo("Success", f"Book issued! Loan ID: {loan_id}")
            self.refresh_all()
            self.entry_loan_book_id.delete(0, tk.END)
            self.entry_loan_member_id.delete(0, tk.END)
        except LibraryError as err:
            messagebox.showerror("Error", str(err))

    def _on_return_selected_loan(self) -> None:
        selected = self.loans_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a loan from the list to return.")
            return

        item = self.loans_tree.item(selected[0])
        loan_id = int(item["values"][0])
        status = item["values"][7]

        if status != "ACTIVE":
            messagebox.showinfo("Notice", "Selected loan is already returned.")
            return

        try:
            overdue_days, fine_cents = self.controller.return_book(loan_id)
            if overdue_days > 0:
                fine_str = cents_to_display(fine_cents)
                messagebox.showinfo(
                    "Returned", f"Book returned! Overdue by {overdue_days} days. Fine: {fine_str}"
                )
            else:
                messagebox.showinfo("Returned", "Book returned on time with no fine!")
            self.refresh_all()
        except LibraryError as err:
            messagebox.showerror("Error", str(err))

    # --- Refreshes ---

    def refresh_all(self) -> None:
        self.refresh_books()
        self.refresh_members()
        self.refresh_loans()

    def refresh_books(self) -> None:
        books = self.controller.list_books()
        self._populate_books_tree(books)

    def _populate_books_tree(self, books: list[Book]) -> None:
        for item in self.books_tree.get_children():
            self.books_tree.delete(item)
        for b in books:
            self.books_tree.insert(
                "",
                tk.END,
                values=(b.id, b.isbn, b.title, b.author, b.total_copies, b.available_copies),
            )

    def refresh_members(self) -> None:
        for item in self.members_tree.get_children():
            self.members_tree.delete(item)
        for m in self.controller.list_members():
            self.members_tree.insert(
                "",
                tk.END,
                values=(m.id, m.member_code, m.name, m.email, m.max_borrow_limit, m.created_at),
            )

    def refresh_loans(self) -> None:
        for item in self.loans_tree.get_children():
            self.loans_tree.delete(item)
        for loan in self.controller.list_loans():
            fine_str = cents_to_display(loan.fine_cents)
            ret_str = loan.return_date if loan.return_date else "-"
            self.loans_tree.insert(
                "",
                tk.END,
                values=(
                    loan.loan_id,
                    loan.book_title,
                    f"{loan.member_name} ({loan.member_code})",
                    loan.loan_date,
                    loan.due_date,
                    ret_str,
                    fine_str,
                    loan.status,
                ),
            )


def launch_gui(service: LibraryService | None = None) -> None:
    if service is None:
        db_path = Path(__file__).resolve().parent / "data" / "library.db"
        repo = LibraryRepository.from_path(db_path)
        service = LibraryService(repo)

    root = tk.Tk()
    controller = LibraryGUIController(service)
    _ = LibraryGUIApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
