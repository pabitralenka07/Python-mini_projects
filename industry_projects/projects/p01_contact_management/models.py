"""Data models for Contact Management System."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Contact:
    """Represents an address book contact entry."""

    name: str
    phone: str
    email: str
    address: str = ""
    created_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Contact name cannot be empty.")
        if not self.phone.strip():
            raise ValueError("Phone number cannot be empty.")
        if not self.email.strip():
            raise ValueError("Email cannot be empty.")
