# Project 04: Library Management System (PILOT)

A complete, layered, relational Library Management System built with Python 3.11+, SQLite, and an optional Level 2 Tkinter GUI. This project acts as the pilot architecture establishing our 4-tier pattern: Models, Repository (SQL), Service (Business Rules), and Presentation (CLI & GUI).

---

## 1. Features
- **Book Cataloging & Inventory**: Manage books by title, author, and ISBN with automatic tracking of total vs. available copy inventory.
- **Member Registration**: Register readers with custom borrow allowances and unique member codes.
- **Circulation & Due Dates**: Issue books with automated due-date scheduling (default 14 days) and return processing.
- **Overdue Fine Engine**: Real-time overdue day computation and fine assessment ($0.50/day) driven by an injectable clock.
- **Referential Integrity**: Enforces strict database rules preventing deletion of books currently on active loan (`ON DELETE RESTRICT`).
- **Flexible UI**: Interactive terminal CLI with aligned tables, plus an optional Level 2 Desktop GUI built with `tkinter`.
- **Zero ORM / Database Safety**: Uses pure parameterized `sqlite3` queries, transaction rollbacks on failures, and corruption safeguards with automatic `.bak` recovery.

---

## 2. How It Works
When a book is borrowed, the service verifies that available copies exist and that the member has not reached their borrowing limit. It creates an active loan record and decrements the available copies in a single atomic database transaction. When a book is returned, the system compares the return date against the due date using the clock abstraction, charges any applicable overdue fines, and marks the loan returned while incrementing the available copy count. If a user attempts to delete a catalog entry that currently has outstanding loans, both the domain service and SQLite foreign key constraints block the operation.

---

## 3. Database Schema

### Tables & Columns
```
+-------------------------------------------------------------+
|                          books                              |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| isbn              | TEXT    | UNIQUE NOT NULL               |
| title             | TEXT    | NOT NULL                      |
| author            | TEXT    | NOT NULL                      |
| total_copies      | INTEGER | NOT NULL CHECK (>= 0)         |
| available_copies  | INTEGER | NOT NULL CHECK (0 <= x <= tot)|
+-------------------+---------+-------------------------------+
                               ▲
                               │ ON DELETE RESTRICT
                               │
+------------------------------+------------------------------+
|                          loans                              |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| book_id           | INTEGER | REFERENCES books(id)          |
| member_id         | INTEGER | REFERENCES members(id)        |
| loan_date         | TEXT    | NOT NULL (ISO-8601)           |
| due_date          | TEXT    | NOT NULL (ISO-8601)           |
| return_date       | TEXT    | NULLABLE (ISO-8601)           |
| fine_cents        | INTEGER | DEFAULT 0 CHECK (>= 0)        |
| status            | TEXT    | CHECK (status IN ('ACTIVE',   |
|                   |         |        'RETURNED'))           |
+-------------------+---------+-------------------------------+
                               │
                               │ ON DELETE RESTRICT
                               ▼
+-------------------------------------------------------------+
|                         members                             |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| member_code       | TEXT    | UNIQUE NOT NULL               |
| name              | TEXT    | NOT NULL                      |
| email             | TEXT    | UNIQUE NOT NULL               |
| max_borrow_limit  | INTEGER | DEFAULT 3 CHECK (> 0)         |
| created_at        | TEXT    | NOT NULL (ISO-8601)           |
+-------------------+---------+-------------------------------+
```

### Relational Entity Diagram
```
  [ books ] 1 ───────────< N [ loans ] N >─────────── 1 [ members ]
```

---

## 4. Class Architecture & Design Roles

| Class | File | Responsibility |
|---|---|---|
| `Book` | `models.py` | Immutable dataclass representing a book and its copy inventory invariants. |
| `Member` | `models.py` | Immutable dataclass representing registered patrons and their borrow allowances. |
| `Loan` | `models.py` | Dataclass capturing an individual borrowing transaction and fine state. |
| `LoanDetail` | `models.py` | Composite projection model joining book, member, and loan fields for UI displays. |
| `LibraryRepository` | `repository.py` | Dedicated SQL persistence tier executing parameterized queries within atomic transactions. |
| `LibraryService` | `service.py` | Pure domain business tier enforcing borrowing limits, dates, fine calculation, and deletion guards. |
| `LibraryGUIController`| `gui_app.py` | Headless controller layer mediating between Tkinter UI widgets and the service layer. |
| `LibraryGUIApp` | `gui_app.py` | Level 2 Tkinter view containing multi-tab forms, Treeviews, and dialogs. |

