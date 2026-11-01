"""Service layer for Airport Management System with gate conflict guards and status transitions."""

from datetime import datetime

from common.clock import Clock, SystemClock
from projects.p07_airport_management.models import (
    BoardEntry,
    Flight,
    FlightStatus,
    Gate,
    Passenger,
)
from projects.p07_airport_management.repository import AirportRepository


class AirportError(Exception):
    """Base exception for airport operations."""

    pass


class FlightNotFoundError(AirportError):
    """Raised when flight does not exist."""

    pass


class GateNotFoundError(AirportError):
    """Raised when gate does not exist."""

    pass


class PassengerNotFoundError(AirportError):
    """Raised when passenger does not exist."""

    pass


class InvalidFlightStatusTransitionError(AirportError):
    """Raised when attempting an illegal flight status state change."""

    pass


class GateConflictError(AirportError):
    """Raised when assigning an occupied gate within the turnaround buffer window."""

    pass


class SeatAlreadyAssignedError(AirportError):
    """Raised when seat is already assigned to another passenger on the flight."""

    pass


class CheckInNotAllowedError(AirportError):
    """Raised when checking in to a flight that is departed or cancelled."""

    pass


# Valid state transitions for commercial flights
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    FlightStatus.SCHEDULED: {FlightStatus.BOARDING, FlightStatus.DELAYED, FlightStatus.CANCELLED},
    FlightStatus.BOARDING: {FlightStatus.DEPARTED, FlightStatus.CANCELLED},
    FlightStatus.DELAYED: {FlightStatus.BOARDING, FlightStatus.CANCELLED},
    FlightStatus.DEPARTED: set(),  # Terminal state
    FlightStatus.CANCELLED: set(),  # Terminal state
}


class AirportService:
    """Coordinates airport gates, flight dispatch, state machine transitions,
    and passenger check-ins.
    """

    def __init__(self, repository: AirportRepository, clock: Clock | None = None) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()

    # --- Gates & Flights Registration ---

    def register_gate(self, gate_number: str, terminal: str) -> Gate:
        gate = Gate(gate_number=gate_number.strip().upper(), terminal=terminal.strip().upper())
        return self.repo.add_gate(gate)

    def list_gates(self) -> list[Gate]:
        return self.repo.list_gates()

    def schedule_flight(
        self,
        flight_number: str,
        airline: str,
        origin: str,
        destination: str,
        departure_time: str,
        arrival_time: str,
        gate_id: int | None = None,
    ) -> Flight:
        flight = Flight(
            flight_number=flight_number.strip().upper(),
            airline=airline.strip(),
            origin=origin.strip(),
            destination=destination.strip(),
            departure_time=departure_time.strip(),
            arrival_time=arrival_time.strip(),
            gate_id=gate_id,
            status=FlightStatus.SCHEDULED,
        )
        return self.repo.add_flight(flight)

    def get_flight(self, flight_id: int) -> Flight:
        flight = self.repo.get_flight(flight_id)
        if not flight:
            raise FlightNotFoundError(f"Flight ID {flight_id} not found.")
        return flight

    def get_flight_by_number(self, flight_number: str) -> Flight:
        flight = self.repo.get_flight_by_number(flight_number.strip().upper())
        if not flight:
            raise FlightNotFoundError(f"Flight '{flight_number}' not found.")
        return flight

    # --- Gate Assignment with Overlap Rejection ---

    def assign_gate(self, flight_id: int, gate_id: int, turnaround_minutes: int = 60) -> None:
        flight = self.get_flight(flight_id)
        gate = self.repo.get_gate(gate_id)
        if not gate:
            raise GateNotFoundError(f"Gate ID {gate_id} not found.")

        target_dep = datetime.fromisoformat(flight.departure_time)

        # Inspect all non-departed/non-cancelled flights currently assigned to this gate
        existing_flights = self.repo.list_flights_at_gate(gate_id)
        for existing in existing_flights:
            if existing.id == flight.id:
                continue

            existing_dep = datetime.fromisoformat(existing.departure_time)
            # Ensure timezone awareness matches
            if target_dep.tzinfo is not None and existing_dep.tzinfo is None:
                existing_dep = existing_dep.replace(tzinfo=target_dep.tzinfo)
            elif target_dep.tzinfo is None and existing_dep.tzinfo is not None:
                target_dep = target_dep.replace(tzinfo=existing_dep.tzinfo)

            minutes_diff = abs((target_dep - existing_dep).total_seconds()) / 60.0
            if minutes_diff < turnaround_minutes:
                raise GateConflictError(
                    f"Gate conflict: Flight {existing.flight_number} is scheduled at "
                    f"Gate {gate.gate_number} at {existing.departure_time}. "
                    f"A minimum of {turnaround_minutes}m turnaround buffer is required."
                )

        self.repo.assign_gate(flight_id, gate_id)

    # --- Validated Flight Status State Machine ---

    def update_flight_status(self, flight_id: int, target_status: str) -> None:
        flight = self.get_flight(flight_id)
        target_clean = target_status.strip().upper()

        if target_clean not in FlightStatus.__members__:
            raise InvalidFlightStatusTransitionError(f"Unknown flight status: '{target_status}'.")

        allowed = ALLOWED_TRANSITIONS.get(flight.status, set())
        if target_clean not in allowed:
            next_states = sorted(list(allowed)) or "None (Terminal state)"
            raise InvalidFlightStatusTransitionError(
                f"Cannot transition flight {flight.flight_number} from '{flight.status}' "
                f"to '{target_clean}'. Allowed next states: {next_states}."
            )

        self.repo.update_flight_status(flight_id, target_clean)

    # --- Passenger Check-In & Seat Assignment ---

    def register_passenger(self, full_name: str, passport_number: str, flight_id: int) -> Passenger:
        self.get_flight(flight_id)
        passenger = Passenger(
            full_name=full_name.strip(),
            passport_number=passport_number.strip().upper(),
            flight_id=flight_id,
        )
        return self.repo.add_passenger(passenger)

    def check_in(self, passenger_id: int, seat_number: str) -> None:
        passenger = self.repo.get_passenger(passenger_id)
        if not passenger:
            raise PassengerNotFoundError(f"Passenger ID {passenger_id} not found.")

        if passenger.checked_in:
            raise AirportError(f"Passenger '{passenger.full_name}' is already checked in.")

        flight = self.get_flight(passenger.flight_id)
        if flight.status in (FlightStatus.DEPARTED, FlightStatus.CANCELLED):
            raise CheckInNotAllowedError(
                f"Cannot check in: Flight {flight.flight_number} is {flight.status}."
            )

        seat_clean = seat_number.strip().upper()
        occupied = self.repo.get_occupied_seats(flight.id or 0)
        if seat_clean in occupied:
            raise SeatAlreadyAssignedError(
                f"Seat {seat_clean} is already assigned on flight {flight.flight_number}."
            )

        self.repo.check_in_passenger(passenger_id, seat_clean)

    # --- Flight Schedule Board ---

    def get_departure_board(self) -> list[BoardEntry]:
        return self.repo.list_board_entries()
