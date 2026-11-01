# Project 02: Bank Management System

A robust, layered banking core built with Python 3.11+, SQLite, integer-cents financial precision, OOP account hierarchies, and atomic transfer transactions.

---

## 1. Features
- **Customer Lifecycle**: Register customers with unique email validation.
- **Polymorphic Account Types**:
  - `SavingsAccount`: Mandates a minimum balance ($50.00 / 5,000 cents); rejects withdrawals dropping below the threshold.
  - `CurrentAccount`: Permits overdraft protection up to an approved limit ($500.00 / 50,000 cents).
- **Atomic Transfers**: Fund transfers between accounts execute as a single atomic SQLite transaction (`with conn:`), guaranteeing that either both accounts update or neither does.
- **Integer Minor-Unit Currency**: All monetary amounts are processed as integer cents, eliminating floating-point round-off errors.
- **Ledger Statements**: Full historical ledger recording timestamps, transaction types (`DEPOSIT`, `WITHDRAWAL`, `TRANSFER_IN`, `TRANSFER_OUT`), and balance snapshots.
- **Account Closing Protection**: Prevents closing accounts with unresolved balances.

---

## 2. How It Works
When an account transaction is requested, `BankService` retrieves the polymorphic `Account` entity from `BankRepository`. The account class's `validate_withdrawal` method determines whether the requested amount satisfies the specific account type's rules (minimum balance for savings, overdraft ceiling for current accounts). If permitted, the repository updates the ledger and balance within an atomic transaction. In transfers, debits, credits, and dual ledger entries are wrapped in a single database transaction, rolling back automatically if any individual step encounters an error.

---

## 3. Database Schema

### Tables & Columns
```
+-------------------------------------------------------------+
|                          customers                          |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| name              | TEXT    | NOT NULL CHECK (length > 0)   |
| email             | TEXT    | UNIQUE NOT NULL CHECK (email) |
| created_at        | TEXT    | NOT NULL (ISO-8601)           |
+-------------------+---------+-------------------------------+
                               ▲
                               │ ON DELETE RESTRICT
                               │
+------------------------------+------------------------------+
|                          accounts                           |
+-------------------+---------+-------------------------------+
| account_number    | TEXT    | PRIMARY KEY                   |
| customer_id       | INTEGER | REFERENCES customers(id)      |
| account_type      | TEXT    | CHECK (IN ('SAVINGS',         |
|                   |         |            'CURRENT'))        |
| balance_cents     | INTEGER | NOT NULL                      |
| minimum_balance   | INTEGER | NOT NULL DEFAULT 0            |
| overdraft_limit   | INTEGER | NOT NULL DEFAULT 0            |
| status            | TEXT    | CHECK (IN ('ACTIVE','CLOSED'))|
| created_at        | TEXT    | NOT NULL (ISO-8601)           |
+-------------------+---------+-------------------------------+
                               ▲
                               │ ON DELETE RESTRICT
                               │
+------------------------------+------------------------------+
|                        transactions                         |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| account_number    | TEXT    | REFERENCES accounts(acc_num)  |
| transaction_type  | TEXT    | CHECK (IN ('DEPOSIT',         |
|                   |         |  'WITHDRAWAL','TRANSFER_IN',  |
|                   |         |  'TRANSFER_OUT'))             |
| amount_cents      | INTEGER | NOT NULL CHECK (amount > 0)   |
| balance_after     | INTEGER | NOT NULL                      |
| reference_account | TEXT    | NULLABLE                      |
| timestamp         | TEXT    | NOT NULL (ISO-8601)           |
+-------------------+---------+-------------------------------+
```

### Relational Entity Diagram
```
  [ customers ] 1 ───────────< N [ accounts ] 1 ───────────< N [ transactions ]
```

---

## 4. Class Architecture & Design Roles

| Class | File | Responsibility |
|---|---|---|
| `Customer` | `models.py` | Immutable entity representing bank patrons. |
| `Account` | `models.py` | Abstract base class defining common ledger fields and withdrawal contract. |
| `SavingsAccount` | `models.py` | Concrete subclass enforcing $50.00 minimum balance invariant. |
| `CurrentAccount` | `models.py` | Concrete subclass enforcing $500.00 overdraft limit invariant. |
| `TransactionRecord` | `models.py` | Immutable snapshot of an individual ledger operation. |
| `BankRepository` | `repository.py` | SQL layer executing atomic queries, balance updates, and transfers. |
| `BankService` | `service.py` | Business engine managing customer onboarding, polymorphic validation, and transfers. |

### Design Choice Note & Simpler Alternative
A simpler alternative to OOP inheritance would be placing an `if account_type == 'SAVINGS': ... else: ...` block inside the service. However, using distinct subclasses makes rules self-contained, testable in isolation, and open to extension (e.g. adding a `FixedDepositAccount` without modifying existing withdrawal logic).

---

## 5. Common Mistakes & Beginner Pitfalls
1. **Splitting Transfers Across Separate Transactions**: Performing `UPDATE accounts SET balance = balance - 100 WHERE id = 1` in one statement and credit in another without `with conn:`. If an unexpected exception or power loss occurs in between, money vanishes into thin air.
2. **Using Float Arithmetic for Currency**: Writing `balance -= 0.1` repeatedly leads to floating-point drift (e.g., `19.999999999999996`). We store money strictly as integer minor units (`10` cents) and format only when printing.

---

## 6. How to Run

### Command-Line Interface (CLI)
```bash
.venv/bin/python -m projects.p02_bank_management
```

### Seed Fake Demo Data
```bash
.venv/bin/python -m projects.p02_bank_management.seed
```

---

## 7. How to Test
```bash
.venv/bin/pytest tests/test_p02_bank_management.py -v
```

---

## 8. Sample Session

```text
=============================================
         BANK MANAGEMENT SYSTEM              
=============================================
 1. Register Customer
 2. Open Account (Savings / Current)
 3. Deposit Funds
 4. Withdraw Funds
 5. Transfer Funds (Atomic)
 6. View Account Statement
 7. List Customers & Accounts
 8. Close Account
 0. Exit
=============================================
Enter option (0-8): 2

--- Open Bank Account ---
Enter Customer ID: 1
Select Account Type (SAVINGS/CURRENT): SAVINGS
Note: Savings account requires minimum opening deposit of $50.00.
Enter Initial Deposit (e.g., $100.00): $500.00

Success: SAVINGS Account opened! Account Number: SAV-482190 | Balance: $500.00

Enter option (0-8): 5

--- Transfer Funds (Single Transaction) ---
Source Account Number: SAV-482190
Destination Account Number: CUR-910234
Transfer Amount: $100.00

Transfer Successful!
  Source (SAV-482190) Balance: $400.00
  Destination (CUR-910234) Balance: $300.00
```

---

## 9. Known Limitations
- Does not compute scheduled compound monthly interest automatically.
- Does not enforce daily transfer limits per account.

---

## 10. Enhancement Ideas
1. **Periodic Interest Accrual**: Add a monthly maintenance job that calculates and deposits interest into savings accounts based on average daily balances.
2. **Tiered Overdraft Fees**: Assess a flat fee whenever a current account enters negative balance territory.
3. **Joint Accounts**: Support multiple customer IDs linked to a single shared account.

---

## 11. Practice Exercises for You
- **Exercise 1: Account Freeze**: Add a `SUSPENDED` status to the `Account` model. Suspended accounts allow deposits but strictly block withdrawals and transfers.
- **Exercise 2: Daily Withdrawal Quota**: Add a table tracking daily withdrawal totals per account, rejecting any withdrawals that cause the cumulative daily total to exceed $1,000.00.
