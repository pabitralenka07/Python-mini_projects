"""Data models for Zoo Management System."""

from dataclasses import dataclass
from enum import StrEnum


class TicketType(StrEnum):
    """Admission ticket categories."""

    ADULT = "ADULT"
    CHILD = "CHILD"
    SENIOR = "SENIOR"


# Pinned minor-unit prices for zoo admission tickets
TICKET_PRICING_CENTS: dict[str, int] = {
    TicketType.ADULT: 2000,  # $20.00
    TicketType.CHILD: 1000,  # $10.00
    TicketType.SENIOR: 1500,  # $15.00
}


@dataclass(frozen=True)
class Enclosure:
    """Represents an animal habitat enclosure with a strict maximum capacity."""

    name: str
    habitat_type: str  # SAVANNAH, AVIARY, ARCTIC, REPTILE, AQUARIUM
    max_capacity: int
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Enclosure name cannot be empty.")
        if not self.habitat_type.strip():
            raise ValueError("Habitat type cannot be empty.")
        if self.max_capacity <= 0:
            raise ValueError("Enclosure capacity must be greater than zero.")


@dataclass(frozen=True)
class EnclosureDetail:
    """Composite projection showing enclosure occupancy against maximum capacity."""

    enclosure_id: int
    name: str
    habitat_type: str
    max_capacity: int
    current_animals: int
    available_capacity: int


@dataclass(frozen=True)
class Animal:
    """Represents an individual animal resident in the zoo."""

    name: str
    species: str
    age_years: int
    dietary_category: str  # CARNIVORE, HERBIVORE, OMNIVORE
    enclosure_id: int
    feeding_time: str  # e.g. "09:30" or "15:00"
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Animal name cannot be empty.")
        if not self.species.strip():
            raise ValueError("Animal species cannot be empty.")
        if self.age_years < 0:
            raise ValueError("Animal age cannot be negative.")
        if self.enclosure_id <= 0:
            raise ValueError("Invalid enclosure ID.")


@dataclass(frozen=True)
class FeedingScheduleEntry:
    """Composite record for zoo keepers' daily animal feeding timetable."""

    animal_id: int
    animal_name: str
    species: str
    enclosure_name: str
    dietary_category: str
    feeding_time: str


@dataclass(frozen=True)
class Keeper:
    """Represents a staff zoo keeper caring for an enclosure."""

    name: str
    employee_id: str
    assigned_enclosure_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Keeper name cannot be empty.")
        if not self.employee_id.strip():
            raise ValueError("Employee ID cannot be empty.")


@dataclass(frozen=True)
class TicketSale:
    """Represents an admission ticket transaction."""

    ticket_type: str
    quantity: int
    unit_price_cents: int
    total_cents: int
    sold_at: str  # ISO 8601: YYYY-MM-DDTHH:MM:SS
    id: int | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if self.unit_price_cents < 0:
            raise ValueError("Unit price cannot be negative.")
        if self.total_cents < 0:
            raise ValueError("Total cents cannot be negative.")


@dataclass(frozen=True)
class DailyRevenueReport:
    """Summary of tickets sold and revenue collected for a calendar date."""

    sale_date: str
    adult_tickets: int
    child_tickets: int
    senior_tickets: int
    total_tickets: int
    total_revenue_cents: int
