"""Data models for Hospital Management System."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Doctor:
    """Represents a medical specialist on hospital staff."""

    name: str
    specialization: str
    consultation_fee_cents: int
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Doctor name cannot be empty.")
        if not self.specialization.strip():
            raise ValueError("Specialization cannot be empty.")
        if self.consultation_fee_cents < 0:
            raise ValueError("Consultation fee cannot be negative.")


@dataclass(frozen=True)
class Patient:
    """Represents an admitted or outpatient individual."""

    name: str
    dob: str
    phone: str
    admission_date: str
    discharge_date: str | None = None
    status: str = "ADMITTED"  # ADMITTED, DISCHARGED
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Patient name cannot be empty.")
        if not self.phone.strip():
            raise ValueError("Patient phone cannot be empty.")


@dataclass(frozen=True)
class Appointment:
    """Represents a scheduled consultation between a patient and a doctor."""

    doctor_id: int
    patient_id: int
    slot_datetime: str  # YYYY-MM-DD HH:MM
    status: str = "SCHEDULED"  # SCHEDULED, COMPLETED, CANCELLED
    id: int | None = None


@dataclass(frozen=True)
class AppointmentDetail:
    """Composite projection for formatted appointment displays."""

    appointment_id: int
    doctor_name: str
    specialization: str
    patient_name: str
    slot_datetime: str
    status: str


@dataclass(frozen=True)
class Bill:
    """Represents an itemized patient invoice."""

    patient_id: int
    room_charge_cents: int
    doctor_fee_cents: int
    medicine_fee_cents: int
    total_cents: int
    paid: bool = False
    created_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class AdminUser:
    """Represents an educational administrative login record."""

    username: str
    password_hash: bytes
    salt: bytes
    failed_attempts: int = 0
    locked_until: str | None = None
