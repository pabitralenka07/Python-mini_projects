"""Service layer for Contact Management System with validation and safe CSV export."""

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from projects.p01_contact_management.models import Contact
from projects.p01_contact_management.repository import ContactRepository

FORMULA_PREFIXES = ("=", "+", "-", "@")


class ContactError(Exception):
    """Base exception for contact service operations."""

    pass


class ContactNotFoundError(ContactError):
    """Raised when contact cannot be found by ID."""

    pass


class DuplicateContactError(ContactError):
    """Raised when phone number or email already exists."""

    pass


class ValidationError(ContactError):
    """Raised when field validation fails."""

    pass


def sanitize_csv_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection by prepending a quote.

    Checks if value starts with =, +, -, or @.
    """
    stripped = value.strip()
    if stripped.startswith(FORMULA_PREFIXES):
        return f"'{stripped}"
    return stripped


class ContactService:
    """Domain logic for contact lifecycle, search, and safe CSV data handling."""

    def __init__(self, repository: ContactRepository) -> None:
        self.repo = repository

    def validate_contact_data(
        self, name: str, phone: str, email: str, exclude_id: int | None = None
    ) -> tuple[str, str, str]:
        name_clean = name.strip()
        phone_clean = phone.strip()
        email_clean = email.strip().lower()

        if not name_clean:
            raise ValidationError("Name cannot be empty.")

        # Phone validation: digits, optional leading +, dashes, spaces, parentheses
        digits_only = re.sub(r"\D", "", phone_clean)
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise ValidationError(f"Phone '{phone_clean}' must contain between 7 and 15 digits.")

        # Email validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
            raise ValidationError(f"Email '{email_clean}' is not a valid email address.")

        # Duplicate phone check
        existing_phone = self.repo.get_contact_by_phone(phone_clean)
        if existing_phone and existing_phone.id != exclude_id:
            raise DuplicateContactError(
                f"A contact with phone '{phone_clean}' already exists ({existing_phone.name})."
            )

        # Duplicate email check
        existing_email = self.repo.get_contact_by_email(email_clean)
        if existing_email and existing_email.id != exclude_id:
            raise DuplicateContactError(
                f"A contact with email '{email_clean}' already exists ({existing_email.name})."
            )

        return name_clean, phone_clean, email_clean

    def add_contact(self, name: str, phone: str, email: str, address: str = "") -> Contact:
        name_clean, phone_clean, email_clean = self.validate_contact_data(name, phone, email)
        created_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        contact = Contact(
            name=name_clean,
            phone=phone_clean,
            email=email_clean,
            address=address.strip(),
            created_at=created_at,
        )
        return self.repo.add_contact(contact)

    def edit_contact(
        self, contact_id: int, name: str, phone: str, email: str, address: str = ""
    ) -> Contact:
        existing = self.repo.get_contact_by_id(contact_id)
        if not existing:
            raise ContactNotFoundError(f"Contact ID {contact_id} not found.")

        name_clean, phone_clean, email_clean = self.validate_contact_data(
            name, phone, email, exclude_id=contact_id
        )

        updated = Contact(
            id=contact_id,
            name=name_clean,
            phone=phone_clean,
            email=email_clean,
            address=address.strip(),
            created_at=existing.created_at,
        )
        self.repo.update_contact(updated)
        return updated

    def delete_contact(self, contact_id: int) -> None:
        existing = self.repo.get_contact_by_id(contact_id)
        if not existing:
            raise ContactNotFoundError(f"Contact ID {contact_id} not found.")
        self.repo.delete_contact(contact_id)

    def search_contacts(self, query: str) -> list[Contact]:
        return self.repo.search_contacts(query)

    def list_contacts(self) -> list[Contact]:
        return self.repo.list_contacts()

    def export_csv(self, file_path: Path | str) -> int:
        """Export all contacts to CSV with formula injection neutralization."""
        contacts = self.repo.list_contacts()
        dest = Path(file_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Phone", "Email", "Address", "Created_At"])
            for c in contacts:
                writer.writerow(
                    [
                        c.id,
                        sanitize_csv_cell(c.name),
                        sanitize_csv_cell(c.phone),
                        sanitize_csv_cell(c.email),
                        sanitize_csv_cell(c.address),
                        c.created_at,
                    ]
                )
        return len(contacts)

    def import_csv(self, file_path: Path | str) -> tuple[int, int, list[str]]:
        """Import contacts from CSV, skipping rows with errors or duplicates.

        Returns:
            (imported_count, skipped_count, list_of_error_reasons)
        """
        source = Path(file_path)
        if not source.exists():
            raise ValidationError(f"CSV file '{file_path}' does not exist.")

        imported = 0
        skipped = 0
        errors: list[str] = []

        with open(source, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]
            if not {"name", "phone", "email"}.issubset(set(headers)):
                raise ValidationError("CSV must contain columns: 'name', 'phone', and 'email'.")

            for row_num, row in enumerate(reader, start=2):
                name = row.get("name", "") or row.get("Name", "")
                phone = row.get("phone", "") or row.get("Phone", "")
                email = row.get("email", "") or row.get("Email", "")
                address = row.get("address", "") or row.get("Address", "")

                try:
                    self.add_contact(name=name, phone=phone, email=email, address=address)
                    imported += 1
                except (ValidationError, DuplicateContactError) as err:
                    skipped += 1
                    errors.append(f"Row {row_num}: {err}")

        return imported, skipped, errors
