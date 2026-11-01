# Project 06: Bus Reservation System

An intermediate Python terminal application that teaches fleet scheduling, text visual seat layouts, partial database unique constraints to prevent double-booking, multi-tier refund calculation, and safe non-overwriting file generation.

---

## 1. Architecture & Design

The application follows the layered architecture:

- **`models.py`**: Immutable dataclasses (`Bus`, `Route`, `Schedule`, `ScheduleDetail`, `Booking`, `TicketReceipt`) validating business ranges (positive fares, seat numbers, non-empty names).
- **`repository.py`**: Prepared SQLite transactions, foreign key cascades, and a **partial unique index** (`uq_schedule_seat_active`) that prevents conflicting seat bookings while allowing cancelled seats to be booked again.
- **`service.py`**:
  - **Seat Map Visualizer**: Formats a 2x2 aisle layout showing reserved `[ X ]` and available `[ # ]` seats.
  - **Double-Booking Prevention**: Validates bounds and relies on database atomicity.
  - **Refund Calculator**: Tiered refund policies based on departure time difference.
  - **Safe Ticket Exporter**: Uses exclusive file creation (`open(..., 'x')`) and dynamic suffix numbering to guarantee existing tickets are never overwritten.
- **`cli.py`**: Terminal user interface with tabular schedule views and safe input prompts.

---

## 2. Database Schema & Relationships

```text
+-----------------------+           +-----------------------+
|         buses         |           |        routes         |
+-----------------------+           +-----------------------+
| id (PK)               |<----+     | id (PK)               |<----+
| bus_number (UNIQUE)   |     |     | origin                |     |
| bus_type              |     |     | destination           |     |
| total_seats           |     |     | distance_km           |     |
+-----------------------+     |     +-----------------------+     |
                              |                 ^                 |
                              |                 |                 |
                   +----------+---------+       |                 |
                   |     schedules      |       |                 |
                   +--------------------+       |                 |
                   | id (PK)            |       |                 |
                   | bus_id (FK) -------+       |                 |
                   | route_id (FK) -----+-------+                 |
                   | departure_time     |                         |
                   | arrival_time       |                         |
                   | fare_cents         |                         |
                   +--------------------+                         |
                              ^                                   |
                              |                                   |
                   +----------+---------+                         |
                   |      bookings      |                         |
                   +--------------------+                         |
                   | id (PK)            |                         |
                   | schedule_id (FK) --+                         |
                   | passenger_name     |                         |
                   | passenger_phone    |                         |
                   | seat_number        |                         |
                   | fare_paid_cents    |                         |
                   | status ('CONFIRMED'|                         |
                   |         'CANCELLED')                         |
                   | created_at         |                         |
                   | cancelled_at       |                         |
                   | refund_cents       |                         |
                   +--------------------+                         |
                   | UNIQUE(schedule_id,|                         |
                   |   seat_number)     |                         |
                   | WHERE status =     |                         |
                   |   'CONFIRMED'      |                         |
                   +--------------------+                         |
```

---

## 3. Visual Seat Map & Layout

The system renders an interactive 2x2 seat map with an aisle:

```text
=== SEAT MAP FOR BUS BUS-101 (AC_SLEEPER) ===
Total Capacity: 20 seats | Available: 18
 [Driver]
--------------------------------
  [ X ] [ X ]   [ 3 ] [ 4 ]
  [ 5 ] [ 6 ]   [ 7 ] [ 8 ]
  [ 9 ] [ 10]   [ 11] [ 12]
  [ 13] [ 14]   [ 15] [ 16]
  [ 17] [ 18]   [ 19] [ 20]
--------------------------------
Legend: [ # ] Available   [ X ] Booked
```

---

## 4. Cancellation & Refund Rules

When a passenger cancels a booking, refund eligibility depends on the time remaining before scheduled departure:

| Hours Before Departure | Refund Percentage | Example ($50.00 Fare) |
| :--- | :--- | :--- |
| **> 2.0 hours** | **80%** | **$40.00** |
| **> 0.5 hours (30 min)** | **50%** | **$25.00** |
| **<= 0.5 hours or Departed** | **0%** | **$0.00** |

Once cancelled, the seat is marked with `status = 'CANCELLED'`, which removes it from the partial unique index and immediately opens the seat for other passengers.

---

## 5. Non-Overwriting File Ticket Export

When saving a ticket receipt to disk:
1. The service checks if `ticket_<id>.txt` exists.
2. If it exists, it increments a sequence counter: `ticket_<id>_1.txt`, `ticket_<id>_2.txt`, etc.
3. It opens the file with the `'x'` exclusive mode flag (`open(path, 'x')`), which fails at the OS level if the file already exists, guaranteeing zero data loss.

---

## 6. Sample CLI Session

```text
==================================================
           BUS RESERVATION SYSTEM                 
==================================================
 1. View Available Schedules & Fares
 2. View Visual Seat Layout
 3. Book a Seat
 4. Cancel Booking & Claim Refund
 5. View / Save Ticket Receipt
 6. Register New Bus (Fleet Admin)
 7. Add Route (Fleet Admin)
 8. Schedule Trip (Fleet Admin)
 0. Exit
==================================================
Enter choice (0-8): 3
Enter Schedule ID: 1
Passenger Full Name: Dennis Ritchie
Passenger Phone Number: 555-0199
Desired Seat Number: 3

[SUCCESS] Seat #3 reserved successfully!
Booking Reference ID: #3
Fare Charged: $45.00
Would you like to print/save your ticket receipt? (y/n): y
...
```

---

## 7. Unsolved Practice Exercises

1. **Exercise 1: Round-Trip Discount Booking**
   - Implement a booking workflow that reserves an outbound seat and an inbound return seat together.
   - Apply a 10% discount to both fares if booked as a round-trip bundle.
2. **Exercise 2: Gender-Specific Seat Neighbor Rule**
   - Add a `passenger_gender` field (`M`, `F`).
   - If a female passenger reserves a seat in a 2-seat pair (e.g. seat 1 and 2), prevent an unrelated male passenger from booking the adjacent seat unless booked together.
