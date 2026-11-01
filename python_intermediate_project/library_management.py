"""4. Library Management System - books, members, issue/return with fines."""
from datetime import date, timedelta
from tkinter import messagebox, ttk

from common import (AppError, CrudFrame, Database, Field, choice_id, fill_tree, guarded, launch,
                    make_tree, options, refresh_on_tab_change, selected_id)

SCHEMA = """
CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
    isbn TEXT UNIQUE, copies INTEGER NOT NULL DEFAULT 1 CHECK(copies >= 0));
CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, phone TEXT);
CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id), member_id INTEGER NOT NULL REFERENCES members(id),
    issued TEXT NOT NULL, due TEXT NOT NULL, returned TEXT, fine REAL NOT NULL DEFAULT 0);
"""
LOAN_DAYS, FINE_PER_DAY, MAX_LOANS = 14, 2.0, 3


class Library:
    def __init__(self, db):
        self.db = db

    def available(self, book_id):
        row = self.db.one("SELECT copies - (SELECT COUNT(*) FROM loans WHERE book_id=? AND returned IS NULL) AS a "
                          "FROM books WHERE id=?", (book_id, book_id))
        if row is None:
            raise AppError("Book not found")
        return row["a"]

    def issue(self, book_id, member_id, today=None):
        today = today or date.today()
        if self.available(book_id) <= 0:
            raise AppError("No copies of this book are available")
        active = self.db.one("SELECT COUNT(*) AS n FROM loans WHERE member_id=? AND returned IS NULL",
                             (member_id,))["n"]
        if active >= MAX_LOANS:
            raise AppError(f"Member already has {MAX_LOANS} books out")
        due = today + timedelta(days=LOAN_DAYS)
        self.db.execute("INSERT INTO loans(book_id, member_id, issued, due) VALUES(?,?,?,?)",
                        (book_id, member_id, today.isoformat(), due.isoformat()))
        return due

    def return_book(self, loan_id, today=None):
        today = today or date.today()
        loan = self.db.one("SELECT * FROM loans WHERE id=?", (loan_id,))
        if loan is None or loan["returned"]:
            raise AppError("This loan is not active")
        late = max(0, (today - date.fromisoformat(loan["due"])).days)
        fine = late * FINE_PER_DAY
        self.db.execute("UPDATE loans SET returned=?, fine=? WHERE id=?", (today.isoformat(), fine, loan_id))
        return fine


class App:
    def __init__(self, root):
        self.db = Database("library.db", SCHEMA)
        self.lib = Library(self.db)
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        books_sql = ("SELECT id, title, author, isbn, copies, copies - (SELECT COUNT(*) FROM loans "
                     "WHERE book_id=books.id AND returned IS NULL) AS available FROM books")
        self.books = CrudFrame(nb, self.db, "books", [
            Field("title"), Field("author"), Field("isbn", required=False), Field("copies", kind="int")],
            list_sql=books_sql)
        self.members = CrudFrame(nb, self.db, "members", [
            Field("name"), Field("email", required=False), Field("phone", required=False)])
        nb.add(self.books, text="Books")
        nb.add(self.members, text="Members")

        tab = ttk.Frame(nb)
        nb.add(tab, text="Issue / Return")
        box = ttk.LabelFrame(tab, text="Issue a book")
        box.pack(fill="x", padx=8, pady=6)
        self.book_cb = ttk.Combobox(box, width=40, state="readonly",
                                    postcommand=lambda: self.book_cb.configure(values=options(
                                        self.db, "SELECT id, title FROM books ORDER BY title")()))
        self.member_cb = ttk.Combobox(box, width=40, state="readonly",
                                      postcommand=lambda: self.member_cb.configure(values=options(
                                          self.db, "SELECT id, name FROM members ORDER BY name")()))
        for i, (label, w) in enumerate((("Book", self.book_cb), ("Member", self.member_cb))):
            ttk.Label(box, text=label).grid(row=i, column=0, padx=4, pady=3, sticky="e")
            w.grid(row=i, column=1, padx=4, pady=3)
        ttk.Button(box, text="Issue", command=self.issue).grid(row=2, column=1, sticky="w", pady=4)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=8)
        ttk.Button(bar, text="Return selected loan", command=self.return_book).pack(side="left")
        ttk.Label(bar, text=f"  Loan period {LOAN_DAYS} days, fine {FINE_PER_DAY:.0f}/day late").pack(side="left")
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True, padx=8, pady=6)
        self.loan_tree = make_tree(holder)
        self.tab = tab
        refresh_on_tab_change(nb, self.books, self.members, self)
        self.refresh()

    def refresh(self):
        cols, rows = self.db.columns_and_rows(
            "SELECT l.id, b.title AS book, m.name AS member, l.issued, l.due, "
            "COALESCE(l.returned,'-') AS returned, l.fine FROM loans l "
            "JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id ORDER BY l.id DESC")
        fill_tree(self.loan_tree, cols, rows)

    @guarded
    def issue(self):
        due = self.lib.issue(choice_id(self.book_cb.get()), choice_id(self.member_cb.get()))
        messagebox.showinfo("Issued", f"Due back on {due}")
        self.refresh()

    @guarded
    def return_book(self):
        fine = self.lib.return_book(selected_id(self.loan_tree, "loan"))
        messagebox.showinfo("Returned", f"Book returned. Fine to collect: {fine:.2f}")
        self.refresh()


if __name__ == "__main__":
    launch(App, "Library Management System", "950x620")
