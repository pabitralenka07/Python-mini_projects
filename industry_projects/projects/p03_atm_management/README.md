# Project 03: ATM Management System

An educational ATM simulation demonstrating cryptographic PIN hashing, account lockout protection, banknote denomination dispensing, and cross-project service reuse from `p02_bank_management`.

---

## 1. Educational Authentication Disclaimer
> [!IMPORTANT]
> **EDUCATIONAL SIMULATION ONLY**: This project is strictly an educational model illustrating intermediate Python concepts (salting, constant-time comparisons, and brute-force lockout counters). It is **not** a secure authentication system and must never be used to secure real financial assets. Real ATMs employ physical Hardware Security Modules (HSMs), Triple-DES/AES PIN-block encryption (ISO 9564), tamper-resistant EMV chip protocols, and interbank network switches.

---

## 2. Features
- **Cross-Module Service Reuse**: Reuses the core ledger, deposit, withdrawal, and statement operations directly from `projects.p02_bank_management.service.BankService` instead of duplicating code.
- **PIN Cryptography**: Stores PINs as salted `hashlib.scrypt` digests with constant-time verification (`hmac.compare_digest`) to resist timing attacks.
- **Brute-Force Lockout**: Automatically locks a card for 15 minutes after 3 consecutive failed PIN attempts.
- **Physical Banknote Dispenser**: Greedily decomposes withdrawn amounts into available physical currency notes ($100, $50, $20, $10) and enforces $10 multiples.
- **Daily Withdrawal Limits**: Tracks and enforces a rolling daily limit ($1,000.00 / 100,000 cents per day) across multiple ATM visits.
- **Mini Statement**: Displays the most recent 5 ledger transactions on screen.

---

## 3. How It Works
When a user enters a card number and PIN, `ATMService` validates the card against `ATMRepository` using a per-user random salt and `hashlib.scrypt`. If authentication succeeds, the session menu provides access to balance inquiries, deposits, withdrawals, and PIN updates. During cash withdrawal, the service verifies that the requested sum is a multiple of $10, checks that cumulative daily withdrawals do not exceed the $1,000 quota, and delegates the debit to `BankService.withdraw()`. Upon successful debit, the ATM returns a banknote breakdown detailing the physical bill count.

---

## 4. Database Schema

### Tables & Columns
```
+-------------------------------------------------------------+
|                          atm_cards                          |
+-------------------+---------+-------------------------------+
| card_number       | TEXT    | PRIMARY KEY                   |
| account_number    | TEXT    | NOT NULL                      |
| pin_hash          | BLOB    | NOT NULL (scrypt digest)      |
| salt              | BLOB    | NOT NULL (16 random bytes)    |
| failed_attempts   | INTEGER | NOT NULL DEFAULT 0            |
| locked_until      | TEXT    | NULLABLE (ISO-8601 timestamp) |
| status            | TEXT    | CHECK (status IN ('ACTIVE',   |
|                   |         |        'BLOCKED'))            |
+-------------------+---------+-------------------------------+
                               ▲
                               │ ON DELETE RESTRICT
                               │
+------------------------------+------------------------------+
|                    daily_atm_withdrawals                    |
+-------------------+---------+-------------------------------+
| id                | INTEGER | PRIMARY KEY AUTOINCREMENT     |
| card_number       | TEXT    | REFERENCES atm_cards(card_no) |
| withdrawal_date   | TEXT    | NOT NULL (YYYY-MM-DD)         |
| total_amount_cents| INTEGER | NOT NULL DEFAULT 0            |
|                   |         | UNIQUE(card_no, withdr_date)  |
+-------------------+---------+-------------------------------+
```

### Relational Entity Diagram
```
  [ atm_cards ] 1 ───────────< N [ daily_atm_withdrawals ]
        │
        └─ (reusable reference) ──> [ accounts (from p02_bank_management) ]
```

---

