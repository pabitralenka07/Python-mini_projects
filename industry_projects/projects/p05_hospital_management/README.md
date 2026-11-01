# Project 05: Hospital Management System

A beginner-friendly yet architecturally robust Hospital Management System demonstrating layered architecture, relational database constraints, domain invariant enforcement, and role-based administrative authentication simulation.

---

## 1. Architecture & Design Patterns

The project follows a **layered separation of concerns**:

1. **`models.py` (Domain Entities)**: Clean dataclasses representing `Doctor`, `Patient`, `Appointment`, `Bill`, and `AdminUser`.
2. **`repository.py` (Data Access Layer)**: Handles all SQLite interactions, migration checks, prepared queries, and foreign key enforcement.
3. **`service.py` (Business Logic Layer)**:
   - **Double-Booking Guard**: Prevents scheduling two appointments for the same doctor at the same date and time slot.
   - **Discharge Gatekeeper**: Enforces that an admitted patient cannot be discharged while any outstanding bill remains unpaid.
   - **Educational Security**: Implements `scrypt`-based password hashing with individual salts and brute-force lockout safeguards (educational simulation).
4. **`cli.py` (Presentation Layer)**: Interactive terminal user interface with clean tabular views (`format_table`) and resilient error handling.

---

## 2. Database Schema & Relationships

```text
+-----------------------+           +-----------------------+
|        doctors        |           |       patients        |
+-----------------------+           +-----------------------+
| id (PK)               |<----+     | id (PK)               |<----+
| name                  |     |     | name                  |     |
| specialization        |     |     | age, gender, contact  |     |
| consultation_fee_cents|     |     | ailment, status       |     |
| created_at            |     |     | admitted_at           |     |
+-----------------------+     |     | discharged_at         |     |
                              |     +-----------------------+     |
                              |                 ^                 |
                              |                 |                 |
                   +----------+---------+       |                 |
                   |    appointments    |       |                 |
                   +--------------------+       |                 |
                   | id (PK)            |       |                 |
                   | doctor_id (FK) ----+       |                 |
                   | patient_id (FK) ---+-------+                 |
                   | appointment_date   |                         |
                   | time_slot          |                         |
                   | notes, status      |                         |
                   | created_at         |                         |
                   +--------------------+                         |
                   | UNIQUE(doctor_id,  |                         |
                   |   date, slot)      |                         |
                   +--------------------+                         |
                                                                  |
                                       +--------------------+     |
                                       |       bills        |     |
                                       +--------------------+     |
                                       | id (PK)            |     |
                                       | patient_id (FK) ---+-----+
                                       | amount_cents       |
                                       | description        |
                                       | status ('UNPAID')  |
                                       | created_at         |
                                       | paid_at            |
                                       +--------------------+
```

### Constraints Enforced:
- `FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE`
- `FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE`
- `UNIQUE(doctor_id, appointment_date, time_slot)` prevents duplicate doctor bookings at the database level.

---

## 3. Key Invariants & Rules

### A. Preventing Double-Booking
When an appointment is requested:
1. `service.book_appointment()` queries whether the doctor already has a non-cancelled booking on that date and slot.
2. Even if a race condition occurred, the SQLite table constraint `UNIQUE(doctor_id, appointment_date, time_slot)` throws `sqlite3.IntegrityError`, caught and converted into `DoubleBookingError`.

### B. Discharge Billing Invariant
Before marking a patient as `DISCHARGED`:
1. `service.discharge_patient(patient_id)` queries all unpaid bills for that patient.
2. If unpaid balance > 0, an `UnpaidBillsDischargeError` is raised with the total pending amount in dollars and cents.
3. Discharge is granted only when all bills are settled.

### C. Admin Security (Educational Simulation)
Administrative actions (such as discharging patients or viewing sensitive administrative billing aggregates) are protected by a simulated login system using `hashlib.scrypt` with random 16-byte salts and exponential/lockout guards.

---

## 4. Common Pitfalls & Mistakes

- **Floating-Point Currency**: Never store consultation fees or hospital bills as floating-point numbers (`$150.50` -> `150.5`). Floating-point arithmetic causes rounding errors. Always store money as integer minor units (`amount_cents = 15050`).
- **Ignoring Foreign Keys**: SQLite disables foreign keys by default. Our `DatabaseManager` explicitly enables them on every connection via `PRAGMA foreign_keys = ON;`.
- **String Formats for Timestamps**: Always store ISO 8601 strings in UTC (`datetime.now(timezone.utc).isoformat()`) to avoid timezone confusion across hospital shifts.

---

## 5. Sample CLI Session

```text
================================================
         HOSPITAL MANAGEMENT SYSTEM             
  [Logged in as: admin]
================================================
 1. Admin Login / Logout
 2. Register Doctor
 3. Admit Patient
 4. Book Appointment (No Double-Booking)
 5. Generate Patient Bill
 6. Settle (Pay) Patient Bill
 7. Discharge Patient (Unpaid Check)
 8. View Appointments Schedule
 9. View Patients Directory
 10. View Doctors Directory
 0. Exit
================================================
Enter choice (0-10): 4
Doctor ID: 1
Patient ID: 1
Appointment Date (YYYY-MM-DD): 2026-11-05
Time Slot (e.g. 10:00, 14:30): 10:00
Notes: Follow-up checkup
[ERROR] Doctor already has an active appointment at 2026-11-05 10:00.
```

---

## 6. Unsolved Practice Exercises

1. **Exercise 1: Prescriptions Management**
   - Add a `prescriptions` table linked to an `appointment_id` or `patient_id`.
   - Store medicine name, dosage, duration (days), and doctor instructions.
   - Ensure prescriptions can only be created by doctors for completed or scheduled appointments.

2. **Exercise 2: Room Allocation & Bed Capacity**
   - Create a `rooms` table with bed capacities and daily room rates.
   - When admitting a patient, assign an available bed in a room.
   - When discharging the patient, calculate room charges based on days admitted and automatically add them to the patient's bill before final discharge check.
