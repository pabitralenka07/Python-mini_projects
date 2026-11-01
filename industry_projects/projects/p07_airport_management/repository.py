"""Database repository for Airport Management System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p07_airport_management.models import (
    BoardEntry,
    Flight,
    Gate,
    Passenger,
)

AIRPORT_SCHEMA = """
CREATE TABLE IF NOT EXISTS gates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gate_number TEXT NOT NULL UNIQUE CHECK(length(trim(gate_number)) > 0),
    terminal TEXT NOT NULL CHECK(length(trim(terminal)) > 0)
);

CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number TEXT NOT NULL UNIQUE CHECK(length(trim(flight_number)) > 0),
    airline TEXT NOT NULL CHECK(length(trim(airline)) > 0),
    origin TEXT NOT NULL CHECK(length(trim(origin)) > 0),
    destination TEXT NOT NULL CHECK(length(trim(destination)) > 0),
    departure_time TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    gate_id INTEGER REFERENCES gates(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'SCHEDULED'
        CHECK(status IN ('SCHEDULED', 'BOARDING', 'DEPARTED', 'DELAYED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS passengers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL CHECK(length(trim(full_name)) > 0),
    passport_number TEXT NOT NULL CHECK(length(trim(passport_number)) > 0),
    flight_id INTEGER NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    seat_number TEXT,
    checked_in INTEGER NOT NULL DEFAULT 0 CHECK(checked_in IN (0, 1)),
    UNIQUE(flight_id, passport_number)
);

-- Ensures no two checked-in passengers share the same seat on a flight
CREATE UNIQUE INDEX IF NOT EXISTS uq_flight_seat
ON passengers(flight_id, seat_number)
WHERE seat_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_flights_departure ON flights(departure_time);
CREATE INDEX IF NOT EXISTS idx_flights_gate ON flights(gate_id);
CREATE INDEX IF NOT EXISTS idx_passengers_flight ON passengers(flight_id);
"""


class AirportRepository:
    """Manages SQLite queries for gates, flights, and passenger check-ins."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "AirportRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=AIRPORT_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    @classmethod
    def in_memory(cls) -> "AirportRepository":
        manager = DatabaseManager(
            db_path=":memory:",
            schema_sql=AIRPORT_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    # --- Gates ---

    def add_gate(self, gate: Gate) -> Gate:
        query = "INSERT INTO gates (gate_number, terminal) VALUES (?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (gate.gate_number, gate.terminal))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for gate.")
            gate_id = int(cursor.lastrowid)

        return Gate(id=gate_id, gate_number=gate.gate_number, terminal=gate.terminal)

    def get_gate(self, gate_id: int) -> Gate | None:
        query = "SELECT id, gate_number, terminal FROM gates WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (gate_id,)).fetchone()
            if not row:
                return None
            return Gate(id=row["id"], gate_number=row["gate_number"], terminal=row["terminal"])

    def list_gates(self) -> list[Gate]:
        query = "SELECT id, gate_number, terminal FROM gates ORDER BY terminal, gate_number;"
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Gate(id=r["id"], gate_number=r["gate_number"], terminal=r["terminal"]) for r in rows
            ]

    # --- Flights ---

    def add_flight(self, flight: Flight) -> Flight:
        query = """
            INSERT INTO flights (
                flight_number, airline, origin, destination,
                departure_time, arrival_time, gate_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    flight.flight_number,
                    flight.airline,
                    flight.origin,
                    flight.destination,
                    flight.departure_time,
                    flight.arrival_time,
                    flight.gate_id,
                    flight.status,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for flight.")
            fl_id = int(cursor.lastrowid)

        return Flight(
            id=fl_id,
            flight_number=flight.flight_number,
            airline=flight.airline,
            origin=flight.origin,
            destination=flight.destination,
            departure_time=flight.departure_time,
            arrival_time=flight.arrival_time,
            gate_id=flight.gate_id,
            status=flight.status,
        )

    def get_flight(self, flight_id: int) -> Flight | None:
        query = """
            SELECT id, flight_number, airline, origin, destination,
                   departure_time, arrival_time, gate_id, status
            FROM flights WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (flight_id,)).fetchone()
            if not row:
                return None
            return Flight(
                id=row["id"],
                flight_number=row["flight_number"],
                airline=row["airline"],
                origin=row["origin"],
                destination=row["destination"],
                departure_time=row["departure_time"],
                arrival_time=row["arrival_time"],
                gate_id=row["gate_id"],
                status=row["status"],
            )

    def get_flight_by_number(self, flight_number: str) -> Flight | None:
        query = """
            SELECT id, flight_number, airline, origin, destination,
                   departure_time, arrival_time, gate_id, status
            FROM flights WHERE flight_number = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (flight_number,)).fetchone()
            if not row:
                return None
            return Flight(
                id=row["id"],
                flight_number=row["flight_number"],
                airline=row["airline"],
                origin=row["origin"],
                destination=row["destination"],
                departure_time=row["departure_time"],
                arrival_time=row["arrival_time"],
                gate_id=row["gate_id"],
                status=row["status"],
            )

    def list_flights_at_gate(self, gate_id: int) -> list[Flight]:
        query = """
            SELECT id, flight_number, airline, origin, destination,
                   departure_time, arrival_time, gate_id, status
            FROM flights
            WHERE gate_id = ? AND status NOT IN ('DEPARTED', 'CANCELLED');
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (gate_id,)).fetchall()
            return [
                Flight(
                    id=r["id"],
                    flight_number=r["flight_number"],
                    airline=r["airline"],
                    origin=r["origin"],
                    destination=r["destination"],
                    departure_time=r["departure_time"],
                    arrival_time=r["arrival_time"],
                    gate_id=r["gate_id"],
                    status=r["status"],
                )
                for r in rows
            ]

    def update_flight_status(self, flight_id: int, new_status: str) -> None:
        query = "UPDATE flights SET status = ? WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (new_status, flight_id))
            if cursor.rowcount == 0:
                raise DatabaseError(f"Flight ID {flight_id} not found.")

    def assign_gate(self, flight_id: int, gate_id: int) -> None:
        query = "UPDATE flights SET gate_id = ? WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (gate_id, flight_id))
            if cursor.rowcount == 0:
                raise DatabaseError(f"Flight ID {flight_id} not found.")

    def list_board_entries(self) -> list[BoardEntry]:
        query = """
            SELECT
                f.id as flight_id,
                f.flight_number,
                f.airline,
                f.destination,
                f.departure_time,
                COALESCE(g.gate_number || ' (' || g.terminal || ')', 'TBD') as gate,
                f.status
            FROM flights f
            LEFT JOIN gates g ON f.gate_id = g.id
            ORDER BY f.departure_time ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                BoardEntry(
                    flight_id=r["flight_id"],
                    flight_number=r["flight_number"],
                    airline=r["airline"],
                    destination=r["destination"],
                    departure_time=r["departure_time"],
                    gate=r["gate"],
                    status=r["status"],
                )
                for r in rows
            ]

    # --- Passengers ---

    def add_passenger(self, passenger: Passenger) -> Passenger:
        query = """
            INSERT INTO passengers (full_name, passport_number, flight_id, seat_number, checked_in)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    passenger.full_name,
                    passenger.passport_number,
                    passenger.flight_id,
                    passenger.seat_number,
                    1 if passenger.checked_in else 0,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for passenger.")
            p_id = int(cursor.lastrowid)

        return Passenger(
            id=p_id,
            full_name=passenger.full_name,
            passport_number=passenger.passport_number,
            flight_id=passenger.flight_id,
            seat_number=passenger.seat_number,
            checked_in=passenger.checked_in,
        )

    def get_passenger(self, passenger_id: int) -> Passenger | None:
        query = """
            SELECT id, full_name, passport_number, flight_id, seat_number, checked_in
            FROM passengers WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (passenger_id,)).fetchone()
            if not row:
                return None
            return Passenger(
                id=row["id"],
                full_name=row["full_name"],
                passport_number=row["passport_number"],
                flight_id=row["flight_id"],
                seat_number=row["seat_number"],
                checked_in=bool(row["checked_in"]),
            )

    def get_passenger_by_passport(self, flight_id: int, passport: str) -> Passenger | None:
        query = """
            SELECT id, full_name, passport_number, flight_id, seat_number, checked_in
            FROM passengers WHERE flight_id = ? AND passport_number = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (flight_id, passport)).fetchone()
            if not row:
                return None
            return Passenger(
                id=row["id"],
                full_name=row["full_name"],
                passport_number=row["passport_number"],
                flight_id=row["flight_id"],
                seat_number=row["seat_number"],
                checked_in=bool(row["checked_in"]),
            )

    def get_occupied_seats(self, flight_id: int) -> set[str]:
        query = (
            "SELECT seat_number FROM passengers WHERE flight_id = ? AND seat_number IS NOT NULL;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (flight_id,)).fetchall()
            return {r["seat_number"] for r in rows}

    def check_in_passenger(self, passenger_id: int, seat_number: str) -> None:
        query = "UPDATE passengers SET seat_number = ?, checked_in = 1 WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (seat_number, passenger_id))
            if cursor.rowcount == 0:
                raise DatabaseError(f"Passenger ID {passenger_id} not found.")
