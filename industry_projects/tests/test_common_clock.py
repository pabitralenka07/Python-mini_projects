"""Tests for common.clock module."""

from datetime import datetime

from common.clock import FrozenClock, SystemClock


def test_system_clock_produces_valid_timestamps() -> None:
    clock = SystemClock()
    now = clock.now()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert len(clock.today_iso()) == 10
    assert "T" in clock.now_iso()


def test_frozen_clock_deterministic_advancement() -> None:
    clock = FrozenClock("2026-05-10T10:00:00+00:00")
    assert clock.today_iso() == "2026-05-10"

    clock.advance(days=5, hours=2)
    assert clock.today_iso() == "2026-05-15"
    assert clock.now().hour == 12

    clock.set_time("2026-12-31T23:59:59+00:00")
    assert clock.today_iso() == "2026-12-31"
