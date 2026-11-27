"""Data models for Airport Management System."""

from dataclasses import dataclass
from enum import StrEnum


class FlightStatus(StrEnum):
    """Lifecycle states of an airport commercial flight."""

    SCHEDULED = "SCHEDULED"
    BOARDING = "BOARDING"
    DEPARTED = "DEPARTED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Gate:
    """Represents an airport boarding gate."""

    gate_number: str
    terminal: str
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.gate_number.strip():
            raise ValueError("Gate number cannot be empty.")
        if not self.terminal.strip():
            raise ValueError("Terminal cannot be empty.")


@dataclass(frozen=True)
class Flight:
    """Represents a scheduled commercial flight."""

    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    gate_id: int | None = None
    status: str = FlightStatus.SCHEDULED
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.flight_number.strip():
            raise ValueError("Flight number cannot be empty.")
        if not self.airline.strip():
            raise ValueError("Airline cannot be empty.")
        if not self.origin.strip():
            raise ValueError("Origin cannot be empty.")
        if not self.destination.strip():
            raise ValueError("Destination cannot be empty.")


@dataclass(frozen=True)
class Passenger:
    """Represents a ticketed passenger on a flight."""

    full_name: str
    passport_number: str
    flight_id: int
    seat_number: str | None = None
    checked_in: bool = False
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.full_name.strip():
            raise ValueError("Full name cannot be empty.")
        if not self.passport_number.strip():
            raise ValueError("Passport number cannot be empty.")
        if self.flight_id <= 0:
            raise ValueError("Invalid flight ID.")


@dataclass(frozen=True)
class BoardEntry:
    """Composite display record for airport schedule display board."""

    flight_id: int
    flight_number: str
    airline: str
    destination: str
    departure_time: str
    gate: str
    status: str