### Design Choice Note & Simpler Alternative
Instead of a separate repository and service tier, beginners often place SQL queries directly inside button callbacks or CLI menus. While that approach is faster for tiny scripts, it tightly couples UI code to SQL tables and makes automated headless testing impossible without mocking the database driver. Our 4-tier separation allows full headless testability.

---

## 5. Common Mistakes & Beginner Pitfalls
1. **Float Representation for Money**: Storing fines as floats (e.g., `0.50`) leads to floating-point representation drift (e.g., `0.49999999999999994`). We store currency strictly as integer minor units (`50` cents) and convert to string representation only at the display boundary.
2. **Non-Atomic Operations**: Decrementing inventory in one query and inserting a loan record in a separate transaction without `with conn:`. If the computer crashes between the two statements, a book copy is permanently lost from available inventory.
3. **Hardcoded Clock Usage**: Using `datetime.now()` directly inside business services prevents unit tests from testing overdue fees without sleeping or mocking system time. We inject a `Clock` protocol to make overdue logic 100% deterministic.

---

## 6. How to Run

### Command-Line Interface (CLI)
From the `python_intermediate_projects` root folder:
```bash
.venv/bin/python -m projects.p04_library_management
```

### Graphical User Interface (Level 2 Tkinter GUI)
```bash
.venv/bin/python -m projects.p04_library_management.gui_app
```

### Seed Fake Demo Data
```bash
.venv/bin/python -m projects.p04_library_management.seed
```

---

## 7. How to Test
Run the comprehensive test suite with Pytest:
```bash
.venv/bin/pytest tests/test_p04_library_management.py -v
```

---

## 8. Sample Session

```text
=============================================
      LIBRARY MANAGEMENT SYSTEM (PILOT)      
=============================================
 1. Add New Book
 2. Search Books
 3. List All Books
 4. Register Member
 5. List All Members
 6. Issue Book (Borrow)
 7. Return Book
 8. View Active Loans
 9. View Loan History
 10. Delete Book
 0. Exit
=============================================
Enter option (0-10): 1

--- Add New Book ---
Enter ISBN: 978-0132350884
Enter Title: Clean Code
Enter Author: Robert C. Martin
Enter Total Copies: 3

Success: Book 'Clean Code' cataloged with ID 1!

Enter option (0-10): 4

--- Register Member ---
Enter Member Code (e.g., M001): M101
Enter Full Name: Alice Johnson
Enter Email: alice@example.com
Borrow Limit [3]: 3

Success: Member 'Alice Johnson' registered with ID 1!

Enter option (0-10): 6

--- Issue Book (Borrow) ---
Enter Book ID: 1
Enter Member ID: 1

Success: Loan record created! Loan ID: 1. (Standard period: 14 days)
```

---

## 9. Known Limitations
- Does not automatically reserve books when copies reach zero.
- Single fine rate applied universally across all book categories.

---

## 10. Enhancement Ideas
1. **Book Reservations Queue**: Allow members to join a waitlist when all copies of a book are on loan.
2. **Category-Based Fine Tiers**: Implement different overdue fine rates based on book category (e.g., reference books vs. fiction).
3. **Email Overdue Reminders**: Add a background notification script warning members 2 days prior to the loan due date.

---

## 11. Practice Exercises for You
- **Exercise 1: Renewal Feature**: Implement a `renew_loan(loan_id: int)` method in `LibraryService` that extends the loan due date by another 14 days, provided the book is not overdue and hasn't exceeded a maximum of 2 renewals.
- **Exercise 2: Member Suspension**: Add an `is_suspended` boolean flag to the `Member` table. If a member accumulates more than $10.00 in unpaid fines, automatically suspend their account from borrowing until cleared.