## 5. Class Architecture & Design Roles

| Class | File | Responsibility |
|---|---|---|
| `ATMCard` | `models.py` | Immutable entity holding card credentials, salt, and lockout status. |
| `CashDispenseResult`| `models.py` | Dataclass summarizing total dispensed cash and banknote counts ($100, $50, $20, $10). |
| `ATMRepository` | `repository.py` | SQL layer managing cards and daily cumulative withdrawal records. |
| `ATMService` | `service.py` | PIN verification, lockout enforcement, banknote dispensing, and BankService delegation. |

### Architectural Code Reuse
Instead of re-implementing customer tables, account balances, or transaction tables, `ATMService` accepts an instantiated `BankService` directly. All actual debits and balance assertions are executed by `BankService`, ensuring a single source of truth for bank ledgers.

---

## 6. Common Mistakes & Beginner Pitfalls
1. **Storing PINs in Plaintext or Simple Hashes**: Storing `1234` or even `md5("1234")` makes credentials trivial to crack using lookup tables. We use `hashlib.scrypt` with a unique 16-byte cryptographically random salt per card.
2. **Ignoring Cash Denominations**: Allowing users to request arbitrary non-bill amounts (like $43.27) at an ATM. Physical ATMs only dispense standard banknotes; our greedy algorithm ensures clean bill distribution in $10 increments.

---

## 7. How to Run

### Command-Line Interface (CLI)
```bash
.venv/bin/python -m projects.p03_atm_management
```

### Seed Fake Demo Data
```bash
.venv/bin/python -m projects.p03_atm_management.seed
```

---

## 8. How to Test
```bash
.venv/bin/pytest tests/test_p03_atm_management.py -v
```

---

## 9. Sample Session

```text
=======================================================
      AUTOMATED TELLER MACHINE (ATM SIMULATION)      
  [EDUCATIONAL SIMULATION ONLY - NOT PRODUCTION AUTH] 
=======================================================

Please insert your card to begin.
(Type 'exit' or 0 to quit)
Enter Card Number: 4000-1234-5678-9010
Enter 4-Digit PIN: ****

PIN Verified. Welcome to your account!

----------------------------------------
 CARD INSERTED: ****-****-****-9010
----------------------------------------
 1. Check Balance
 2. Withdraw Cash (Dispense Notes)
 3. Deposit Cash
 4. Mini Statement (Last 5 Transactions)
 5. Change PIN
 0. Eject Card / Finish Session
----------------------------------------
Select option (0-5): 2

--- Cash Withdrawal ---
Available note denominations: $100, $50, $20, $10 (Multiples of $10 only)
Enter amount to withdraw (e.g. $80): $180.00

=== CASH DISPENSED ===
Total: $180.00
Banknotes: 1 x $100, 1 x $50, 1 x $20, 1 x $10
Please take your cash from the dispensing slot.
```

---

## 10. Known Limitations
- Does not simulate a physical ATM banknote hopper inventory running out of specific bills (e.g., ATM out of $20 notes).
- Only supports single-currency ($ USD) dispensing.

---

## 11. Enhancement Ideas
1. **Physical Hopper Inventory**: Model internal ATM bill cartridges (e.g., 50x $100 notes remaining), dynamically falling back to smaller bills when high denominations are depleted.
2. **ATM Transfer Feature**: Allow cardholders to transfer funds from their card's account to third-party bank accounts directly from the ATM console.
3. **Receipt Generation**: Generate a formatted text receipt file on desktop after cash withdrawals.

---

## 12. Practice Exercises for You
- **Exercise 1: Dynamic Note Configuration**: Allow the user to request their preferred banknote mix (e.g., "Give me all $20s instead of $100s") if sufficient bills are available.
- **Exercise 2: PIN Complexity Rules**: Modify `change_pin` to reject trivial PINs such as sequential digits (`1234`, `4321`) or identical repeated digits (`1111`, `9999`).
