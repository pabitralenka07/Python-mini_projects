"""Database repository for Electricity Bill Management System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p09_electricity_bill.models import (
    BillDetail,
    Consumer,
    ElectricityBill,
    MeterReading,
)

ELECTRICITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS consumers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumer_number TEXT NOT NULL UNIQUE CHECK(length(trim(consumer_number)) > 0),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    address TEXT NOT NULL CHECK(length(trim(address)) > 0),
    meter_number TEXT NOT NULL UNIQUE CHECK(length(trim(meter_number)) > 0),
    tariff_category TEXT NOT NULL DEFAULT 'RESIDENTIAL'
        CHECK(tariff_category IN ('RESIDENTIAL', 'COMMERCIAL'))
);

CREATE TABLE IF NOT EXISTS meter_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumer_id INTEGER NOT NULL REFERENCES consumers(id) ON DELETE CASCADE,
    reading_date TEXT NOT NULL,
    reading_value INTEGER NOT NULL CHECK(reading_value >= 0)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumer_id INTEGER NOT NULL REFERENCES consumers(id) ON DELETE CASCADE,
    bill_number TEXT NOT NULL UNIQUE CHECK(length(trim(bill_number)) > 0),
    previous_reading INTEGER NOT NULL CHECK(previous_reading >= 0),
    current_reading INTEGER NOT NULL CHECK(current_reading >= previous_reading),
    units_consumed INTEGER NOT NULL CHECK(units_consumed >= 0),
    energy_charge_cents INTEGER NOT NULL CHECK(energy_charge_cents >= 0),
    fixed_charge_cents INTEGER NOT NULL CHECK(fixed_charge_cents >= 0),
    tax_cents INTEGER NOT NULL CHECK(tax_cents >= 0),
    total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'UNPAID' CHECK(status IN ('UNPAID', 'PAID')),
    issued_at TEXT NOT NULL,
    paid_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_readings_consumer ON meter_readings(consumer_id);
CREATE INDEX IF NOT EXISTS idx_bills_consumer ON bills(consumer_id);
"""


