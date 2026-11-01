# Project 01: Contact Management System

A production-grade, layered Contact Management System built with Python 3.11+, SQLite, CSV import/export, and a Level 2 Tkinter GUI.

---

## 1. Features
- **Contact Lifecycle**: Add, view, edit, and delete contacts with full field validations.
- **Deduplication**: Automatic database and service-level rejection of duplicate phone numbers or email addresses.
- **Search Engine**: Search across names, phone numbers, and emails using partial matching.
- **Safe CSV Export**: Implements spreadsheet formula injection protection by neutralizing leading `=`, `+`, `-`, or `@` characters.
- **Safe CSV Import**: Parses external address books, validates field formats, and imports valid rows while logging skipped duplicates.
- **Dual Presentation**: Clean interactive terminal CLI with table views, plus an optional Level 2 Tkinter GUI.

---

## 2. How It Works
User inputs are validated in the service layer against strict phone length and email regex rules before reaching SQLite. Queries are executed via `ContactRepository` using parameterized statements (`?`) with uniqueness constraints on phone and email columns. Deletion actions require explicit confirmation, where EOF or any non-yes answer immediately cancels the action. When exporting contacts to CSV, cells beginning with formula trigger characters are automatically sanitized to prevent arbitrary spreadsheet code execution.

---

## 3. Database Schema

### Table & Columns
```
+-------------------------------------------------------------+
|                          contacts                           |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| name              | TEXT    | NOT NULL CHECK (length > 0)   |
| phone             | TEXT    | UNIQUE NOT NULL CHECK(len>=7) |
| email             | TEXT    | UNIQUE NOT NULL CHECK(email)  |
| address           | TEXT    | NOT NULL DEFAULT ''           |
| created_at        | TEXT    | NOT NULL (ISO-8601)           |
+-------------------+---------+-------------------------------+
```

### Text Relational Diagram
```
  [ contacts ] (Standalone table with unique indices on phone and email)
```

---

## 4. Class Architecture & Design Roles

| Class | File | Responsibility |
|---|---|---|
| `Contact` | `models.py` | Immutable dataclass representing a contact entity with basic integrity rules. |
| `ContactRepository` | `repository.py` | Encapsulates all SQL statements, transaction contexts, and row-to-model mapping. |
| `ContactService` | `service.py` | Business logic for validation, duplicate checking, CSV parsing, and formula escaping. |
| `ContactGUIController` | `gui_app.py` | Headless controller decoupling UI events from underlying data operations. |
| `ContactGUIApp` | `gui_app.py` | Level 2 Tkinter view with treeviews, search filtering, and dialogs. |

### Design Choice Note & Simpler Alternative
A simpler alternative to using a relational database would be storing contacts in a flat JSON or CSV file. However, flat files require rewriting the entire file on every edit or deletion, and cannot easily enforce atomic uniqueness constraints across concurrent operations.

---

## 5. Common Mistakes & Beginner Pitfalls
1. **Spreadsheet Formula Injection**: Exporting raw user text like `=CMD|' /C calc'!A0` directly to CSV. When opened in Microsoft Excel or LibreOffice Calc, the spreadsheet executes the string as a formula or shell command. We neutralize this by prefixing formula triggers (`=`, `+`, `-`, `@`) with a quote.
2. **Permissive Phone Validation**: Accepting non-numeric symbols indiscriminately or truncating phone numbers without warning. We strip whitespace and verify a valid digit count (7-15 digits).

---

## 6. How to Run

### Command-Line Interface (CLI)
```bash
.venv/bin/python -m projects.p01_contact_management
```

### Graphical User Interface (Level 2 Tkinter GUI)
```bash
.venv/bin/python -m projects.p01_contact_management.gui_app
```

### Seed Fake Demo Data
```bash
.venv/bin/python -m projects.p01_contact_management.seed
```

---

## 7. How to Test
```bash
.venv/bin/pytest tests/test_p01_contact_management.py -v
```

---

## 8. Sample Session

```text
=============================================
      CONTACT MANAGEMENT SYSTEM      
=============================================
 1. Add New Contact
 2. Search Contacts
 3. List All Contacts
 4. Edit Contact
 5. Delete Contact
 6. Import Contacts from CSV
 7. Export Contacts to CSV
 0. Exit
=============================================
Enter option (0-7): 1

--- Add New Contact ---
Enter Full Name: Ada Lovelace
Enter Phone Number: +1-555-8900
Enter Email: ada@computing.example
Enter Address (optional): London, UK

Success: Contact 'Ada Lovelace' created with ID 1!
```

---

## 9. Known Limitations
- Does not support grouping contacts into custom categories (e.g., Work vs. Family).
- Search currently matches substrings within fields rather than fuzzy phonetics.

---

## 10. Enhancement Ideas
1. **Contact Groups & Tags**: Allow tagging contacts (e.g., `Friends`, `Colleagues`) with filterable group views.
2. **vCard (.vcf) Export**: Add support for the industry-standard vCard format used by mobile operating systems.
3. **Audit History Log**: Track timestamped modifications and previous phone numbers in a secondary history table.

---

## 11. Practice Exercises for You
- **Exercise 1: Birthday Reminder**: Add an optional `birthday` field (`YYYY-MM-DD`) and write a service method `get_upcoming_birthdays(days: int = 7)` returning contacts celebrating birthdays within the window.
- **Exercise 2: Favorite Flag**: Add an `is_favorite` boolean to the `Contact` model and add a menu command to toggle and list favorites first.
