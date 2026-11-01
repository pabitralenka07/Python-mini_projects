"""Tests for Project 09: Electricity Bill Management System."""

from unittest.mock import patch

import pytest

from common.clock import FrozenClock
from projects.p09_electricity_bill.cli import run_cli
from projects.p09_electricity_bill.gui_app import ElectricityBillApp
from projects.p09_electricity_bill.repository import ElectricityRepository
from projects.p09_electricity_bill.service import (
    BillAlreadyPaidError,
    ElectricityService,
    NonMonotonicReadingError,
)


@pytest.fixture
def electricity_setup() -> tuple[ElectricityRepository, ElectricityService, FrozenClock]:
    clock = FrozenClock("2026-11-01T10:00:00")
    repo = ElectricityRepository.in_memory()
    service = ElectricityService(repo, clock=clock)
    return repo, service, clock


def test_consumer_registration_and_initial_reading(
    electricity_setup: tuple[ElectricityRepository, ElectricityService, FrozenClock],
) -> None:
    _, service, _ = electricity_setup
    consumer = service.register_consumer(
        consumer_number="CON-001",
        name="Diana Prince",
        address="10 Gateway Blvd",
        meter_number="MTR-100",
        tariff_category="RESIDENTIAL",
        initial_reading=50,
    )
    assert consumer.id is not None

    latest_reading = service.repo.get_latest_meter_reading(consumer.id)
    assert latest_reading is not None
    assert latest_reading.reading_value == 50


def test_slab_tariff_calculation_tiers(
    electricity_setup: tuple[ElectricityRepository, ElectricityService, FrozenClock],
) -> None:
    _, service, _ = electricity_setup
    # 250 units residential:
    # 100 units @ 10c = 1000 cents
    # 150 units @ 15c = 2250 cents
    # Total energy charge = 3250 cents ($32.50)
    energy_cents, breakdown = service.calculate_energy_charge(250, "RESIDENTIAL")
    assert energy_cents == 3250
    assert len(breakdown) == 2
    assert breakdown[0].units_in_slab == 100
    assert breakdown[0].amount_cents == 1000
    assert breakdown[1].units_in_slab == 150
    assert breakdown[1].amount_cents == 2250

    # 600 units residential:
    # 100 @ 10c = 1000c
    # 200 @ 15c = 3000c
    # 200 @ 20c = 4000c
    # 100 @ 30c = 3000c
    # Total = 11000 cents ($110.00)
    energy_600, _ = service.calculate_energy_charge(600, "RESIDENTIAL")
    assert energy_600 == 11000


def test_monotonic_reading_enforcement(
    electricity_setup: tuple[ElectricityRepository, ElectricityService, FrozenClock],
) -> None:
    _, service, _ = electricity_setup
    consumer = service.register_consumer(
        consumer_number="CON-002",
        name="Bruce Wayne",
        address="1007 Mountain Drive",
        meter_number="MTR-200",
        initial_reading=500,
    )
    assert consumer.id is not None

    # Submitting current reading of 450 kWh (< 500 kWh baseline) must fail
    with pytest.raises(NonMonotonicReadingError, match="cannot be less than previous reading"):
        service.generate_bill(consumer.id, current_reading=450)

    # Submitting current reading of 750 kWh (>= 500 kWh) succeeds
    bill = service.generate_bill(consumer.id, current_reading=750)
    assert bill.units_consumed == 250
    assert bill.status == "UNPAID"


def test_bill_settlement_and_duplicate_payment_guard(
    electricity_setup: tuple[ElectricityRepository, ElectricityService, FrozenClock],
) -> None:
    _, service, _ = electricity_setup
    consumer = service.register_consumer(
        consumer_number="CON-003",
        name="Barry Allen",
        address="55 Central City Way",
        meter_number="MTR-300",
        initial_reading=100,
    )
    assert consumer.id is not None

    bill = service.generate_bill(consumer.id, current_reading=300)
    assert bill.id is not None
    assert bill.status == "UNPAID"

    # Settle bill
    service.pay_bill(bill.id)
    updated_bill = service.repo.get_bill(bill.id)
    assert updated_bill is not None
    assert updated_bill.status == "PAID"
    assert updated_bill.paid_at is not None

    # Duplicate settlement attempt fails
    with pytest.raises(BillAlreadyPaidError, match="is already paid"):
        service.pay_bill(bill.id)


def test_cli_handles_eof_gracefully(
    electricity_setup: tuple[ElectricityRepository, ElectricityService, FrozenClock],
) -> None:
    _, service, _ = electricity_setup
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)


def test_gui_headless_initialization(
    electricity_setup: tuple[ElectricityRepository, ElectricityService, FrozenClock],
) -> None:
    _, service, _ = electricity_setup
    # Headless-safe Tkinter test
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        app = ElectricityBillApp(root, service=service)
        assert app is not None
        assert app.notebook.index("end") == 3
        root.destroy()
    except tk.TclError:
        # Pass gracefully on headless Linux systems without X display
        pytest.skip("Tkinter display not available in headless test environment")
