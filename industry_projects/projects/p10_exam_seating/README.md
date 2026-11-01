# Project 10: Exam Seating Arrangement System

An examination operations application demonstrating deterministic seeded pseudo-random allocations, course separation to prevent academic dishonesty, 2D matrix seating grids, and CSV export capabilities.

---

## 1. Architecture & Design

The application follows the layered separation of concerns:

- **`models.py`**: Immutable dataclasses (`Student`, `Room`, `Exam`, `SeatAllocation`, `AllocatedSeatView`).
- **`repository.py`**: SQLite data access with foreign keys, prepared queries, and dual unique constraints:
  - `UNIQUE(exam_id, student_id)`: Prevents multiple seats for one student in an exam session.
  - `UNIQUE(exam_id, room_id, seat_label)`: Prevents assigning two students to the same physical desk.
- **`service.py`**:
  - **Hall Capacity Guard**: Verifies total enrolled students against sum of assigned hall capacities before allocation.
  - **Interleaved Course Separation**: Alternates students across distinct course queues in adjacent desks (`R1C1: Course A`, `R1C2: Course B`, `R1C3: Course A`), minimizing cheating opportunities.
  - **Deterministic Seeded RNG**: Uses an explicit `random.Random(seed)` instance, ensuring identical allocations across repeated runs when given the same seed.
  - **2D ASCII Seating Chart Formatter**: Renders clean room matrices.
  - **CSV Exporter**: Generates student seating lists for examination invigilators.
- **`cli.py`**: Interactive terminal menu with tabular displays and CSV exports.

---

## 2. Database Schema & Relationships

```text
+-----------------------+           +-----------------------+
|        students       |           |         rooms         |
+-----------------------+           +-----------------------+
| id (PK)               |<----+     | id (PK)               |<----+
| roll_number (UNIQUE)  |     |     | room_number (UNIQUE)  |     |
| name                  |     |     | rows, cols            |     |
| course_code           |     |     | total_capacity        |     |
+-----------------------+     |     +-----------------------+     |
                              |                 ^                 |
                              |                 |                 |
                   +----------+---------+       |                 |
                   |  seat_allocations  |       |                 |
                   +--------------------+       |                 |
                   | id (PK)            |       |                 |
                   | student_id (FK) ---+       |                 |
                   | room_id (FK) ------+-------+                 |
                   | exam_id (FK) ------+-------+                 |
                   | seat_label         |       |                 |
                   +--------------------+       |                 |
                   | UNIQUE(exam_id,    |       |                 |
                   |   student_id)      |       |                 |
                   | UNIQUE(exam_id,    |       |                 |
                   |   room_id, label)  |       |                 |
                   +--------------------+       |                 |
                                                v                 |
                                     +--------------------+       |
                                     |       exams        |       |
                                     +--------------------+       |
                                     | id (PK)            |       |
                                     | course_code        |       |
                                     | exam_name          |       |
                                     | exam_date, slot    |       |
                                     +--------------------+       |
                                     | UNIQUE(course_code,|       |
                                     |   date, slot)      |       |
                                     +--------------------+       |
```

---

## 3. Course Separation Interleaving Algorithm

When multiple courses conduct examinations during the same slot (e.g. `CS101` and `MA201`):

```text
Concurrent Queues:
  CS101: [CS-101, CS-102, CS-103, CS-104]
  MA201: [MA-201, MA-202, MA-203, MA-204]

Interleaved Sequence:
  Index 0 -> CS-101
  Index 1 -> MA-201
  Index 2 -> CS-102
  Index 3 -> MA-202
  ...
```

When mapped to a 2D seating grid (`rows x cols`), adjacent desks in every row alternate courses:

```text
=== SEATING CHART: ROOM HALL-101 (Capacity: 12) ===
Layout: 3 Rows x 4 Columns | Occupied: 12
 [ Blackboard / Invigilator Desk ]
--------------------------------------------------------------------------------------------------------
 [R1C1: CS101 CS-105]     [R1C2: MA201 MA-204]     [R1C3: CS101 CS-102]     [R1C4: MA201 MA-208]   
 [R2C1: CS101 CS-101]     [R2C2: MA201 MA-202]     [R2C3: CS101 CS-107]     [R2C4: MA201 MA-206]   
 [R3C1: CS101 CS-104]     [R3C2: MA201 MA-201]     [R3C3: CS101 CS-108]     [R3C4: MA201 MA-205]   
--------------------------------------------------------------------------------------------------------
```

---

## 4. Determinism & Seeded Pseudo-Randomness

The allocation service uses `random.Random(seed)` rather than global `random.seed()`:
- Prevents cross-module interference with other background tasks or test fixtures.
- Guarantees that passing `seed=42` produces identical seat layouts every single time.
- Allows administrators to audit or regenerate lost seating plans with 100% reproducibility.

---

## 5. Sample CLI Session

```text
======================================================
        EXAM SEATING ARRANGEMENT SYSTEM               
======================================================
 1. View Room Seating Chart (ASCII Grid)
 2. Run Seating Allocation (Course Separation)
 3. Export Seating Plan to CSV File
 4. View Enrolled Students
 5. View Examination Rooms
 6. Add Student, Room, or Exam Session
 0. Exit
======================================================
Enter choice (0-6): 2
Enter Exam Date (YYYY-MM-DD): 2026-12-10
Select Exam Slot (MORNING/AFTERNOON): MORNING
Enter Deterministic RNG Seed (default 42): 42

[SUCCESS] Successfully allocated 16 students into exam halls!
Adjacency course separation rules enforced.
```

---

## 6. Unsolved Practice Exercises

1. **Exercise 1: Checkered 2D Adjacency (Diagonal Separation)**
   - Enhance the interleaving algorithm so that students of the same course are separated not only horizontally across columns, but also vertically across rows (a true checkerboard pattern).
2. **Exercise 2: Special Accommodations Allocation**
   - Add a `requires_accessible_desk: bool` flag to `Student`.
   - Ensure students requiring accessible desks are strictly placed in row 1 closest to the hall door.
