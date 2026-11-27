"""Service layer for Hospital Management System with appointment scheduling and billing logic.

IMPORTANT NOTICE:
The admin authentication functionality here is strictly an educational simulation.
It illustrates password hashing with scrypt, salt generation, and rate limiting.
It is NOT intended for production medical data or HIPAA compliance.
"""

from datetime import datetime, timedelta

from common.clock import Clock, SystemClock
from common.security import hash_secret, is_locked, verify_secret
from projects.p05_hospital_management.models import (
    AdminUser,
    AppointmentDetail,
    Bill,
    Doctor,
    Patient,
)
from projects.p05_hospital_management.repository import HospitalRepository


class HospitalError(Exception):
    """Base exception for hospital service errors."""

    pass


class DoctorNotFoundError(HospitalError):
    """Raised when a doctor ID cannot be found."""

    pass


class PatientNotFoundError(HospitalError):
    """Raised when a patient ID cannot be found."""

    pass


class DoubleBookingError(HospitalError):
    """Raised when attempting to double-book a doctor for the same time slot."""

    pass


class UnpaidBillsDischargeError(HospitalError):
    """Raised when attempting to discharge a patient with unpaid invoices."""

    pass


class AdminAuthError(HospitalError):
    """Raised when admin authentication fails or account is locked."""

    pass


class BillNotFoundError(HospitalError):
    """Raised when requested bill record does not exist."""

    pass


class HospitalService:
    """Coordinates hospital admissions, doctor appointments, billing, and admin authentication."""

    def __init__(
        self,
        repository: HospitalRepository,
        clock: Clock | None = None,
        max_admin_attempts: int = 3,
        lockout_minutes: int = 15,
    ) -> None:
        self.repo = repository
        self.clock = clock if clock is not None else SystemClock()
        self.max_admin_attempts = max_admin_attempts
        self.lockout_minutes = lockout_minutes


    def register_admin(self, username: str, password: str) -> None:
        user_clean = username.strip().lower()
        if not user_clean:
            raise AdminAuthError("Username cannot be empty.")
        if len(password) < 6:
            raise AdminAuthError("Password must be at least 6 characters.")

        existing = self.repo.get_admin(user_clean)
        if existing:
            raise AdminAuthError(f"Admin '{user_clean}' already exists.")

        pwd_hash, salt = hash_secret(password)
        admin = AdminUser(username=user_clean, password_hash=pwd_hash, salt=salt)
        self.repo.add_admin(admin)

    def authenticate_admin(self, username: str, password: str) -> AdminUser:
        user_clean = username.strip().lower()
        admin = self.repo.get_admin(user_clean)
        if not admin:
            raise AdminAuthError("Invalid admin credentials.")

        now_iso = self.clock.now_iso()
        if is_locked(admin.locked_until, now_iso):
            raise AdminAuthError(
                f"Admin account is locked due to multiple failed attempts. "
                f"Locked until: {admin.locked_until}."
            )

        if not verify_secret(password, admin.salt, admin.password_hash):
            attempts = admin.failed_attempts + 1
            if attempts >= self.max_admin_attempts:
                dt_now = datetime.fromisoformat(now_iso)
                locked_until = (dt_now + timedelta(minutes=self.lockout_minutes)).isoformat()
                self.repo.record_admin_failed_attempt(user_clean, attempts, locked_until)
                raise AdminAuthError(
                    f"Max failed attempts exceeded. Admin locked for {self.lockout_minutes} mins."
                )
            else:
                self.repo.record_admin_failed_attempt(user_clean, attempts, None)
                rem = self.max_admin_attempts - attempts
                raise AdminAuthError(f"Incorrect password. {rem} attempt(s) remaining.")

        if admin.failed_attempts > 0 or admin.locked_until is not None:
            self.repo.reset_admin_attempts(user_clean)

        return admin


    def register_doctor(
        self, name: str, specialization: str, consultation_fee_cents: int
    ) -> Doctor:
        doctor = Doctor(
            name=name.strip(),
            specialization=specialization.strip(),
            consultation_fee_cents=consultation_fee_cents,
        )
        return self.repo.add_doctor(doctor)

    def list_doctors(self) -> list[Doctor]:
        return self.repo.list_doctors()

    def admit_patient(self, name: str, dob: str, phone: str) -> Patient:
        today = self.clock.today_iso()
        patient = Patient(
            name=name.strip(),
            dob=dob.strip(),
            phone=phone.strip(),
            admission_date=today,
            status="ADMITTED",
        )
        return self.repo.add_patient(patient)

    def list_patients(self, status: str | None = None) -> list[Patient]:
        return self.repo.list_patients(status=status)

    def discharge_patient(self, patient_id: int) -> None:
        patient = self.repo.get_patient(patient_id)
        if not patient:
            raise PatientNotFoundError(f"Patient ID {patient_id} not found.")

        if patient.status == "DISCHARGED":
            raise HospitalError(f"Patient '{patient.name}' is already discharged.")

        unpaid_count = self.repo.get_unpaid_bills_count_for_patient(patient_id)
        if unpaid_count > 0:
            raise UnpaidBillsDischargeError(
                f"Cannot discharge patient '{patient.name}': {unpaid_count} unpaid bill(s) pending."
            )

        today = self.clock.today_iso()
        self.repo.discharge_patient(patient_id, today)


    def book_appointment(self, doctor_id: int, patient_id: int, slot_datetime: str) -> int:
        doctor = self.repo.get_doctor(doctor_id)
        if not doctor:
            raise DoctorNotFoundError(f"Doctor ID {doctor_id} not found.")

        patient = self.repo.get_patient(patient_id)
        if not patient:
            raise PatientNotFoundError(f"Patient ID {patient_id} not found.")

        slot_clean = slot_datetime.strip()
        existing = self.repo.get_appointment_by_slot(doctor_id, slot_clean)
        if existing:
            raise DoubleBookingError(
                f"Doctor '{doctor.name}' is already booked for slot '{slot_clean}'."
            )

        return self.repo.create_appointment(doctor_id, patient_id, slot_clean)

    def list_appointments(self) -> list[AppointmentDetail]:
        return self.repo.list_appointments()


    def generate_bill(
        self,
        patient_id: int,
        room_charge_cents: int = 0,
        doctor_fee_cents: int = 0,
        medicine_fee_cents: int = 0,
    ) -> Bill:
        patient = self.repo.get_patient(patient_id)
        if not patient:
            raise PatientNotFoundError(f"Patient ID {patient_id} not found.")

        if room_charge_cents < 0 or doctor_fee_cents < 0 or medicine_fee_cents < 0:
            raise HospitalError("Fee amounts cannot be negative.")

        total_cents = room_charge_cents + doctor_fee_cents + medicine_fee_cents
        created_at = self.clock.today_iso()

        bill = Bill(
            patient_id=patient_id,
            room_charge_cents=room_charge_cents,
            doctor_fee_cents=doctor_fee_cents,
            medicine_fee_cents=medicine_fee_cents,
            total_cents=total_cents,
            paid=False,
            created_at=created_at,
        )
        return self.repo.create_bill(bill)

    def settle_bill(self, bill_id: int) -> None:
        bill = self.repo.get_bill(bill_id)
        if not bill:
            raise BillNotFoundError(f"Bill ID {bill_id} not found.")
        if bill.paid:
            raise HospitalError(f"Bill ID {bill_id} is already settled.")
        self.repo.pay_bill(bill_id)

    def list_bills_for_patient(self, patient_id: int) -> list[Bill]:
        return self.repo.list_bills_for_patient(patient_id)
