# Project 09: Electricity Bill Management System

An enterprise utility billing application teaching tiered slab tariff algorithms, monotonic reading validation constraints, minor-unit financial arithmetic, interactive terminal operations, and a Level 2 Tkinter GUI.

---

> [!NOTE]
> **Educational Disclaimer**: The tariff slabs, fixed charges, and tax percentages implemented here are educational simulations designed to illustrate tiered pricing algorithms. They do not represent any real-world utility company rates or official regulatory tariffs.

---

## 1. Architecture & Design

The application follows the layered separation of concerns:

- **`models.py`**: Immutable dataclasses (`Consumer`, `MeterReading`, `TariffSlab`, `SlabBreakdown`, `ElectricityBill`, `BillDetail`).
- **`repository.py`**: SQLite database interactions with prepared queries, foreign keys, and a table-level check constraint:
  `CHECK(current_reading >= previous_reading)`.
- **`service.py`**:
  - **Monotonic Reading Guard**: Rejects any reading entry that is less than the previously recorded cumulative kWh reading.
  - **Tiered Slab Tariff Engine**: Splits units consumed across progressive rate buckets.
  - **Minor-Unit Financial Math**: Calculates energy charges, fixed charges, and 5% taxes entirely in integer cents.
- **`cli.py`**: Terminal interface providing tabular summaries, invoice calculation, and payment settlement.
- **`gui_app.py`**: Level 2 Tkinter application featuring modern styling, tabbed notebook navigation, customer lookup, real-time bill breakdown preview, and invoice settlement.

---

## 2. Database Schema & Relationships

```text
+-----------------------+
|       consumers       |
+-----------------------+
| id (PK)               |<----+
| consumer_number (UQ)  |     |
| name                  |     |
| address               |     |
| meter_number (UQ)     |     |
| tariff_category       |     |
+-----------------------+     |
            ^                 |
            |                 |
+-----------+-----------+     |     +-----------------------+
|    meter_readings     |     |     |         bills         |
+-----------------------+     |     +-----------------------+
| id (PK)               |     |     | id (PK)               |
| consumer_id (FK) -----+     +-----+ consumer_id (FK)      |
| reading_date          |           | bill_number (UQ)      |
| reading_value         |           | previous_reading      |
+-----------------------+           | current_reading       |
                                    | units_consumed        |
                                    | energy_charge_cents   |
                                    | fixed_charge_cents    |
                                    | tax_cents             |
                                    | total_cents           |
                                    | due_date, status      |
                                    | issued_at, paid_at    |
                                    +-----------------------+
                                    | CHECK(current_reading |
                                    |   >= previous_reading)|
                                    +-----------------------+
```

---

## 3. Tiered Slab Tariff Algorithm

Utility billing does not multiply all units by a flat single rate. Instead, energy consumed is sliced across progressive tiers:

### Residential Slabs:
| Tier Range (kWh) | Unit Rate | Example: 250 Units Consumed |
| :--- | :--- | :--- |
| **0 - 100 kWh** | $0.10 / kWh (`10` cents) | 100 kWh @ $0.10 = **$10.00** |
| **101 - 300 kWh** | $0.15 / kWh (`15` cents) | 150 kWh @ $0.15 = **$22.50** |
| **301 - 500 kWh** | $0.20 / kWh (`20` cents) | 0 kWh |
| **> 500 kWh** | $0.30 / kWh (`30` cents) | 0 kWh |
| **Fixed Service Charge** | Flat rate | **$5.00** |
| **Utility Tax (5%)** | 5% on subtotal ($37.50) | **$1.87** |
| **TOTAL INVOICE** | | **$39.37** |

---

## 4. Monotonic Meter Reading Invariant

A physical utility meter displays cumulative energy consumption; its counter always ticks upward.
1. When a new reading is entered, `service.generate_bill()` fetches the latest reading from `meter_readings`.
2. If `current_reading < previous_reading`, a `NonMonotonicReadingError` is raised.
3. Even if bypassed at the service layer, the database schema check constraint `CHECK(current_reading >= previous_reading)` prevents corrupted entries.

---

## 5. Sample CLI Session

```text
======================================================
        ELECTRICITY BILL MANAGEMENT SYSTEM            
======================================================
 1. View Consumer Accounts
 2. Register New Consumer Account
 3. Enter Meter Reading & Generate Bill
 4. View Itemized Bill Breakdown
 5. Settle (Pay) Utility Bill
 6. View All Invoices (Bill History)
 0. Exit
======================================================
Enter choice (0-6): 3
Enter Consumer Number: CON-1001
Previous Recorded Meter Reading: 100 kWh
Enter Current Meter Reading (kWh): 350

[SUCCESS] Invoice Generated Successfully!
Invoice Number : BILL-CON-1001-202610311440
Units Consumed : 250 kWh
Energy Charge  : $32.50
Fixed Charge   : $5.00
Utility Tax    : $1.87
Total Amount   : $39.37
Due Date       : 2026-11-15
```

---

## 6. Launching the Level 2 Tkinter GUI

Run the GUI with the `--gui` flag:
```bash
.venv/bin/python -m projects.p09_electricity_bill --gui
```

---

## 7. Unsolved Practice Exercises

1. **Exercise 1: Peak vs Off-Peak Time-of-Use (TOU) Metering**
   - Extend `MeterReading` to record peak hours (e.g. 14:00 - 19:00) vs off-peak hours consumption.
   - Apply a 1.5x multiplier to peak units in the slab calculation engine.
2. **Exercise 2: Late Payment Surcharge**
   - In `service.pay_bill()`, compare `clock.today_iso()` against `bill.due_date`.
   - If payment is made after the due date, apply a 2% late penalty charge to the total amount before settlement.
