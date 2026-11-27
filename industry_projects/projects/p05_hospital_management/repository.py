"""Database repository for Hospital Management System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p05_hospital_management.models import (
    AdminUser,
    Appointment,
    AppointmentDetail,
    Bill,
    Doctor,
    Patient,
)

HOSPITAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    specialization TEXT NOT NULL,
    consultation_fee_cents INTEGER NOT NULL CHECK(consultation_fee_cents >= 0)
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    dob TEXT NOT NULL,
    phone TEXT NOT NULL,
    admission_date TEXT NOT NULL,
    discharge_date TEXT,
    status TEXT NOT NULL DEFAULT 'ADMITTED' CHECK(status IN ('ADMITTED', 'DISCHARGED'))
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    slot_datetime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SCHEDULED'
        CHECK(status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')),
    UNIQUE(doctor_id, slot_datetime)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    room_charge_cents INTEGER NOT NULL DEFAULT 0 CHECK(room_charge_cents >= 0),
    doctor_fee_cents INTEGER NOT NULL DEFAULT 0 CHECK(doctor_fee_cents >= 0),
    medicine_fee_cents INTEGER NOT NULL DEFAULT 0 CHECK(medicine_fee_cents >= 0),
    total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
    paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_users (
    username TEXT PRIMARY KEY,
    password_hash BLOB NOT NULL,
    salt BLOB NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);

CREATE INDEX IF NOT EXISTS idx_appointments_slot ON appointments(doctor_id, slot_datetime);
CREATE INDEX IF NOT EXISTS idx_bills_patient ON bills(patient_id);
"""