class ElectricityRepository:
    """Manages SQLite queries for electricity consumers, meter readings, and bills."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "ElectricityRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=ELECTRICITY_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    @classmethod
    def in_memory(cls) -> "ElectricityRepository":
        manager = DatabaseManager(
            db_path=":memory:",
            schema_sql=ELECTRICITY_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)


    def add_consumer(self, consumer: Consumer) -> Consumer:
        query = """
            INSERT INTO consumers (consumer_number, name, address, meter_number, tariff_category)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    consumer.consumer_number,
                    consumer.name,
                    consumer.address,
                    consumer.meter_number,
                    consumer.tariff_category,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for consumer.")
            c_id = int(cursor.lastrowid)

        return Consumer(
            id=c_id,
            consumer_number=consumer.consumer_number,
            name=consumer.name,
            address=consumer.address,
            meter_number=consumer.meter_number,
            tariff_category=consumer.tariff_category,
        )

    def get_consumer(self, consumer_id: int) -> Consumer | None:
        query = """
            SELECT id, consumer_number, name, address, meter_number, tariff_category
            FROM consumers WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (consumer_id,)).fetchone()
            if not row:
                return None
            return Consumer(
                id=row["id"],
                consumer_number=row["consumer_number"],
                name=row["name"],
                address=row["address"],
                meter_number=row["meter_number"],
                tariff_category=row["tariff_category"],
            )

    def get_consumer_by_number(self, consumer_number: str) -> Consumer | None:
        query = """
            SELECT id, consumer_number, name, address, meter_number, tariff_category
            FROM consumers WHERE consumer_number = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (consumer_number,)).fetchone()
            if not row:
                return None
            return Consumer(
                id=row["id"],
                consumer_number=row["consumer_number"],
                name=row["name"],
                address=row["address"],
                meter_number=row["meter_number"],
                tariff_category=row["tariff_category"],
            )

    def list_consumers(self) -> list[Consumer]:
        query = """
            SELECT id, consumer_number, name, address, meter_number, tariff_category
            FROM consumers ORDER BY consumer_number ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Consumer(
                    id=r["id"],
                    consumer_number=r["consumer_number"],
                    name=r["name"],
                    address=r["address"],
                    meter_number=r["meter_number"],
                    tariff_category=r["tariff_category"],
                )
                for r in rows
            ]


    def add_meter_reading(self, reading: MeterReading) -> MeterReading:
        query = (
            "INSERT INTO meter_readings (consumer_id, reading_date, reading_value) "
            "VALUES (?, ?, ?);"
        )
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query, (reading.consumer_id, reading.reading_date, reading.reading_value)
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for meter reading.")
            mr_id = int(cursor.lastrowid)

        return MeterReading(
            id=mr_id,
            consumer_id=reading.consumer_id,
            reading_date=reading.reading_date,
            reading_value=reading.reading_value,
        )

    def get_latest_meter_reading(self, consumer_id: int) -> MeterReading | None:
        query = """
            SELECT id, consumer_id, reading_date, reading_value
            FROM meter_readings
            WHERE consumer_id = ?
            ORDER BY reading_date DESC, id DESC
            LIMIT 1;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (consumer_id,)).fetchone()
            if not row:
                return None
            return MeterReading(
                id=row["id"],
                consumer_id=row["consumer_id"],
                reading_date=row["reading_date"],
                reading_value=row["reading_value"],
            )


    def create_bill(self, bill: ElectricityBill) -> ElectricityBill:
        query = """
            INSERT INTO bills (
                consumer_id, bill_number, previous_reading, current_reading,
                units_consumed, energy_charge_cents, fixed_charge_cents,
                tax_cents, total_cents, due_date, status, issued_at, paid_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    bill.consumer_id,
                    bill.bill_number,
                    bill.previous_reading,
                    bill.current_reading,
                    bill.units_consumed,
                    bill.energy_charge_cents,
                    bill.fixed_charge_cents,
                    bill.tax_cents,
                    bill.total_cents,
                    bill.due_date,
                    bill.status,
                    bill.issued_at,
                    bill.paid_at,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for bill.")
            b_id = int(cursor.lastrowid)

        return ElectricityBill(
            id=b_id,
            consumer_id=bill.consumer_id,
            bill_number=bill.bill_number,
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
        )

    def get_bill(self, bill_id: int) -> ElectricityBill | None:
        query = """
            SELECT id, consumer_id, bill_number, previous_reading, current_reading,
                   units_consumed, energy_charge_cents, fixed_charge_cents,
                   tax_cents, total_cents, due_date, status, issued_at, paid_at
            FROM bills WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (bill_id,)).fetchone()
            if not row:
                return None
            return ElectricityBill(
                id=row["id"],
                consumer_id=row["consumer_id"],
                bill_number=row["bill_number"],
                previous_reading=row["previous_reading"],
                current_reading=row["current_reading"],
                units_consumed=row["units_consumed"],
                energy_charge_cents=row["energy_charge_cents"],
                fixed_charge_cents=row["fixed_charge_cents"],
                tax_cents=row["tax_cents"],
                total_cents=row["total_cents"],
                due_date=row["due_date"],
                status=row["status"],
                issued_at=row["issued_at"],
                paid_at=row["paid_at"],
            )

    def list_bills_for_consumer(self, consumer_id: int) -> list[ElectricityBill]:
        query = """
            SELECT id, consumer_id, bill_number, previous_reading, current_reading,
                   units_consumed, energy_charge_cents, fixed_charge_cents,
                   tax_cents, total_cents, due_date, status, issued_at, paid_at
            FROM bills WHERE consumer_id = ? ORDER BY issued_at DESC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (consumer_id,)).fetchall()
            return [
                ElectricityBill(
                    id=r["id"],
                    consumer_id=r["consumer_id"],
                    bill_number=r["bill_number"],
                    previous_reading=r["previous_reading"],
                    current_reading=r["current_reading"],
                    units_consumed=r["units_consumed"],
                    energy_charge_cents=r["energy_charge_cents"],
                    fixed_charge_cents=r["fixed_charge_cents"],
                    tax_cents=r["tax_cents"],
                    total_cents=r["total_cents"],
                    due_date=r["due_date"],
                    status=r["status"],
                    issued_at=r["issued_at"],
                    paid_at=r["paid_at"],
                )
                for r in rows
            ]

    def list_all_bill_details(self) -> list[BillDetail]:
        query = """
            SELECT
                b.id as bill_id,
                b.bill_number,
                c.consumer_number,
                c.name as consumer_name,
                c.meter_number,
                c.tariff_category,
                b.previous_reading,
                b.current_reading,
                b.units_consumed,
                b.energy_charge_cents,
                b.fixed_charge_cents,
                b.tax_cents,
                b.total_cents,
                b.due_date,
                b.status,
                b.issued_at,
                b.paid_at
            FROM bills b
            JOIN consumers c ON b.consumer_id = c.id
            ORDER BY b.issued_at DESC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                BillDetail(
                    bill_id=r["bill_id"],
                    bill_number=r["bill_number"],
                    consumer_number=r["consumer_number"],
                    consumer_name=r["consumer_name"],
                    meter_number=r["meter_number"],
                    tariff_category=r["tariff_category"],
                    previous_reading=r["previous_reading"],
                    current_reading=r["current_reading"],
                    units_consumed=r["units_consumed"],
                    energy_charge_cents=r["energy_charge_cents"],
                    fixed_charge_cents=r["fixed_charge_cents"],
                    tax_cents=r["tax_cents"],
                    total_cents=r["total_cents"],
                    due_date=r["due_date"],
                    status=r["status"],
                    issued_at=r["issued_at"],
                    paid_at=r["paid_at"],
                )
                for r in rows
            ]

    def mark_bill_paid(self, bill_id: int, paid_at: str) -> None:
        query = "UPDATE bills SET status = 'PAID', paid_at = ? WHERE id = ? AND status = 'UNPAID';"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (paid_at, bill_id))
            if cursor.rowcount == 0:
                raise DatabaseError(f"Bill ID {bill_id} could not be settled or is already paid.")
