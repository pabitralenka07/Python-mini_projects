"""Database repository for Bus Reservation System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p06_bus_reservation.models import (
    Booking,
    Bus,
    Route,
    Schedule,
    ScheduleDetail,
)

BUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS buses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_number TEXT NOT NULL UNIQUE CHECK(length(trim(bus_number)) > 0),
    bus_type TEXT NOT NULL,
    total_seats INTEGER NOT NULL CHECK(total_seats > 0)
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL CHECK(length(trim(origin)) > 0),
    destination TEXT NOT NULL CHECK(length(trim(destination)) > 0),
    distance_km REAL NOT NULL CHECK(distance_km > 0)
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_id INTEGER NOT NULL REFERENCES buses(id) ON DELETE RESTRICT,
    route_id INTEGER NOT NULL REFERENCES routes(id) ON DELETE RESTRICT,
    departure_time TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    fare_cents INTEGER NOT NULL CHECK(fare_cents >= 0)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE RESTRICT,
    passenger_name TEXT NOT NULL CHECK(length(trim(passenger_name)) > 0),
    passenger_phone TEXT NOT NULL CHECK(length(trim(passenger_phone)) > 0),
    seat_number INTEGER NOT NULL CHECK(seat_number > 0),
    fare_paid_cents INTEGER NOT NULL CHECK(fare_paid_cents >= 0),
    status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK(status IN ('CONFIRMED', 'CANCELLED')),
    created_at TEXT NOT NULL,
    cancelled_at TEXT,
    refund_cents INTEGER NOT NULL DEFAULT 0 CHECK(refund_cents >= 0)
);

-- Partial unique index ensures no two CONFIRMED bookings can share the same seat on a schedule
CREATE UNIQUE INDEX IF NOT EXISTS uq_schedule_seat_active
ON bookings(schedule_id, seat_number)
WHERE status = 'CONFIRMED';

CREATE INDEX IF NOT EXISTS idx_schedules_bus ON schedules(bus_id);
CREATE INDEX IF NOT EXISTS idx_schedules_route ON schedules(route_id);
CREATE INDEX IF NOT EXISTS idx_bookings_schedule ON bookings(schedule_id);
"""