class HospitalRepository:
    """Manages SQLite queries for hospital staff, patients, appointments, and billing."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "HospitalRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=HOSPITAL_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    @classmethod
    def in_memory(cls) -> "HospitalRepository":
        manager = DatabaseManager(
            db_path=":memory:",
            schema_sql=HOSPITAL_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)


    def add_doctor(self, doctor: Doctor) -> Doctor:
        query = """
            INSERT INTO doctors (name, specialization, consultation_fee_cents)
            VALUES (?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query, (doctor.name, doctor.specialization, doctor.consultation_fee_cents)
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for doctor.")
            doc_id = int(cursor.lastrowid)

        return Doctor(
            id=doc_id,
            name=doctor.name,
            specialization=doctor.specialization,
            consultation_fee_cents=doctor.consultation_fee_cents,
        )

    def get_doctor(self, doctor_id: int) -> Doctor | None:
        query = "SELECT id, name, specialization, consultation_fee_cents FROM doctors WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (doctor_id,)).fetchone()
            if not row:
                return None
            return Doctor(
                id=row["id"],
                name=row["name"],
                specialization=row["specialization"],
                consultation_fee_cents=row["consultation_fee_cents"],
            )

    def list_doctors(self) -> list[Doctor]:
        query = (
            "SELECT id, name, specialization, consultation_fee_cents "
            "FROM doctors ORDER BY name ASC;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Doctor(
                    id=r["id"],
                    name=r["name"],
                    specialization=r["specialization"],
                    consultation_fee_cents=r["consultation_fee_cents"],
                )
                for r in rows
            ]


    def add_patient(self, patient: Patient) -> Patient:
        query = """
            INSERT INTO patients (name, dob, phone, admission_date, status)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (patient.name, patient.dob, patient.phone, patient.admission_date, patient.status),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for patient.")
            p_id = int(cursor.lastrowid)

        return Patient(
            id=p_id,
            name=patient.name,
            dob=patient.dob,
            phone=patient.phone,
            admission_date=patient.admission_date,
            status=patient.status,
        )

    def get_patient(self, patient_id: int) -> Patient | None:
        query = """
            SELECT id, name, dob, phone, admission_date, discharge_date, status
            FROM patients WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (patient_id,)).fetchone()
            if not row:
                return None
            return Patient(
                id=row["id"],
                name=row["name"],
                dob=row["dob"],
                phone=row["phone"],
                admission_date=row["admission_date"],
                discharge_date=row["discharge_date"],
                status=row["status"],
            )

    def list_patients(self, status: str | None = None) -> list[Patient]:
        base_query = """
            SELECT id, name, dob, phone, admission_date, discharge_date, status
            FROM patients
        """
        params: list[str] = []
        if status:
            base_query += " WHERE status = ?"
            params.append(status)
        base_query += " ORDER BY id DESC;"

        with self.db.get_connection() as conn:
            rows = conn.execute(base_query, params).fetchall()
            return [
                Patient(
                    id=r["id"],
                    name=r["name"],
                    dob=r["dob"],
                    phone=r["phone"],
                    admission_date=r["admission_date"],
                    discharge_date=r["discharge_date"],
                    status=r["status"],
                )
                for r in rows
            ]

    def discharge_patient(self, patient_id: int, discharge_date: str) -> None:
        query = """
            UPDATE patients
            SET status = 'DISCHARGED', discharge_date = ?
            WHERE id = ?;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (discharge_date, patient_id))


    def create_appointment(self, doctor_id: int, patient_id: int, slot_datetime: str) -> int:
        query = """
            INSERT INTO appointments (doctor_id, patient_id, slot_datetime, status)
            VALUES (?, ?, ?, 'SCHEDULED');
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (doctor_id, patient_id, slot_datetime))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for appointment.")
            return int(cursor.lastrowid)

    def get_appointment_by_slot(self, doctor_id: int, slot_datetime: str) -> Appointment | None:
        query = """
            SELECT id, doctor_id, patient_id, slot_datetime, status
            FROM appointments
            WHERE doctor_id = ? AND slot_datetime = ? AND status != 'CANCELLED';
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (doctor_id, slot_datetime.strip())).fetchone()
            if not row:
                return None
            return Appointment(
                id=row["id"],
                doctor_id=row["doctor_id"],
                patient_id=row["patient_id"],
                slot_datetime=row["slot_datetime"],
                status=row["status"],
            )

    def list_appointments(self) -> list[AppointmentDetail]:
        query = """
            SELECT a.id, d.name AS doc_name, d.specialization, p.name AS pat_name,
                   a.slot_datetime, a.status
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN patients p ON a.patient_id = p.id
            ORDER BY a.slot_datetime ASC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                AppointmentDetail(
                    appointment_id=r["id"],
                    doctor_name=r["doc_name"],
                    specialization=r["specialization"],
                    patient_name=r["pat_name"],
                    slot_datetime=r["slot_datetime"],
                    status=r["status"],
                )
                for r in rows
            ]


    def create_bill(self, bill: Bill) -> Bill:
        query = """
            INSERT INTO bills (
                patient_id, room_charge_cents, doctor_fee_cents,
                medicine_fee_cents, total_cents, paid, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query,
                (
                    bill.patient_id,
                    bill.room_charge_cents,
                    bill.doctor_fee_cents,
                    bill.medicine_fee_cents,
                    bill.total_cents,
                    1 if bill.paid else 0,
                    bill.created_at,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for bill.")
            b_id = int(cursor.lastrowid)

        return Bill(
            id=b_id,
            patient_id=bill.patient_id,
            room_charge_cents=bill.room_charge_cents,
            doctor_fee_cents=bill.doctor_fee_cents,
            medicine_fee_cents=bill.medicine_fee_cents,
            total_cents=bill.total_cents,
            paid=bill.paid,
            created_at=bill.created_at,
        )

    def get_bill(self, bill_id: int) -> Bill | None:
        query = """
            SELECT id, patient_id, room_charge_cents, doctor_fee_cents,
                   medicine_fee_cents, total_cents, paid, created_at
            FROM bills WHERE id = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (bill_id,)).fetchone()
            if not row:
                return None
            return Bill(
                id=row["id"],
                patient_id=row["patient_id"],
                room_charge_cents=row["room_charge_cents"],
                doctor_fee_cents=row["doctor_fee_cents"],
                medicine_fee_cents=row["medicine_fee_cents"],
                total_cents=row["total_cents"],
                paid=bool(row["paid"]),
                created_at=row["created_at"],
            )

    def get_unpaid_bills_count_for_patient(self, patient_id: int) -> int:
        query = "SELECT COUNT(*) FROM bills WHERE patient_id = ? AND paid = 0;"
        with self.db.get_connection() as conn:
            val = conn.execute(query, (patient_id,)).fetchone()[0]
            return int(val)

    def pay_bill(self, bill_id: int) -> None:
        query = "UPDATE bills SET paid = 1 WHERE id = ?;"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (bill_id,))

    def list_bills_for_patient(self, patient_id: int) -> list[Bill]:
        query = """
            SELECT id, patient_id, room_charge_cents, doctor_fee_cents,
                   medicine_fee_cents, total_cents, paid, created_at
            FROM bills WHERE patient_id = ? ORDER BY id DESC;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (patient_id,)).fetchall()
            return [
                Bill(
                    id=r["id"],
                    patient_id=r["patient_id"],
                    room_charge_cents=r["room_charge_cents"],
                    doctor_fee_cents=r["doctor_fee_cents"],
                    medicine_fee_cents=r["medicine_fee_cents"],
                    total_cents=r["total_cents"],
                    paid=bool(r["paid"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]


    def add_admin(self, admin: AdminUser) -> None:
        query = """
            INSERT INTO admin_users (username, password_hash, salt, failed_attempts, locked_until)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(
                query,
                (
                    admin.username,
                    admin.password_hash,
                    admin.salt,
                    admin.failed_attempts,
                    admin.locked_until,
                ),
            )

    def get_admin(self, username: str) -> AdminUser | None:
        query = """
            SELECT username, password_hash, salt, failed_attempts, locked_until
            FROM admin_users WHERE username = ?;
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (username.strip().lower(),)).fetchone()
            if not row:
                return None
            return AdminUser(
                username=row["username"],
                password_hash=row["password_hash"],
                salt=row["salt"],
                failed_attempts=row["failed_attempts"],
                locked_until=row["locked_until"],
            )

    def record_admin_failed_attempt(
        self, username: str, attempts: int, locked_until: str | None = None
    ) -> None:
        query = """
            UPDATE admin_users
            SET failed_attempts = ?, locked_until = ?
            WHERE username = ?;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (attempts, locked_until, username.strip().lower()))

    def reset_admin_attempts(self, username: str) -> None:
        query = """
            UPDATE admin_users
            SET failed_attempts = 0, locked_until = NULL
            WHERE username = ?;
        """
        with self.db.get_connection() as conn, conn:
            conn.execute(query, (username.strip().lower(),))
