# Project 07: Airport Management System

An airport operations management terminal application demonstrating relational database constraints, strict finite state machine transitions, gate turnaround buffer conflict detection, and passenger check-in seat guarantees.

---

## 1. Architecture & Design

The application follows the layered separation of concerns:

- **`models.py`**: Immutable dataclasses (`Gate`, `Flight`, `Passenger`, `BoardEntry`) and a `FlightStatus` enum (`SCHEDULED`, `BOARDING`, `DEPARTED`, `DELAYED`, `CANCELLED`).
- **`repository.py`**: SQLite data access with foreign keys, prepared queries, and a partial unique index (`uq_flight_seat`) preventing duplicate seat assignments while allowing passengers without seats to be registered.
- **`service.py`**:
  - **State Machine Engine**: Enforces valid flight lifecycle state transitions. Prevents illegal moves like `DEPARTED` -> `BOARDING` or reviving `CANCELLED` flights.
  - **Gate Overlap Guard**: Enforces a minimum 60-minute turnaround buffer between flights assigned to the same boarding gate.
  - **Passenger Check-in Gatekeeper**: Ensures check-in can only occur when flights are in `SCHEDULED` or `BOARDING` status, and rejects duplicate seat allocations.
  - **Departure Board Generator**: Queries composite flight board entries.
- **`cli.py`**: Interactive terminal flight board interface with tabular formatting.

---

## 2. Database Schema & Relationships

```text
+-----------------------+           +-----------------------+
|         gates         |           |        flights        |
+-----------------------+           +-----------------------+
| id (PK)               |<----+     | id (PK)               |<----+
| gate_number (UNIQUE)  |     |     | flight_number (UNIQUE)|     |
| terminal              |     |     | airline               |     |
+-----------------------+     |     | origin, destination   |     |
                              +-----+ gate_id (FK, NULLABLE)|     |
                                    | departure_time        |     |
                                    | arrival_time          |     |
                                    | status                |     |
                                    +-----------------------+     |
                                                ^                 |
                                                |                 |
                                     +----------+---------+       |
                                     |     passengers     |       |
                                     +--------------------+       |
                                     | id (PK)            |       |
                                     | full_name          |       |
                                     | passport_number    |       |
                                     | flight_id (FK) ----+-------+
                                     | seat_number (NULL) |
                                     | checked_in (0 / 1) |
                                     +--------------------+
                                     | UNIQUE(flight_id,  |
                                     |   passport_number) |
                                     | UNIQUE(flight_id,  |
                                     |   seat_number)     |
                                     | WHERE seat_number  |
                                     |   IS NOT NULL      |
                                     +--------------------+
```

---

## 3. Finite State Machine for Flight Status

Commercial flight lifecycles follow a strict state machine:

```text
               +------------+
               | SCHEDULED  |
               +------------+
                 /    |    \
                /     |     \
               v      |      v
        +-----------+ |   +-----------+
        |  DELAYED  | |   | CANCELLED | (Terminal)
        +-----------+ |   +-----------+
              \       |         ^
               \      |        /
                v     v       /
               +------------+/
               |  BOARDING  |
               +------------+
                     |
                     v
               +------------+
               |  DEPARTED  | (Terminal)
               +------------+
```

### Transition Matrix:
- `SCHEDULED` -> `BOARDING`, `DELAYED`, `CANCELLED`
- `DELAYED`   -> `BOARDING`, `CANCELLED`
- `BOARDING`  -> `DEPARTED`, `CANCELLED`
- `DEPARTED`  -> None (Terminal state, cannot transition)
- `CANCELLED` -> None (Terminal state, cannot transition)

Any other transition raises `InvalidFlightStatusTransitionError`.

---

## 4. Gate Conflict & Turnaround Buffer Rule

When a flight is assigned to Gate G:
1. The service searches for all existing active flights (not `DEPARTED` or `CANCELLED`) assigned to Gate G.
2. For each flight, the difference in departure time is computed: `abs(dep_A - dep_B)`.
3. If `minutes_diff < 60`, `GateConflictError` is raised. This models real-world gate taxiing, baggage turnaround, and aircraft servicing.

---

## 5. Sample CLI Session

```text
====================================================
           AIRPORT MANAGEMENT SYSTEM             
====================================================
 1. View Airport Flight Board (Departures)
 2. Passenger Check-In & Seat Assignment
 3. Assign Gate to Flight (Overlap Detection)
 4. Update Flight Status (State Machine)
 5. Schedule New Commercial Flight
 6. Register Boarding Gate
 7. Register Ticketed Passenger
 0. Exit
====================================================
Enter choice (0-7): 1

+---------+-------------------+------------------------------+---------------------+-------------+-----------+
| Flight  | Airline           | Destination                  | Departure           | Gate        | Status    |
+---------+-------------------+------------------------------+---------------------+-------------+-----------+
| AA-101  | American Airlines | LHR (London Heathrow)        | 2026-11-20T10:00:00 | A1 (Term 1) | BOARDING  |
| UA-303  | United Airlines   | SFO (San Francisco)          | 2026-11-20T11:15:00 | B1 (Term 2) | SCHEDULED |
| DL-202  | Delta Airlines    | CDG (Paris Charles de Gaulle)| 2026-11-20T14:30:00 | A1 (Term 1) | SCHEDULED |
+---------+-------------------+------------------------------+---------------------+-------------+-----------+
```

---

## 6. Unsolved Practice Exercises

1. **Exercise 1: Baggage Tracking System**
   - Create a `baggage` table with `tag_number`, `passenger_id`, `weight_kg`, and `status` (`CHECKED_IN`, `LOADED`, `OFFLOADED`, `CLAIMED`).
   - Prevent checking in more than 2 bags per passenger or bags exceeding 32 kg.
2. **Exercise 2: Automated Turnaround Delay Propagation**
   - If a flight arriving at Gate A1 is delayed past its scheduled turnaround window, write a function that automatically suggests alternative gates with zero time conflicts.
