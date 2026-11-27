"""Database repository for Zoo Management System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p08_zoo_management.models import (
    Animal,
    DailyRevenueReport,
    Enclosure,
    EnclosureDetail,
    FeedingScheduleEntry,
    Keeper,
    TicketSale,
    TicketType,
)

ZOO_SCHEMA = """
CREATE TABLE IF NOT EXISTS enclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    habitat_type TEXT NOT NULL CHECK(length(trim(habitat_type)) > 0),
    max_capacity INTEGER NOT NULL CHECK(max_capacity > 0)
);

CREATE TABLE IF NOT EXISTS animals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    species TEXT NOT NULL CHECK(length(trim(species)) > 0),
    age_years INTEGER NOT NULL CHECK(age_years >= 0),
    dietary_category TEXT NOT NULL
        CHECK(dietary_category IN ('CARNIVORE', 'HERBIVORE', 'OMNIVORE')),
    enclosure_id INTEGER NOT NULL REFERENCES enclosures(id) ON DELETE RESTRICT,
    feeding_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS keepers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    employee_id TEXT NOT NULL UNIQUE CHECK(length(trim(employee_id)) > 0),
    assigned_enclosure_id INTEGER REFERENCES enclosures(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ticket_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_type TEXT NOT NULL CHECK(ticket_type IN ('ADULT', 'CHILD', 'SENIOR')),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents >= 0),
    total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
    sold_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_animals_enclosure ON animals(enclosure_id);
