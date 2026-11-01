"""Repository layer for Contact Management System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p01_contact_management.models import Contact

CONTACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    phone TEXT NOT NULL UNIQUE CHECK(length(phone) >= 7),
    email TEXT NOT NULL UNIQUE CHECK(email LIKE '%_@_%._%'),
    address TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
"""


class ContactRepository:
    """Encapsulates SQLite persistence for contacts."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "ContactRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=CONTACTS_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    def add_contact(self, contact: Contact) -> Contact:
        query = """
            INSERT INTO contacts (name, phone, email, address, created_at)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    contact.name,
                    contact.phone,
                    contact.email,
                    contact.address,
                    contact.created_at,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for contact.")
            contact_id = int(cursor.lastrowid)

        return Contact(
            id=contact_id,
            name=contact.name,
            phone=contact.phone,
            email=contact.email,
            address=contact.address,
            created_at=contact.created_at,
        )

    def update_contact(self, contact: Contact) -> None:
        if contact.id is None:
            raise ValueError("Contact ID required for update.")
        query = """
            UPDATE contacts
            SET name = ?, phone = ?, email = ?, address = ?
            WHERE id = ?;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(
                query,
                (contact.name, contact.phone, contact.email, contact.address, contact.id),
            )

    def delete_contact(self, contact_id: int) -> None:
        query = "DELETE FROM contacts WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (contact_id,))

    def get_contact_by_id(self, contact_id: int) -> Contact | None:
        query = "SELECT id, name, phone, email, address, created_at FROM contacts WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (contact_id,)).fetchone()
            if not row:
                return None
            return Contact(
                id=row["id"],
                name=row["name"],
                phone=row["phone"],
                email=row["email"],
                address=row["address"],
                created_at=row["created_at"],
            )

    def get_contact_by_phone(self, phone: str) -> Contact | None:
        query = "SELECT id, name, phone, email, address, created_at FROM contacts WHERE phone = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (phone.strip(),)).fetchone()
            if not row:
                return None
            return Contact(
                id=row["id"],
                name=row["name"],
                phone=row["phone"],
                email=row["email"],
                address=row["address"],
                created_at=row["created_at"],
            )

    def get_contact_by_email(self, email: str) -> Contact | None:
        query = "SELECT id, name, phone, email, address, created_at FROM contacts WHERE email = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (email.strip().lower(),)).fetchone()
            if not row:
                return None
            return Contact(
                id=row["id"],
                name=row["name"],
                phone=row["phone"],
                email=row["email"],
                address=row["address"],
                created_at=row["created_at"],
            )

    def search_contacts(self, query_str: str) -> list[Contact]:
        pattern = f"%{query_str.strip()}%"
        query = """
            SELECT id, name, phone, email, address, created_at
            FROM contacts
            WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
            ORDER BY name ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (pattern, pattern, pattern)).fetchall()
            return [
                Contact(
                    id=r["id"],
                    name=r["name"],
                    phone=r["phone"],
                    email=r["email"],
                    address=r["address"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def list_contacts(self) -> list[Contact]:
        query = (
            "SELECT id, name, phone, email, address, created_at FROM contacts ORDER BY name ASC;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Contact(
                    id=r["id"],
                    name=r["name"],
                    phone=r["phone"],
                    email=r["email"],
                    address=r["address"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
