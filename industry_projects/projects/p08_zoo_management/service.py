"""Service layer for Zoo Management System with enclosure capacity checks and ticket admissions."""

from common.clock import Clock, SystemClock
from projects.p08_zoo_management.models import (
    TICKET_PRICING_CENTS,
    Animal,
    DailyRevenueReport,
    Enclosure,
    EnclosureDetail,
    FeedingScheduleEntry,
    Keeper,
    TicketSale,
)
from projects.p08_zoo_management.repository import ZooRepository


class ZooError(Exception):
    """Base exception for zoo management operations."""

    pass


class EnclosureNotFoundError(ZooError):
    """Raised when an enclosure ID or name is not found."""

    pass


class EnclosureCapacityExceededError(ZooError):
    """Raised when attempting to add an animal to an enclosure at maximum capacity."""

    pass


class AnimalNotFoundError(ZooError):
    """Raised when an animal is not found."""

    pass


class KeeperNotFoundError(ZooError):
    """Raised when a staff keeper is not found."""

    pass


class InvalidTicketSaleError(ZooError):
    """Raised when ticket purchase parameters are invalid."""

    pass


class ZooService:
    """Coordinates animal habitats, staffing, feeding schedules, and admission ticketing."""

    def __init__(self, repository: ZooRepository, clock: Clock | None = None) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()

    # --- Enclosures ---

    def create_enclosure(self, name: str, habitat_type: str, max_capacity: int) -> Enclosure:
        if max_capacity <= 0:
            raise ZooError("Enclosure capacity must be greater than zero.")

        enc = Enclosure(
            name=name.strip(),
            habitat_type=habitat_type.strip().upper(),
            max_capacity=max_capacity,
        )
        return self.repo.add_enclosure(enc)

    def list_enclosures(self) -> list[EnclosureDetail]:
        return self.repo.list_enclosure_details()

    # --- Animals & Capacity Invariant ---

    def add_animal(
        self,
        name: str,
        species: str,
        age_years: int,
        dietary_category: str,
        enclosure_id: int,
        feeding_time: str,
    ) -> Animal:
        enclosure = self.repo.get_enclosure(enclosure_id)
        if not enclosure:
            raise EnclosureNotFoundError(f"Enclosure ID {enclosure_id} not found.")

        # Check strict capacity invariant
        current_count = self.repo.count_animals_in_enclosure(enclosure_id)
        if current_count >= enclosure.max_capacity:
            raise EnclosureCapacityExceededError(
                f"Cannot add animal '{name}': Enclosure '{enclosure.name}' has reached "
                f"its maximum capacity of {enclosure.max_capacity} animal(s)."
            )

        diet_clean = dietary_category.strip().upper()
        if diet_clean not in ("CARNIVORE", "HERBIVORE", "OMNIVORE"):
            raise ZooError(
                f"Invalid dietary category '{dietary_category}'. "
                "Must be CARNIVORE, HERBIVORE, or OMNIVORE."
            )

        animal = Animal(
            name=name.strip(),
            species=species.strip(),
            age_years=age_years,
            dietary_category=diet_clean,
            enclosure_id=enclosure_id,
            feeding_time=feeding_time.strip(),
        )
        return self.repo.add_animal(animal)

    def get_feeding_schedule(self) -> list[FeedingScheduleEntry]:
        return self.repo.list_feeding_schedule()

    # --- Staff Keepers ---

    def register_keeper(
        self, name: str, employee_id: str, assigned_enclosure_id: int | None = None
    ) -> Keeper:
        if assigned_enclosure_id is not None:
            enc = self.repo.get_enclosure(assigned_enclosure_id)
            if not enc:
                raise EnclosureNotFoundError(f"Enclosure ID {assigned_enclosure_id} not found.")

        keeper = Keeper(
            name=name.strip(),
            employee_id=employee_id.strip().upper(),
            assigned_enclosure_id=assigned_enclosure_id,
        )
        return self.repo.add_keeper(keeper)

    def list_keepers(self) -> list[Keeper]:
        return self.repo.list_keepers()

    def assign_keeper_to_enclosure(self, keeper_id: int, enclosure_id: int) -> None:
        enc = self.repo.get_enclosure(enclosure_id)
        if not enc:
            raise EnclosureNotFoundError(f"Enclosure ID {enclosure_id} not found.")
        self.repo.assign_keeper_enclosure(keeper_id, enclosure_id)

    # --- Ticket Sales & Daily Revenue Reports ---

    def sell_tickets(self, ticket_type: str, quantity: int) -> TicketSale:
        tt_clean = ticket_type.strip().upper()
        if tt_clean not in TICKET_PRICING_CENTS:
            valid_types = list(TICKET_PRICING_CENTS.keys())
            raise InvalidTicketSaleError(
                f"Invalid ticket type '{ticket_type}'. Valid types: {valid_types}."
            )

        if quantity <= 0:
            raise InvalidTicketSaleError("Ticket quantity must be at least 1.")

        unit_price_cents = TICKET_PRICING_CENTS[tt_clean]
        total_cents = unit_price_cents * quantity
        sold_at = self.clock.now_iso()

        sale = TicketSale(
            ticket_type=tt_clean,
            quantity=quantity,
            unit_price_cents=unit_price_cents,
            total_cents=total_cents,
            sold_at=sold_at,
        )
        return self.repo.record_ticket_sale(sale)

    def get_daily_revenue_report(self, date_str: str | None = None) -> DailyRevenueReport:
        target_date = date_str.strip() if date_str else self.clock.today_iso()
        return self.repo.get_daily_revenue_report(target_date)
