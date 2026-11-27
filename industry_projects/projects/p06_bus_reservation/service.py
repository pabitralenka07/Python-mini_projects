"""Service layer for Bus Reservation System with seat layout, booking, and refund rules."""

import sqlite3
from datetime import datetime
from pathlib import Path

from common.clock import Clock, SystemClock
from projects.p06_bus_reservation.models import (
    Booking,
    Bus,
    Route,
    Schedule,
    ScheduleDetail,
    TicketReceipt,
)
from projects.p06_bus_reservation.repository import BusRepository


class BusError(Exception):
    """Base exception for bus reservation errors."""

    pass


class ScheduleNotFoundError(BusError):
    """Raised when schedule does not exist."""

    pass


class InvalidSeatError(BusError):
    """Raised when seat number is outside valid range."""

    pass


class SeatAlreadyBookedError(BusError):
    """Raised when a seat is already reserved."""

    pass


class BookingNotFoundError(BusError):
    """Raised when booking record does not exist."""

    pass


class BookingAlreadyCancelledError(BusError):
    """Raised when attempting to cancel an already cancelled booking."""

    pass


class BusService:
    """Coordinates fleet scheduling, seat visualization, reservations, and refunds."""

    def __init__(self, repository: BusRepository, clock: Clock | None = None) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()


    def register_bus(self, bus_number: str, bus_type: str, total_seats: int) -> Bus:
        bus = Bus(
            bus_number=bus_number.strip().upper(),
            bus_type=bus_type.strip().upper(),
            total_seats=total_seats,
        )
        return self.repo.add_bus(bus)

    def add_route(self, origin: str, destination: str, distance_km: float) -> Route:
        route = Route(
            origin=origin.strip(),
            destination=destination.strip(),
            distance_km=distance_km,
        )
        return self.repo.add_route(route)

    def schedule_trip(
        self,
        bus_id: int,
        route_id: int,
        departure_time: str,
        arrival_time: str,
        fare_cents: int,
    ) -> Schedule:
        bus = self.repo.get_bus(bus_id)
        if not bus:
            raise BusError(f"Bus ID {bus_id} not found.")

        route = self.repo.get_route(route_id)
        if not route:
            raise BusError(f"Route ID {route_id} not found.")

        sch = Schedule(
            bus_id=bus_id,
            route_id=route_id,
            departure_time=departure_time.strip(),
            arrival_time=arrival_time.strip(),
            fare_cents=fare_cents,
        )
        return self.repo.add_schedule(sch)

    def list_schedules(self) -> list[ScheduleDetail]:
        return self.repo.list_schedule_details()


    def get_seat_layout(self, schedule_id: int) -> str:
        sch = self.repo.get_schedule(schedule_id)
        if not sch:
            raise ScheduleNotFoundError(f"Schedule ID {schedule_id} not found.")

        bus = self.repo.get_bus(sch.bus_id)
        if not bus:
            raise BusError(f"Bus for schedule {schedule_id} not found.")

        booked_seats = self.repo.get_active_seat_numbers(schedule_id)
        lines: list[str] = [
            f"=== SEAT MAP FOR BUS {bus.bus_number} ({bus.bus_type}) ===",
            (
                f"Total Capacity: {bus.total_seats} seats | "
                f"Available: {bus.total_seats - len(booked_seats)}"
            ),
            " [Driver]",
            "-" * 32,
        ]

        row_seats: list[str] = []
        for seat_num in range(1, bus.total_seats + 1):
            marker = "[ X ]" if seat_num in booked_seats else f"[{seat_num:^3d}]"
            row_seats.append(marker)

            if len(row_seats) == 2:
                row_seats.append("   ")

            if len(row_seats) == 5:
                lines.append("  " + "".join(row_seats))
                row_seats = []

        if row_seats:
            lines.append("  " + "".join(row_seats))

        lines.append("-" * 32)
        lines.append("Legend: [ # ] Available   [ X ] Booked")
        return "\n".join(lines)


    def book_seat(
        self,
        schedule_id: int,
        passenger_name: str,
        passenger_phone: str,
        seat_number: int,
    ) -> Booking:
        sch = self.repo.get_schedule(schedule_id)
        if not sch:
            raise ScheduleNotFoundError(f"Schedule ID {schedule_id} not found.")

        bus = self.repo.get_bus(sch.bus_id)
        if not bus:
            raise BusError(f"Bus for schedule {schedule_id} not found.")

        if seat_number < 1 or seat_number > bus.total_seats:
            raise InvalidSeatError(
                f"Seat number {seat_number} is invalid. Valid range: 1 to {bus.total_seats}."
            )

        booked_seats = self.repo.get_active_seat_numbers(schedule_id)
        if seat_number in booked_seats:
            raise SeatAlreadyBookedError(
                f"Seat {seat_number} is already booked on schedule {schedule_id}."
            )

        now_iso = self.clock.now_iso()
        booking = Booking(
            schedule_id=schedule_id,
            passenger_name=passenger_name.strip(),
            passenger_phone=passenger_phone.strip(),
            seat_number=seat_number,
            fare_paid_cents=sch.fare_cents,
            status="CONFIRMED",
            created_at=now_iso,
        )

        try:
            return self.repo.create_booking(booking)
        except sqlite3.IntegrityError as err:
            raise SeatAlreadyBookedError(
                f"Seat {seat_number} was just booked by another passenger."
            ) from err


    def get_ticket_receipt(self, booking_id: int) -> TicketReceipt:
        booking = self.repo.get_booking(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Booking ID {booking_id} not found.")

        sch = self.repo.get_schedule(booking.schedule_id)
        if not sch:
            raise ScheduleNotFoundError(f"Schedule ID {booking.schedule_id} not found.")

        bus = self.repo.get_bus(sch.bus_id)
        route = self.repo.get_route(sch.route_id)

        return TicketReceipt(
            booking_id=booking_id,
            passenger_name=booking.passenger_name,
            passenger_phone=booking.passenger_phone,
            bus_number=bus.bus_number if bus else "N/A",
            bus_type=bus.bus_type if bus else "N/A",
            origin=route.origin if route else "N/A",
            destination=route.destination if route else "N/A",
            departure_time=sch.departure_time,
            arrival_time=sch.arrival_time,
            seat_number=booking.seat_number,
            fare_paid_cents=booking.fare_paid_cents,
            booking_time=booking.created_at,
        )

    def format_ticket(self, receipt: TicketReceipt) -> str:
        dollars = receipt.fare_paid_cents / 100.0
        lines = [
            "==================================================",
            "             BUS TRAVEL TICKET RECEIPT            ",
            "==================================================",
            f" Ticket / Booking ID : #{receipt.booking_id}",
            f" Passenger Name      : {receipt.passenger_name}",
            f" Passenger Phone     : {receipt.passenger_phone}",
            "--------------------------------------------------",
            f" Bus Number          : {receipt.bus_number} ({receipt.bus_type})",
            f" Journey Route       : {receipt.origin} -> {receipt.destination}",
            f" Departure           : {receipt.departure_time}",
            f" Estimated Arrival   : {receipt.arrival_time}",
            f" Seat Number         : Seat #{receipt.seat_number}",
            f" Total Fare Paid     : ${dollars:.2f}",
            f" Booked At           : {receipt.booking_time}",
            "==================================================",
            "   Have a safe journey! Keep this ticket safe.   ",
            "==================================================",
        ]
        return "\n".join(lines)

    def save_ticket_to_file(self, receipt: TicketReceipt, directory: Path) -> Path:
        """Saves ticket receipt to a file without overwriting any existing files."""
        directory.mkdir(parents=True, exist_ok=True)
        base_name = f"ticket_{receipt.booking_id}"
        candidate = directory / f"{base_name}.txt"

        counter = 1
        while candidate.exists():
            candidate = directory / f"{base_name}_{counter}.txt"
            counter += 1

        content = self.format_ticket(receipt)
        with open(candidate, "x", encoding="utf-8") as f:
            f.write(content)

        return candidate


    def calculate_refund(self, fare_cents: int, departure_time: str) -> int:
        """Calculates refund based on hours remaining before departure:

        > 2 hours before departure: 80% refund
        > 30 mins before departure: 50% refund
        <= 30 mins or post-departure: 0% refund
        """
        now_dt = datetime.fromisoformat(self.clock.now_iso())
        dep_dt = datetime.fromisoformat(departure_time)

        if now_dt.tzinfo is not None and dep_dt.tzinfo is None:
            dep_dt = dep_dt.replace(tzinfo=now_dt.tzinfo)
        elif now_dt.tzinfo is None and dep_dt.tzinfo is not None:
            now_dt = now_dt.replace(tzinfo=dep_dt.tzinfo)

        seconds_diff = (dep_dt - now_dt).total_seconds()
        hours_diff = seconds_diff / 3600.0

        if hours_diff > 2.0:
            return int(fare_cents * 0.80)
        elif hours_diff > 0.5:
            return int(fare_cents * 0.50)
        else:
            return 0

    def cancel_booking(self, booking_id: int) -> int:
        """Cancels an active booking and returns the calculated refund in cents."""
        booking = self.repo.get_booking(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Booking ID {booking_id} not found.")

        if booking.status == "CANCELLED":
            raise BookingAlreadyCancelledError(f"Booking ID {booking_id} is already cancelled.")

        sch = self.repo.get_schedule(booking.schedule_id)
        if not sch:
            raise ScheduleNotFoundError(f"Schedule ID {booking.schedule_id} not found.")

        refund_cents = self.calculate_refund(booking.fare_paid_cents, sch.departure_time)
        now_iso = self.clock.now_iso()
        self.repo.cancel_booking(booking_id, now_iso, refund_cents)

        return refund_cents
