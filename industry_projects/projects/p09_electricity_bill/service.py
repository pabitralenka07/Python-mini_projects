"""Service layer for Electricity Bill Management System with slab tariffs
and monotonic reading checks.
"""

from datetime import datetime, timedelta

from common.clock import Clock, SystemClock
from projects.p09_electricity_bill.models import (
    BillDetail,
    Consumer,
    ElectricityBill,
    MeterReading,
    SlabBreakdown,
    TariffSlab,
)
from projects.p09_electricity_bill.repository import ElectricityRepository


class ElectricityError(Exception):
    """Base exception for electricity utility errors."""

    pass


class ConsumerNotFoundError(ElectricityError):
    """Raised when consumer cannot be found."""

    pass


class NonMonotonicReadingError(ElectricityError):
    """Raised when current meter reading is less than previous reading."""

    pass


class BillNotFoundError(ElectricityError):
    """Raised when bill cannot be found."""

    pass


class BillAlreadyPaidError(ElectricityError):
    """Raised when attempting to pay an already settled bill."""

    pass


RESIDENTIAL_SLABS: list[TariffSlab] = [
    TariffSlab(min_units=0, max_units=100, rate_per_unit_cents=10),
    TariffSlab(min_units=100, max_units=300, rate_per_unit_cents=15),
    TariffSlab(min_units=300, max_units=500, rate_per_unit_cents=20),
    TariffSlab(min_units=500, max_units=None, rate_per_unit_cents=30),
]

COMMERCIAL_SLABS: list[TariffSlab] = [
    TariffSlab(min_units=0, max_units=200, rate_per_unit_cents=20),
    TariffSlab(min_units=200, max_units=None, rate_per_unit_cents=35),
]

FIXED_CHARGES_CENTS: dict[str, int] = {
    "RESIDENTIAL": 500,
    "COMMERCIAL": 1500,
}

TAX_RATE: float = 0.05


