"""Tests for Project 06: Bus Reservation System."""

from pathlib import Path
from unittest.mock import patch

import pytest

from common.clock import FrozenClock
from projects.p06_bus_reservation.cli import run_cli
from projects.p06_bus_reservation.repository import BusRepository
from projects.p06_bus_reservation.service import (
    BusService,
    InvalidSeatError,
    SeatAlreadyBookedError,
)


@pytest.fixture
def bus_setup() -> tuple[BusRepository, BusService, FrozenClock]:
    clock = FrozenClock("2026-11-15T08:00:00")
    repo = BusRepository.in_memory()
    service = BusService(repo, clock=clock)
    return repo, service, clock


def test_bus_and_route_and_schedule_creation(
    bus_setup: tuple[BusRepository, BusService, FrozenClock],
) -> None:
    _, service, _ = bus_setup
    bus = service.register_bus("TEST-01", "AC_SEATER", 20)
    route = service.add_route("CityA", "CityB", 200.0)
    assert bus.id is not None
    assert route.id is not None

    sch = service.schedule_trip(
        bus_id=bus.id,
        route_id=route.id,
        departure_time="2026-11-15T12:00:00",
        arrival_time="2026-11-15T15:00:00",
        fare_cents=5000,
    )
    assert sch.id is not None

    details = service.list_schedules()
    assert len(details) == 1
    assert details[0].bus_number == "TEST-01"
    assert details[0].available_seats == 20


def test_seat_map_layout(
    bus_setup: tuple[BusRepository, BusService, FrozenClock],
) -> None:
    _, service, _ = bus_setup
    bus = service.register_bus("TEST-02", "AC_SLEEPER", 12)
    route = service.add_route("CityA", "CityB", 150.0)
    assert bus.id is not None
    assert route.id is not None

    sch = service.schedule_trip(
        bus.id, route.id, "2026-11-15T12:00:00", "2026-11-15T15:00:00", 4000
    )
    assert sch.id is not None

    service.book_seat(sch.id, "Alice", "555-1111", 1)
    layout = service.get_seat_layout(sch.id)

    assert "[Driver]" in layout
    assert "[ X ]" in layout  # Booked seat 1
    assert "[ 2 ]" in layout  # Available seat 2
    assert "Available: 11" in layout


def test_double_booking_prevention_and_rebooking_after_cancellation(
    bus_setup: tuple[BusRepository, BusService, FrozenClock],
) -> None:
    _, service, _ = bus_setup
    bus = service.register_bus("TEST-03", "EXPRESS", 10)
    route = service.add_route("CityA", "CityB", 100.0)
    assert bus.id is not None
    assert route.id is not None

    sch = service.schedule_trip(
        bus.id, route.id, "2026-11-15T12:00:00", "2026-11-15T14:00:00", 3000
    )
    assert sch.id is not None

    # Invalid seat number
    with pytest.raises(InvalidSeatError):
        service.book_seat(sch.id, "Invalid", "555", 99)

    # First booking succeeds
    b1 = service.book_seat(sch.id, "Passenger1", "555-0001", 3)
    assert b1.id is not None

    # Double booking the same seat raises error
    with pytest.raises(SeatAlreadyBookedError):
        service.book_seat(sch.id, "Passenger2", "555-0002", 3)

    # Cancel first booking
    service.cancel_booking(b1.id)

    # Now booking the exact same seat should succeed!
    b2 = service.book_seat(sch.id, "Passenger2", "555-0002", 3)
    assert b2.id is not None
    assert b2.passenger_name == "Passenger2"


def test_cancellation_refund_tiers(
    bus_setup: tuple[BusRepository, BusService, FrozenClock],
) -> None:
    _, service, clock = bus_setup
    bus = service.register_bus("TEST-04", "EXPRESS", 10)
    route = service.add_route("CityA", "CityB", 100.0)
    assert bus.id is not None
    assert route.id is not None

    # Trip departs at 12:00:00. Fare is $100.00 (10000 cents)
    sch = service.schedule_trip(
        bus.id, route.id, "2026-11-15T12:00:00", "2026-11-15T14:00:00", 10000
    )
    assert sch.id is not None

    # Case 1: At 08:00:00 (4 hours before departure > 2h) -> 80% refund ($80.00)
    b1 = service.book_seat(sch.id, "P1", "555-0001", 1)
    assert b1.id is not None
    refund1 = service.cancel_booking(b1.id)
    assert refund1 == 8000

    # Case 2: Advance clock to 11:00:00 (1h before departure, 30m-2h) -> 50% refund ($50.00)
    clock.set_time("2026-11-15T11:00:00")
    b2 = service.book_seat(sch.id, "P2", "555-0002", 2)
    assert b2.id is not None
    refund2 = service.cancel_booking(b2.id)
    assert refund2 == 5000

    # Case 3: Advance clock to 11:45:00 (15 minutes before departure <= 30m) -> 0% refund ($0.00)
    clock.set_time("2026-11-15T11:45:00")
    b3 = service.book_seat(sch.id, "P3", "555-0003", 3)
    assert b3.id is not None
    refund3 = service.cancel_booking(b3.id)
    assert refund3 == 0


def test_ticket_safe_non_overwriting_file_export(
    tmp_path: Path,
    bus_setup: tuple[BusRepository, BusService, FrozenClock],
) -> None:
    _, service, _ = bus_setup
    bus = service.register_bus("TEST-05", "EXPRESS", 10)
    route = service.add_route("CityA", "CityB", 100.0)
    assert bus.id is not None
    assert route.id is not None

    sch = service.schedule_trip(
        bus.id, route.id, "2026-11-15T12:00:00", "2026-11-15T14:00:00", 2500
    )
    assert sch.id is not None

    b1 = service.book_seat(sch.id, "Alice", "555-1234", 1)
    assert b1.id is not None
    receipt = service.get_ticket_receipt(b1.id)

    # First save -> creates ticket_1.txt
    file1 = service.save_ticket_to_file(receipt, tmp_path)
    assert file1.name == f"ticket_{b1.id}.txt"
    assert file1.exists()

    # Second save of same ticket receipt -> must create ticket_1_1.txt, NOT overwrite file1
    file2 = service.save_ticket_to_file(receipt, tmp_path)
    assert file2.name == f"ticket_{b1.id}_1.txt"
    assert file2.exists()
    assert file1.exists()


def test_cli_handles_eof_gracefully(
    bus_setup: tuple[BusRepository, BusService, FrozenClock],
) -> None:
    _, service, _ = bus_setup
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)
