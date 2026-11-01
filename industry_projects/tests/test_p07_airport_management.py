"""Tests for Project 07: Airport Management System."""

from unittest.mock import patch

import pytest

from common.clock import FrozenClock
from projects.p07_airport_management.cli import run_cli
from projects.p07_airport_management.models import FlightStatus
from projects.p07_airport_management.repository import AirportRepository
from projects.p07_airport_management.service import (
    AirportService,
    CheckInNotAllowedError,
    GateConflictError,
    InvalidFlightStatusTransitionError,
    SeatAlreadyAssignedError,
)


@pytest.fixture
def airport_setup() -> tuple[AirportRepository, AirportService, FrozenClock]:
    clock = FrozenClock("2026-11-20T08:00:00")
    repo = AirportRepository.in_memory()
    service = AirportService(repo, clock=clock)
    return repo, service, clock


def test_gate_and_flight_creation(
    airport_setup: tuple[AirportRepository, AirportService, FrozenClock],
) -> None:
    _, service, _ = airport_setup
    gate = service.register_gate("C1", "Terminal 3")
    assert gate.id is not None

    flight = service.schedule_flight(
        flight_number="TEST-100",
        airline="Test Air",
        origin="JFK",
        destination="MIA",
        departure_time="2026-11-20T10:00:00",
        arrival_time="2026-11-20T13:00:00",
        gate_id=gate.id,
    )
    assert flight.id is not None
    assert flight.status == FlightStatus.SCHEDULED


def test_flight_status_state_machine_valid_and_invalid_transitions(
    airport_setup: tuple[AirportRepository, AirportService, FrozenClock],
) -> None:
    _, service, _ = airport_setup
    f = service.schedule_flight(
        flight_number="TEST-200",
        airline="Test Air",
        origin="JFK",
        destination="ORD",
        departure_time="2026-11-20T12:00:00",
        arrival_time="2026-11-20T14:00:00",
    )
    assert f.id is not None

    # Invalid: Cannot jump straight from SCHEDULED to DEPARTED
    with pytest.raises(InvalidFlightStatusTransitionError, match="Cannot transition"):
        service.update_flight_status(f.id, FlightStatus.DEPARTED)

    # Valid: SCHEDULED -> BOARDING
    service.update_flight_status(f.id, FlightStatus.BOARDING)
    assert service.get_flight(f.id).status == FlightStatus.BOARDING

    # Valid: BOARDING -> DEPARTED
    service.update_flight_status(f.id, FlightStatus.DEPARTED)
    assert service.get_flight(f.id).status == FlightStatus.DEPARTED

    # Invalid: DEPARTED is terminal, cannot transition back to BOARDING or SCHEDULED
    with pytest.raises(InvalidFlightStatusTransitionError):
        service.update_flight_status(f.id, FlightStatus.BOARDING)


def test_gate_overlap_rejection(
    airport_setup: tuple[AirportRepository, AirportService, FrozenClock],
) -> None:
    _, service, _ = airport_setup
    gate = service.register_gate("D1", "Terminal 4")
    assert gate.id is not None

    f1 = service.schedule_flight(
        flight_number="FLIGHT-1",
        airline="Airline 1",
        origin="JFK",
        destination="BOS",
        departure_time="2026-11-20T10:00:00",
        arrival_time="2026-11-20T11:15:00",
        gate_id=gate.id,
    )
    assert f1.id is not None

    # Flight 2 departs at 10:30:00 (only 30 minutes after Flight 1; buffer is 60 mins)
    f2 = service.schedule_flight(
        flight_number="FLIGHT-2",
        airline="Airline 2",
        origin="JFK",
        destination="DCA",
        departure_time="2026-11-20T10:30:00",
        arrival_time="2026-11-20T11:45:00",
    )
    assert f2.id is not None

    with pytest.raises(GateConflictError, match="Gate conflict"):
        service.assign_gate(f2.id, gate.id, turnaround_minutes=60)

    # Flight 3 departs at 11:30:00 (90 minutes after Flight 1; >= 60 min buffer)
    f3 = service.schedule_flight(
        flight_number="FLIGHT-3",
        airline="Airline 3",
        origin="JFK",
        destination="MCO",
        departure_time="2026-11-20T11:30:00",
        arrival_time="2026-11-20T14:00:00",
    )
    assert f3.id is not None

    # Assigning gate to Flight 3 should succeed
    service.assign_gate(f3.id, gate.id, turnaround_minutes=60)
    assert service.get_flight(f3.id).gate_id == gate.id


def test_passenger_check_in_and_seat_assignment(
    airport_setup: tuple[AirportRepository, AirportService, FrozenClock],
) -> None:
    _, service, _ = airport_setup
    f = service.schedule_flight(
        flight_number="FLIGHT-4",
        airline="Airline 4",
        origin="JFK",
        destination="SEA",
        departure_time="2026-11-20T15:00:00",
        arrival_time="2026-11-20T18:00:00",
    )
    assert f.id is not None

    p1 = service.register_passenger("John Smith", "PASSPORT-1", f.id)
    p2 = service.register_passenger("Mary Smith", "PASSPORT-2", f.id)
    assert p1.id is not None
    assert p2.id is not None

    # Check in passenger 1 to 14A
    service.check_in(p1.id, "14A")
    updated_p1 = service.repo.get_passenger(p1.id)
    assert updated_p1 is not None
    assert updated_p1.checked_in is True
    assert updated_p1.seat_number == "14A"

    # Passenger 2 cannot take seat 14A on the same flight
    with pytest.raises(SeatAlreadyAssignedError):
        service.check_in(p2.id, "14A")

    # Passenger 2 takes seat 14B succeeds
    service.check_in(p2.id, "14B")
    updated_p2 = service.repo.get_passenger(p2.id)
    assert updated_p2 is not None
    assert updated_p2.seat_number == "14B"


def test_check_in_blocked_on_departed_flight(
    airport_setup: tuple[AirportRepository, AirportService, FrozenClock],
) -> None:
    _, service, _ = airport_setup
    f = service.schedule_flight(
        flight_number="FLIGHT-5",
        airline="Airline 5",
        origin="JFK",
        destination="ATL",
        departure_time="2026-11-20T09:00:00",
        arrival_time="2026-11-20T11:30:00",
    )
    assert f.id is not None
    p = service.register_passenger("Late Traveler", "PASSPORT-99", f.id)
    assert p.id is not None

    # Transition flight to BOARDING then DEPARTED
    service.update_flight_status(f.id, FlightStatus.BOARDING)
    service.update_flight_status(f.id, FlightStatus.DEPARTED)

    # Check in should now be blocked
    with pytest.raises(CheckInNotAllowedError, match="Cannot check in"):
        service.check_in(p.id, "1A")


def test_cli_handles_eof_gracefully(
    airport_setup: tuple[AirportRepository, AirportService, FrozenClock],
) -> None:
    _, service, _ = airport_setup
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)