class ElectricityService:
    """Coordinates customer onboarding, meter reading verification, and slab bill generation."""

    def __init__(self, repository: ElectricityRepository, clock: Clock | None = None) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()


    def register_consumer(
        self,
        consumer_number: str,
        name: str,
        address: str,
        meter_number: str,
        tariff_category: str = "RESIDENTIAL",
        initial_reading: int = 0,
    ) -> Consumer:
        cat = tariff_category.strip().upper()
        if cat not in ("RESIDENTIAL", "COMMERCIAL"):
            raise ElectricityError(f"Invalid tariff category '{tariff_category}'.")

        consumer = Consumer(
            consumer_number=consumer_number.strip().upper(),
            name=name.strip(),
            address=address.strip(),
            meter_number=meter_number.strip().upper(),
            tariff_category=cat,
        )
        saved = self.repo.add_consumer(consumer)

        if saved.id is not None:
            self.repo.add_meter_reading(
                MeterReading(
                    consumer_id=saved.id,
                    reading_date=self.clock.today_iso(),
                    reading_value=initial_reading,
                )
            )

        return saved

    def get_consumer(self, consumer_id: int) -> Consumer:
        c = self.repo.get_consumer(consumer_id)
        if not c:
            raise ConsumerNotFoundError(f"Consumer ID {consumer_id} not found.")
        return c

    def get_consumer_by_number(self, consumer_number: str) -> Consumer:
        c = self.repo.get_consumer_by_number(consumer_number.strip().upper())
        if not c:
            raise ConsumerNotFoundError(f"Consumer '{consumer_number}' not found.")
        return c

    def list_consumers(self) -> list[Consumer]:
        return self.repo.list_consumers()


    def calculate_energy_charge(
        self, units: int, tariff_category: str
    ) -> tuple[int, list[SlabBreakdown]]:
        """Calculates energy charge across tiered slabs in minor-unit cents."""
        slabs = COMMERCIAL_SLABS if tariff_category == "COMMERCIAL" else RESIDENTIAL_SLABS
        breakdown: list[SlabBreakdown] = []
        total_energy_cents = 0

        for slab in slabs:
            if units <= slab.min_units:
                continue

            if slab.max_units is not None:
                units_in_slab = min(units, slab.max_units) - slab.min_units
                label = f"{slab.min_units} - {slab.max_units} kWh"
            else:
                units_in_slab = units - slab.min_units
                label = f"> {slab.min_units} kWh"

            amt_cents = units_in_slab * slab.rate_per_unit_cents
            total_energy_cents += amt_cents

            breakdown.append(
                SlabBreakdown(
                    slab_label=label,
                    units_in_slab=units_in_slab,
                    rate_per_unit_cents=slab.rate_per_unit_cents,
                    amount_cents=amt_cents,
                )
            )

        return total_energy_cents, breakdown


    def generate_bill(
        self, consumer_id: int, current_reading: int, reading_date: str | None = None
    ) -> ElectricityBill:
        consumer = self.get_consumer(consumer_id)

        latest = self.repo.get_latest_meter_reading(consumer_id)
        previous_reading = latest.reading_value if latest else 0

        if current_reading < previous_reading:
            raise NonMonotonicReadingError(
                f"Current meter reading ({current_reading} kWh) cannot be less than "
                f"previous reading ({previous_reading} kWh)."
            )

        date_str = reading_date.strip() if reading_date else self.clock.today_iso()
        self.repo.add_meter_reading(
            MeterReading(
                consumer_id=consumer_id,
                reading_date=date_str,
                reading_value=current_reading,
            )
        )

        units_consumed = current_reading - previous_reading
        energy_cents, _ = self.calculate_energy_charge(units_consumed, consumer.tariff_category)
        fixed_cents = FIXED_CHARGES_CENTS.get(consumer.tariff_category, 500)
        subtotal_cents = energy_cents + fixed_cents
        tax_cents = int(subtotal_cents * TAX_RATE)
        total_cents = subtotal_cents + tax_cents

        today_dt = datetime.fromisoformat(self.clock.today_iso())
        due_dt = today_dt + timedelta(days=15)
        due_date = due_dt.strftime("%Y-%m-%d")

        now_iso = self.clock.now_iso()
        timestamp_part = now_iso.replace("-", "").replace(":", "").replace("T", "")[:12]
        bill_number = f"BILL-{consumer.consumer_number}-{timestamp_part}"

        bill = ElectricityBill(
            consumer_id=consumer_id,
            bill_number=bill_number,
            previous_reading=previous_reading,
            current_reading=current_reading,
            units_consumed=units_consumed,
            energy_charge_cents=energy_cents,
            fixed_charge_cents=fixed_cents,
            tax_cents=tax_cents,
            total_cents=total_cents,
            due_date=due_date,
            status="UNPAID",
            issued_at=now_iso,
        )
        return self.repo.create_bill(bill)

    def pay_bill(self, bill_id: int) -> None:
        bill = self.repo.get_bill(bill_id)
        if not bill:
            raise BillNotFoundError(f"Bill ID {bill_id} not found.")

        if bill.status == "PAID":
            raise BillAlreadyPaidError(f"Bill '{bill.bill_number}' is already paid.")

        self.repo.mark_bill_paid(bill_id, self.clock.now_iso())

    def get_bill_detail(self, bill_id: int) -> BillDetail:
        bill = self.repo.get_bill(bill_id)
        if not bill:
            raise BillNotFoundError(f"Bill ID {bill_id} not found.")

        consumer = self.get_consumer(bill.consumer_id)
        _, slabs = self.calculate_energy_charge(bill.units_consumed, consumer.tariff_category)

        return BillDetail(
            bill_id=bill_id,
            bill_number=bill.bill_number,
            consumer_number=consumer.consumer_number,
            consumer_name=consumer.name,
            meter_number=consumer.meter_number,
            tariff_category=consumer.tariff_category,
            previous_reading=bill.previous_reading,
            current_reading=bill.current_reading,
            units_consumed=bill.units_consumed,
            energy_charge_cents=bill.energy_charge_cents,
            fixed_charge_cents=bill.fixed_charge_cents,
            tax_cents=bill.tax_cents,
            total_cents=bill.total_cents,
            due_date=bill.due_date,
            status=bill.status,
            issued_at=bill.issued_at,
            paid_at=bill.paid_at,
            slabs=slabs,
        )

    def list_all_bills(self) -> list[BillDetail]:
        return self.repo.list_all_bill_details()