class BusRepository:
    """Manages SQLite queries for fleet buses, routes, schedules, and seat bookings."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "BusRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=BUS_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    @classmethod
    def in_memory(cls) -> "BusRepository":
        manager = DatabaseManager(
            db_path=":memory:",
            schema_sql=BUS_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)


    def add_bus(self, bus: Bus) -> Bus:
        query = "INSERT INTO buses (bus_number, bus_type, total_seats) VALUES (?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (bus.bus_number, bus.bus_type, bus.total_seats))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for bus.")
            bus_id = int(cursor.lastrowid)

        return Bus(
            id=bus_id,
            bus_number=bus.bus_number,
            bus_type=bus.bus_type,
            total_seats=bus.total_seats,
        )

    def get_bus(self, bus_id: int) -> Bus | None:
        query = "SELECT id, bus_number, bus_type, total_seats FROM buses WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (bus_id,)).fetchone()
            if not row:
                return None
            return Bus(
                id=row["id"],
                bus_number=row["bus_number"],
                bus_type=row["bus_type"],
                total_seats=row["total_seats"],
            )

    def list_buses(self) -> list[Bus]:
        query = "SELECT id, bus_number, bus_type, total_seats FROM buses ORDER BY bus_number ASC;"
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Bus(
                    id=r["id"],
                    bus_number=r["bus_number"],
                    bus_type=r["bus_type"],
                    total_seats=r["total_seats"],
                )
                for r in rows
            ]


    def add_route(self, route: Route) -> Route:
        query = "INSERT INTO routes (origin, destination, distance_km) VALUES (?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (route.origin, route.destination, route.distance_km))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for route.")
            route_id = int(cursor.lastrowid)

        return Route(
            id=route_id,
            origin=route.origin,
            destination=route.destination,
            distance_km=route.distance_km,
        )

    def get_route(self, route_id: int) -> Route | None:
        query = "SELECT id, origin, destination, distance_km FROM routes WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (route_id,)).fetchone()
            if not row:
                return None
            return Route(
                id=row["id"],
                origin=row["origin"],
                destination=row["destination"],
                distance_km=row["distance_km"],
            )

    def list_routes(self) -> list[Route]:
        query = (
            "SELECT id, origin, destination, distance_km FROM routes ORDER BY origin, destination;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Route(
                    id=r["id"],
                    origin=r["origin"],
                    destination=r["destination"],
                    distance_km=r["distance_km"],
                )
                for r in rows
            ]


    def add_schedule(self, schedule: Schedule) -> Schedule:
        query = """
            INSERT INTO schedules (bus_id, route_id, departure_time, arrival_time, fare_cents)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    schedule.bus_id,
                    schedule.route_id,
                    schedule.departure_time,
                    schedule.arrival_time,
                    schedule.fare_cents,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for schedule.")
            sch_id = int(cursor.lastrowid)

        return Schedule(
            id=sch_id,
            bus_id=schedule.bus_id,
            route_id=schedule.route_id,
            departure_time=schedule.departure_time,
            arrival_time=schedule.arrival_time,
            fare_cents=schedule.fare_cents,
        )

    def get_schedule(self, schedule_id: int) -> Schedule | None:
        query = (
            "SELECT id, bus_id, route_id, departure_time, arrival_time, fare_cents "
            "FROM schedules WHERE id = ?;"
        )
        with self.db.get_connection() as conn:
            row = conn.execute(query, (schedule_id,)).fetchone()
            if not row:
                return None
            return Schedule(
                id=row["id"],
                bus_id=row["bus_id"],
                route_id=row["route_id"],
                departure_time=row["departure_time"],
                arrival_time=row["arrival_time"],
                fare_cents=row["fare_cents"],
            )

    def list_schedule_details(self) -> list[ScheduleDetail]:
        query = """
            SELECT
                s.id as schedule_id,
                b.bus_number,
                b.bus_type,
                b.total_seats,
                r.origin,
                r.destination,
                s.departure_time,
                s.arrival_time,
                s.fare_cents,
                (b.total_seats - (
                    SELECT COUNT(*) FROM bookings bk
                    WHERE bk.schedule_id = s.id AND bk.status = 'CONFIRMED'
                )) as available_seats
            FROM schedules s
            JOIN buses b ON s.bus_id = b.id
            JOIN routes r ON s.route_id = r.id
            ORDER BY s.departure_time ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                ScheduleDetail(
                    schedule_id=r["schedule_id"],
                    bus_number=r["bus_number"],
                    bus_type=r["bus_type"],
                    total_seats=r["total_seats"],
                    origin=r["origin"],
                    destination=r["destination"],
                    departure_time=r["departure_time"],
                    arrival_time=r["arrival_time"],
                    fare_cents=r["fare_cents"],
                    available_seats=r["available_seats"],
                )
                for r in rows
            ]


    def create_booking(self, booking: Booking) -> Booking:
        query = """
            INSERT INTO bookings (
                schedule_id, passenger_name, passenger_phone, seat_number,
                fare_paid_cents, status, created_at, cancelled_at, refund_cents
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    booking.schedule_id,
                    booking.passenger_name,
                    booking.passenger_phone,
                    booking.seat_number,
                    booking.fare_paid_cents,
                    booking.status,
                    booking.created_at,
                    booking.cancelled_at,
                    booking.refund_cents,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for booking.")
            book_id = int(cursor.lastrowid)

        return Booking(
            id=book_id,
            schedule_id=booking.schedule_id,
            passenger_name=booking.passenger_name,
            passenger_phone=booking.passenger_phone,
            seat_number=booking.seat_number,
            fare_paid_cents=booking.fare_paid_cents,
            status=booking.status,
            created_at=booking.created_at,
            cancelled_at=booking.cancelled_at,
            refund_cents=booking.refund_cents,
        )

    def get_booking(self, booking_id: int) -> Booking | None:
        query = """
            SELECT id, schedule_id, passenger_name, passenger_phone, seat_number,
                   fare_paid_cents, status, created_at, cancelled_at, refund_cents
            FROM bookings WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (booking_id,)).fetchone()
            if not row:
                return None
            return Booking(
                id=row["id"],
                schedule_id=row["schedule_id"],
                passenger_name=row["passenger_name"],
                passenger_phone=row["passenger_phone"],
                seat_number=row["seat_number"],
                fare_paid_cents=row["fare_paid_cents"],
                status=row["status"],
                created_at=row["created_at"],
                cancelled_at=row["cancelled_at"],
                refund_cents=row["refund_cents"],
            )

    def get_active_seat_numbers(self, schedule_id: int) -> set[int]:
        query = "SELECT seat_number FROM bookings WHERE schedule_id = ? AND status = 'CONFIRMED';"
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (schedule_id,)).fetchall()
            return {int(r["seat_number"]) for r in rows}

    def cancel_booking(self, booking_id: int, cancelled_at: str, refund_cents: int) -> None:
        query = """
            UPDATE bookings
            SET status = 'CANCELLED', cancelled_at = ?, refund_cents = ?
            WHERE id = ? AND status = 'CONFIRMED';
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (cancelled_at, refund_cents, booking_id))
            if cursor.rowcount == 0:
                raise DatabaseError(
                    f"Booking {booking_id} could not be cancelled or was already cancelled."
                )
