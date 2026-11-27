"""Data models for Bus Reservation System."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bus:
    """Represents a bus vehicle in the fleet."""

    bus_number: str
    bus_type: str
    total_seats: int
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.bus_number.strip():
            raise ValueError("Bus number cannot be empty.")
        if not self.bus_type.strip():
            raise ValueError("Bus type cannot be empty.")
        if self.total_seats <= 0:
            raise ValueError("Total seats must be greater than zero.")


@dataclass(frozen=True)
class Route:
    """Represents a travel route between origin and destination."""

    origin: str
    destination: str
    distance_km: float
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.origin.strip():
            raise ValueError("Origin cannot be empty.")
        if not self.destination.strip():
            raise ValueError("Destination cannot be empty.")
        if self.distance_km <= 0:
            raise ValueError("Distance must be greater than zero.")


@dataclass(frozen=True)
class Schedule:
    """Represents a scheduled bus trip with departure/arrival times and fare."""

    bus_id: int
    route_id: int
    departure_time: str
    arrival_time: str
    fare_cents: int
    id: int | None = None

    def __post_init__(self) -> None:
        if self.bus_id <= 0:
            raise ValueError("Invalid bus ID.")
        if self.route_id <= 0:
            raise ValueError("Invalid route ID.")
        if self.fare_cents < 0:
            raise ValueError("Fare cannot be negative.")


@dataclass(frozen=True)
class ScheduleDetail:
    """Composite view of a schedule with bus, route, and seat availability information."""

    schedule_id: int
    bus_number: str
    bus_type: str
    total_seats: int
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    fare_cents: int
    available_seats: int


@dataclass(frozen=True)
class Booking:
    """Represents a passenger's seat reservation on a scheduled trip."""

    schedule_id: int
    passenger_name: str
    passenger_phone: str
    seat_number: int
    fare_paid_cents: int
    status: str = "CONFIRMED"
    created_at: str = ""
    cancelled_at: str | None = None
    refund_cents: int = 0
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.passenger_name.strip():
            raise ValueError("Passenger name cannot be empty.")
        if not self.passenger_phone.strip():
            raise ValueError("Passenger phone cannot be empty.")
        if self.seat_number <= 0:
            raise ValueError("Seat number must be positive.")
        if self.fare_paid_cents < 0:
            raise ValueError("Fare paid cannot be negative.")


@dataclass(frozen=True)
class TicketReceipt:
    """Formatted ticket receipt for screen display or text file generation."""

    booking_id: int
    passenger_name: str
    passenger_phone: str
    bus_number: str
    bus_type: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    seat_number: int
    fare_paid_cents: int
    booking_time: str
