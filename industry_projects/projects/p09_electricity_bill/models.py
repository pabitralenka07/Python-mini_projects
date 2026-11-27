"""Data models for Electricity Bill Management System."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Consumer:
    """Represents an electricity customer."""

    consumer_number: str
    name: str
    address: str
    meter_number: str
    tariff_category: str = "RESIDENTIAL"
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.consumer_number.strip():
            raise ValueError("Consumer number cannot be empty.")
        if not self.name.strip():
            raise ValueError("Consumer name cannot be empty.")
        if not self.meter_number.strip():
            raise ValueError("Meter number cannot be empty.")


@dataclass(frozen=True)
class MeterReading:
    """Represents an officially recorded meter reading in kWh units."""

    consumer_id: int
    reading_date: str
    reading_value: int
    id: int | None = None

    def __post_init__(self) -> None:
        if self.consumer_id <= 0:
            raise ValueError("Invalid consumer ID.")
        if self.reading_value < 0:
            raise ValueError("Meter reading cannot be negative.")


@dataclass(frozen=True)
class TariffSlab:
    """Defines a tiered pricing slab in kWh units and minor-unit cents."""

    min_units: int
    max_units: int | None
    rate_per_unit_cents: int

    def __post_init__(self) -> None:
        if self.min_units < 0:
            raise ValueError("Minimum units cannot be negative.")
        if self.max_units is not None and self.max_units <= self.min_units:
            raise ValueError("Maximum units must exceed minimum units.")
        if self.rate_per_unit_cents < 0:
            raise ValueError("Rate per unit cannot be negative.")


@dataclass(frozen=True)
class SlabBreakdown:
    """Calculated breakdown item for an individual pricing tier."""

    slab_label: str
    units_in_slab: int
    rate_per_unit_cents: int
    amount_cents: int


@dataclass(frozen=True)
class ElectricityBill:
    """Itemized utility invoice generated from meter readings."""

    consumer_id: int
    bill_number: str
    previous_reading: int
    current_reading: int
    units_consumed: int
    energy_charge_cents: int
    fixed_charge_cents: int
    tax_cents: int
    total_cents: int
    due_date: str
    status: str = "UNPAID"
    issued_at: str = ""
    paid_at: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.units_consumed < 0:
            raise ValueError("Units consumed cannot be negative.")
        if self.total_cents < 0:
            raise ValueError("Total bill amount cannot be negative.")


@dataclass(frozen=True)
class BillDetail:
    """Composite projection of bill details with consumer identity information."""

    bill_id: int
    bill_number: str
    consumer_number: str
    consumer_name: str
    meter_number: str
    tariff_category: str
    previous_reading: int
    current_reading: int
    units_consumed: int
    energy_charge_cents: int
    fixed_charge_cents: int
    tax_cents: int
    total_cents: int
    due_date: str
    status: str
    issued_at: str
    paid_at: str | None
    slabs: list[SlabBreakdown] = field(default_factory=list)
