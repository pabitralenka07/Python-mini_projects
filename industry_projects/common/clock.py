"""Injectable clock abstraction for deterministic testing and due-date calculations."""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Protocol defining the clock interface."""

    def now(self) -> datetime:
        """Return current datetime."""
        ...

    def today_iso(self) -> str:
        """Return current date formatted as YYYY-MM-DD."""
        ...

    def now_iso(self) -> str:
        """Return current datetime formatted as ISO-8601 string."""
        ...


class SystemClock:
    """Standard system clock using system UTC time."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today_iso(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def now_iso(self) -> str:
        return self.now().isoformat()


class FrozenClock:
    """Controllable clock for unit testing and deterministic simulation."""

    def __init__(self, current_time: datetime | str | None = None) -> None:
        if current_time is None:
            self._current: datetime = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        elif isinstance(current_time, str):
            dt = datetime.fromisoformat(current_time)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            self._current = dt
        else:
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=UTC)
            self._current = current_time

    def now(self) -> datetime:
        return self._current

    def today_iso(self) -> str:
        return self._current.strftime("%Y-%m-%d")

    def now_iso(self) -> str:
        return self._current.isoformat()

    def set_time(self, new_time: datetime | str) -> None:
        if isinstance(new_time, str):
            dt = datetime.fromisoformat(new_time)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            self._current = dt
        else:
            if new_time.tzinfo is None:
                new_time = new_time.replace(tzinfo=UTC)
            self._current = new_time

    def advance(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> None:
        """Advance the frozen clock by specified duration."""
        self._current += timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
