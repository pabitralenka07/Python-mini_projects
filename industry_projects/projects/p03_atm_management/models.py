"""Data models for ATM Management System."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ATMCard:
    """Represents a physical ATM debit card linked to a bank account."""

    card_number: str
    account_number: str
    pin_hash: bytes
    salt: bytes
    failed_attempts: int = 0
    locked_until: str | None = None
    status: str = "ACTIVE"  # ACTIVE, BLOCKED


@dataclass(frozen=True)
class CashDispenseResult:
    """Represents physical banknote breakdown dispensed by the ATM."""

    total_cents: int
    notes_100: int = 0
    notes_50: int = 0
    notes_20: int = 0
    notes_10: int = 0

    def summary(self) -> str:
        parts: list[str] = []
        if self.notes_100:
            parts.append(f"{self.notes_100} x $100")
        if self.notes_50:
            parts.append(f"{self.notes_50} x $50")
        if self.notes_20:
            parts.append(f"{self.notes_20} x $20")
        if self.notes_10:
            parts.append(f"{self.notes_10} x $10")
        return ", ".join(parts) if parts else "No notes dispensed"
