# Project 08: Zoo Management System

A zoo operations and admissions management application demonstrating relational database constraints, capacity invariant enforcement, feeding schedule dispatching, and minor-unit revenue aggregation.

---

## 1. Architecture & Design

The application follows the layered architecture:

- **`models.py`**: Immutable dataclasses (`Enclosure`, `EnclosureDetail`, `Animal`, `FeedingScheduleEntry`, `Keeper`, `TicketSale`, `DailyRevenueReport`) and `TicketType` enumeration.
- **`repository.py`**: Prepared SQLite transactions, foreign key relations between enclosures, animals, and keepers, and aggregation queries for daily revenue reporting.
- **`service.py`**:
  - **Enclosure Capacity Invariant**: Prevents overcrowding by verifying `current_animals < max_capacity` before any animal admission.
  - **Feeding Schedule Dispatcher**: Sorts and displays feeding timetables by scheduled time for zoo staff.
  - **Minor-Unit Ticketing**: Sells admission tickets using integer cents ($20.00 = 2000 cents) to prevent floating-point rounding errors.
  - **Daily Revenue Aggregator**: Aggregates ticket categories and total income for calendar dates.
- **`cli.py`**: Interactive terminal interface formatted with clean borders and column alignments.

---

## 2. Database Schema & Relationships

```text
+-----------------------+           +-----------------------+
|      enclosures       |           |        keepers        |
+-----------------------+           +-----------------------+
| id (PK)               |<----+     | id (PK)               |
| name (UNIQUE)         |     |     | name                  |
| habitat_type          |     |     | employee_id (UNIQUE)  |
| max_capacity          |     +-----+ assigned_enclosure_id |
+-----------------------+           +-----------------------+
            ^
            |
+-----------+-----------+           +-----------------------+
|        animals        |           |     ticket_sales      |
+-----------------------+           +-----------------------+
| id (PK)               |           | id (PK)               |
| name                  |           | ticket_type           |
| species               |           | quantity              |
| age_years             |           | unit_price_cents      |
| dietary_category      |           | total_cents           |
| enclosure_id (FK) ----+           | sold_at               |
| feeding_time          |           +-----------------------+
+-----------------------+
```

---

## 3. Key Invariants & Rules

### A. Enclosure Capacity Enforcement
Before admitting an animal:
1. `service.add_animal()` queries `repo.count_animals_in_enclosure(enclosure_id)`.
2. If `current_count >= enclosure.max_capacity`, an `EnclosureCapacityExceededError` is raised with a descriptive message.
3. This guarantees animals are never overcrowded beyond veterinary safety limits.

### B. Minor-Unit Admission Ticketing
Ticket prices are strictly managed in cents:
- **ADULT**: $20.00 (`2000` cents)
- **CHILD**: $10.00 (`1000` cents)
- **SENIOR**: $15.00 (`1500` cents)

Total sales are summed via SQLite integer arithmetic (`SUM(total_cents)`), eliminating floating-point rounding drift.

---

## 4. Sample CLI Session

```text
====================================================
             ZOO MANAGEMENT SYSTEM               
====================================================
 1. View Zoo Enclosures & Occupancy
 2. View Daily Animal Feeding Timetable
 3. Add Animal Resident (Capacity Enforced)
 4. Create Habitat Enclosure
 5. Staff Keepers Management
 6. Sell Admission Tickets
 7. View Daily Revenue & Sales Report
 0. Exit
====================================================
Enter choice (0-7): 1

+----+-----------------+----------+----------+-----------+-----------+
| ID | Enclosure Name  | Habitat  | Capacity | Occupancy | Available |
+----+-----------------+----------+----------+-----------+-----------+
| 3  | Arctic Tundra   | ARCTIC   | 2        | 1         | 1         |
| 1  | Savannah Plains | SAVANNAH | 4        | 2         | 2         |
| 2  | Tropical Aviary | AVIARY   | 6        | 1         | 5         |
+----+-----------------+----------+----------+-----------+-----------+
```

---

## 5. Unsolved Practice Exercises

1. **Exercise 1: Veterinary Health Records**
   - Create a `medical_examinations` table with `animal_id`, `exam_date`, `veterinarian_name`, `diagnosis`, and `treatment_notes`.
   - Prevent discharging or transferring an animal if an open medical treatment is flagged.
2. **Exercise 2: Predator-Prey Incompatibility Rule**
   - Ensure that a `CARNIVORE` cannot be placed into the same enclosure as a `HERBIVORE` regardless of remaining enclosure capacity.