CREATE INDEX IF NOT EXISTS idx_ticket_sales_date ON ticket_sales(sold_at);
"""


class ZooRepository:
    """Manages SQLite queries for enclosures, animals, keepers, and ticket admissions."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "ZooRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=ZOO_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    @classmethod
    def in_memory(cls) -> "ZooRepository":
        manager = DatabaseManager(
            db_path=":memory:",
            schema_sql=ZOO_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)


    def add_enclosure(self, enc: Enclosure) -> Enclosure:
        query = "INSERT INTO enclosures (name, habitat_type, max_capacity) VALUES (?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (enc.name, enc.habitat_type, enc.max_capacity))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for enclosure.")
            enc_id = int(cursor.lastrowid)

        return Enclosure(
            id=enc_id, name=enc.name, habitat_type=enc.habitat_type, max_capacity=enc.max_capacity
        )

    def get_enclosure(self, enclosure_id: int) -> Enclosure | None:
        query = "SELECT id, name, habitat_type, max_capacity FROM enclosures WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (enclosure_id,)).fetchone()
            if not row:
                return None
            return Enclosure(
                id=row["id"],
                name=row["name"],
                habitat_type=row["habitat_type"],
                max_capacity=row["max_capacity"],
            )

    def get_enclosure_by_name(self, name: str) -> Enclosure | None:
        query = "SELECT id, name, habitat_type, max_capacity FROM enclosures WHERE name = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (name,)).fetchone()
            if not row:
                return None
            return Enclosure(
                id=row["id"],
                name=row["name"],
                habitat_type=row["habitat_type"],
                max_capacity=row["max_capacity"],
            )

    def count_animals_in_enclosure(self, enclosure_id: int) -> int:
        query = "SELECT COUNT(*) as cnt FROM animals WHERE enclosure_id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (enclosure_id,)).fetchone()
            return int(row["cnt"]) if row else 0

    def list_enclosure_details(self) -> list[EnclosureDetail]:
        query = """
            SELECT
                e.id as enclosure_id,
                e.name,
                e.habitat_type,
                e.max_capacity,
                COUNT(a.id) as current_animals
            FROM enclosures e
            LEFT JOIN animals a ON e.id = a.enclosure_id
            GROUP BY e.id
            ORDER BY e.name ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                EnclosureDetail(
                    enclosure_id=r["enclosure_id"],
                    name=r["name"],
                    habitat_type=r["habitat_type"],
                    max_capacity=r["max_capacity"],
                    current_animals=r["current_animals"],
                    available_capacity=r["max_capacity"] - r["current_animals"],
                )
                for r in rows
            ]


    def add_animal(self, animal: Animal) -> Animal:
        query = """
            INSERT INTO animals (
                name, species, age_years, dietary_category, enclosure_id, feeding_time
            ) VALUES (?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    animal.name,
                    animal.species,
                    animal.age_years,
                    animal.dietary_category,
                    animal.enclosure_id,
                    animal.feeding_time,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for animal.")
            an_id = int(cursor.lastrowid)

        return Animal(
            id=an_id,
            name=animal.name,
            species=animal.species,
            age_years=animal.age_years,
            dietary_category=animal.dietary_category,
            enclosure_id=animal.enclosure_id,
            feeding_time=animal.feeding_time,
        )

    def list_feeding_schedule(self) -> list[FeedingScheduleEntry]:
        query = """
            SELECT
                a.id as animal_id,
                a.name as animal_name,
                a.species,
                e.name as enclosure_name,
                a.dietary_category,
                a.feeding_time
            FROM animals a
            JOIN enclosures e ON a.enclosure_id = e.id
            ORDER BY a.feeding_time ASC, a.name ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                FeedingScheduleEntry(
                    animal_id=r["animal_id"],
                    animal_name=r["animal_name"],
                    species=r["species"],
                    enclosure_name=r["enclosure_name"],
                    dietary_category=r["dietary_category"],
                    feeding_time=r["feeding_time"],
                )
                for r in rows
            ]


    def add_keeper(self, keeper: Keeper) -> Keeper:
        query = "INSERT INTO keepers (name, employee_id, assigned_enclosure_id) VALUES (?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query, (keeper.name, keeper.employee_id, keeper.assigned_enclosure_id)
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for keeper.")
            k_id = int(cursor.lastrowid)

        return Keeper(
            id=k_id,
            name=keeper.name,
            employee_id=keeper.employee_id,
            assigned_enclosure_id=keeper.assigned_enclosure_id,
        )

    def list_keepers(self) -> list[Keeper]:
        query = (
            "SELECT id, name, employee_id, assigned_enclosure_id FROM keepers ORDER BY name ASC;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Keeper(
                    id=r["id"],
                    name=r["name"],
                    employee_id=r["employee_id"],
                    assigned_enclosure_id=r["assigned_enclosure_id"],
                )
                for r in rows
            ]

    def assign_keeper_enclosure(self, keeper_id: int, enclosure_id: int) -> None:
        query = "UPDATE keepers SET assigned_enclosure_id = ? WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (enclosure_id, keeper_id))
            if cursor.rowcount == 0:
                raise DatabaseError(f"Keeper ID {keeper_id} not found.")


    def record_ticket_sale(self, sale: TicketSale) -> TicketSale:
        query = """
            INSERT INTO ticket_sales (ticket_type, quantity, unit_price_cents, total_cents, sold_at)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    sale.ticket_type,
                    sale.quantity,
                    sale.unit_price_cents,
                    sale.total_cents,
                    sale.sold_at,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for ticket sale.")
            sale_id = int(cursor.lastrowid)

        return TicketSale(
            id=sale_id,
            ticket_type=sale.ticket_type,
            quantity=sale.quantity,
            unit_price_cents=sale.unit_price_cents,
            total_cents=sale.total_cents,
            sold_at=sale.sold_at,
        )

    def get_daily_revenue_report(self, date_prefix: str) -> DailyRevenueReport:
        query = """
            SELECT
                ticket_type,
                SUM(quantity) as total_qty,
                SUM(total_cents) as total_amount
            FROM ticket_sales
            WHERE sold_at LIKE ?
            GROUP BY ticket_type;
        """
        like_pattern = f"{date_prefix}%"
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (like_pattern,)).fetchall()

        adult_qty = 0
        child_qty = 0
        senior_qty = 0
        total_rev = 0

        for r in rows:
            tt = r["ticket_type"]
            qty = int(r["total_qty"] or 0)
            amt = int(r["total_amount"] or 0)
            total_rev += amt

            if tt == TicketType.ADULT:
                adult_qty += qty
            elif tt == TicketType.CHILD:
                child_qty += qty
            elif tt == TicketType.SENIOR:
                senior_qty += qty

        return DailyRevenueReport(
            sale_date=date_prefix,
            adult_tickets=adult_qty,
            child_tickets=child_qty,
            senior_tickets=senior_qty,
            total_tickets=adult_qty + child_qty + senior_qty,
            total_revenue_cents=total_rev,
        )
