"""Tests for Project 05: Hospital Management System."""

from unittest.mock import patch

import pytest

from common.clock import FrozenClock
from projects.p05_hospital_management.cli import run_cli
from projects.p05_hospital_management.repository import HospitalRepository
from projects.p05_hospital_management.service import (
    AdminAuthError,
    DoubleBookingError,
    HospitalService,
    UnpaidBillsDischargeError,
)


@pytest.fixture
def hospital_setup() -> tuple[HospitalRepository, HospitalService]:
    repo = HospitalRepository.in_memory()
    service = HospitalService(repo)
    return repo, service


def test_doctor_and_patient_registration(
    hospital_setup: tuple[HospitalRepository, HospitalService],
) -> None:
    repo, service = hospital_setup
    doc = service.register_doctor(
        name="Dr. Smith",
        specialization="Neurology",
        consultation_fee_cents=20000,
    )
    pat = service.admit_patient(
        name="Alice",
        dob="1992-05-10",
        phone="555-1234",
    )

    assert doc.id is not None
    fetched_doc = repo.get_doctor(doc.id)
    assert fetched_doc is not None
    assert fetched_doc.name == "Dr. Smith"
    assert fetched_doc.consultation_fee_cents == 20000

    assert pat.id is not None
    fetched_pat = repo.get_patient(pat.id)
    assert fetched_pat is not None
    assert fetched_pat.name == "Alice"
    assert fetched_pat.status == "ADMITTED"


def test_double_booking_prevention(
    hospital_setup: tuple[HospitalRepository, HospitalService],
) -> None:
    repo, service = hospital_setup
    doc = service.register_doctor(
        name="Dr. Jones",
        specialization="General",
        consultation_fee_cents=10000,
    )
    p1 = service.admit_patient("P1", "1990-01-01", "555-0001")
    p2 = service.admit_patient("P2", "1991-01-01", "555-0002")

    assert doc.id is not None
    assert p1.id is not None
    assert p2.id is not None

    app1_id = service.book_appointment(
        doctor_id=doc.id,
        patient_id=p1.id,
        slot_datetime="2026-11-10 09:00",
    )
    assert app1_id > 0

    with pytest.raises(DoubleBookingError, match="already booked for slot"):
        service.book_appointment(
            doctor_id=doc.id,
            patient_id=p2.id,
            slot_datetime="2026-11-10 09:00",
        )

    app2_id = service.book_appointment(
        doctor_id=doc.id,
        patient_id=p2.id,
        slot_datetime="2026-11-10 10:00",
    )
    assert app2_id > 0


def test_discharge_blocked_by_unpaid_bills(
    hospital_setup: tuple[HospitalRepository, HospitalService],
) -> None:
    repo, service = hospital_setup
    pat = service.admit_patient("Bob", "1985-07-20", "555-8888")
    assert pat.id is not None

    bill = service.generate_bill(
        patient_id=pat.id,
        room_charge_cents=10000,
        doctor_fee_cents=15000,
        medicine_fee_cents=5000,
    )
    assert bill.id is not None
    assert bill.total_cents == 30000

    with pytest.raises(UnpaidBillsDischargeError, match="unpaid bill"):
        service.discharge_patient(pat.id)

    service.settle_bill(bill.id)

    service.discharge_patient(pat.id)
    updated_pat = repo.get_patient(pat.id)
    assert updated_pat is not None
    assert updated_pat.status == "DISCHARGED"
    assert updated_pat.discharge_date is not None


def test_admin_auth_and_lockout() -> None:
    clock = FrozenClock()
    repo = HospitalRepository.in_memory()
    service = HospitalService(repo, clock=clock, max_admin_attempts=3, lockout_minutes=15)

    service.register_admin("head_nurse", "securepass123")

    with pytest.raises(AdminAuthError, match="Incorrect password"):
        service.authenticate_admin("head_nurse", "wrongpass1")

    with pytest.raises(AdminAuthError, match="Incorrect password"):
        service.authenticate_admin("head_nurse", "wrongpass2")

    with pytest.raises(AdminAuthError, match="Max failed attempts exceeded"):
        service.authenticate_admin("head_nurse", "wrongpass3")

    with pytest.raises(AdminAuthError, match="locked due to multiple failed attempts"):
        service.authenticate_admin("head_nurse", "securepass123")

    clock.advance(16 * 60)

    admin = service.authenticate_admin("head_nurse", "securepass123")
    assert admin.username == "head_nurse"


def test_cli_handles_eof_gracefully(
    hospital_setup: tuple[HospitalRepository, HospitalService],
) -> None:
    _, service = hospital_setup
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)
