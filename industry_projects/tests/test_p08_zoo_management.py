"""Tests for Project 08: Zoo Management System."""

from unittest.mock import patch

import pytest

from common.clock import FrozenClock
from projects.p08_zoo_management.cli import run_cli
from projects.p08_zoo_management.models import TicketType
from projects.p08_zoo_management.repository import ZooRepository
from projects.p08_zoo_management.service import (
    EnclosureCapacityExceededError,
    ZooService,
)


@pytest.fixture
def zoo_setup() -> tuple[ZooRepository, ZooService, FrozenClock]:
    clock = FrozenClock("2026-11-25T10:00:00")
    repo = ZooRepository.in_memory()
    service = ZooService(repo, clock=clock)
    return repo, service, clock


def test_enclosure_creation_and_capacity_tracking(
    zoo_setup: tuple[ZooRepository, ZooService, FrozenClock],
) -> None:
    _, service, _ = zoo_setup
    enc = service.create_enclosure("Reptile House", "REPTILE", 2)
    assert enc.id is not None

    enclosures = service.list_enclosures()
    assert len(enclosures) == 1
    assert enclosures[0].name == "Reptile House"
    assert enclosures[0].max_capacity == 2
    assert enclosures[0].current_animals == 0
    assert enclosures[0].available_capacity == 2


def test_enclosure_capacity_enforcement(
    zoo_setup: tuple[ZooRepository, ZooService, FrozenClock],
) -> None:
    _, service, _ = zoo_setup
    # Create enclosure with max capacity 2
    enc = service.create_enclosure("Small Aviary", "AVIARY", 2)
    assert enc.id is not None

    # Add 1st animal
    a1 = service.add_animal("Tweety", "Canary", 1, "HERBIVORE", enc.id, "08:00")
    assert a1.id is not None

    # Add 2nd animal (reaches max capacity 2)
    a2 = service.add_animal("Iago", "Parrot", 3, "HERBIVORE", enc.id, "08:30")
    assert a2.id is not None

    # Attempting to add 3rd animal must fail with EnclosureCapacityExceededError
    with pytest.raises(EnclosureCapacityExceededError, match="maximum capacity"):
        service.add_animal("Hedwig", "Snowy Owl", 2, "CARNIVORE", enc.id, "19:00")


def test_feeding_schedule_retrieval(
    zoo_setup: tuple[ZooRepository, ZooService, FrozenClock],
) -> None:
    _, service, _ = zoo_setup
    enc = service.create_enclosure("Savannah", "SAVANNAH", 5)
    assert enc.id is not None

    service.add_animal("Zebra", "Plains Zebra", 4, "HERBIVORE", enc.id, "09:00")
    service.add_animal("Lion", "African Lion", 6, "CARNIVORE", enc.id, "12:00")

    schedule = service.get_feeding_schedule()
    assert len(schedule) == 2
    # Should be sorted chronologically by feeding time
    assert schedule[0].animal_name == "Zebra"
    assert schedule[0].feeding_time == "09:00"
    assert schedule[1].animal_name == "Lion"
    assert schedule[1].feeding_time == "12:00"


def test_keeper_registration_and_enclosure_assignment(
    zoo_setup: tuple[ZooRepository, ZooService, FrozenClock],
) -> None:
    _, service, _ = zoo_setup
    enc = service.create_enclosure("Primate Kingdom", "SAVANNAH", 10)
    assert enc.id is not None

    keeper = service.register_keeper("Dr. Jane", "EMP-900", enc.id)
    assert keeper.id is not None
    assert keeper.assigned_enclosure_id == enc.id

    keepers = service.list_keepers()
    assert len(keepers) == 1
    assert keepers[0].name == "Dr. Jane"


def test_ticket_sales_and_daily_revenue_calculation(
    zoo_setup: tuple[ZooRepository, ZooService, FrozenClock],
) -> None:
    _, service, _ = zoo_setup
    # ADULT: 2000 cents ($20), CHILD: 1000 cents ($10), SENIOR: 1500 cents ($15)
    # Sell 2 adults ($40.00 / 4000c)
    s1 = service.sell_tickets(TicketType.ADULT, 2)
    assert s1.total_cents == 4000

    # Sell 3 children ($30.00 / 3000c)
    s2 = service.sell_tickets(TicketType.CHILD, 3)
    assert s2.total_cents == 3000

    # Sell 1 senior ($15.00 / 1500c)
    s3 = service.sell_tickets(TicketType.SENIOR, 1)
    assert s3.total_cents == 1500

    report = service.get_daily_revenue_report("2026-11-25")
    assert report.adult_tickets == 2
    assert report.child_tickets == 3
    assert report.senior_tickets == 1
    assert report.total_tickets == 6
    assert report.total_revenue_cents == 8500  # $85.00


def test_cli_handles_eof_gracefully(
    zoo_setup: tuple[ZooRepository, ZooService, FrozenClock],
) -> None:
    _, service, _ = zoo_setup
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)
