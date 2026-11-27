"""Seed script for Hospital Management System with initial sample data."""

from pathlib import Path

from projects.p05_hospital_management.repository import HospitalRepository
from projects.p05_hospital_management.service import (
    AdminAuthError,
    DoubleBookingError,
    HospitalService,
)


def seed_data(repo: HospitalRepository | None = None) -> None:
    if repo is None:
        db_path = Path(__file__).resolve().parent / "data" / "hospital.db"
        repo = HospitalRepository.from_path(db_path)

    service = HospitalService(repo)

    print("Seeding Hospital Management System...")

    try:
        service.register_admin("admin", "admin123")
        print(" -> Created admin user 'admin' (password: admin123)")
    except AdminAuthError:
        print(" -> Admin user 'admin' already exists.")

    existing_docs = service.list_doctors()
    doc_ids: list[int] = []
    if not existing_docs:
        d1 = service.register_doctor("Dr. Sarah Connor", "Cardiology", 15000)
        d2 = service.register_doctor("Dr. Gregory House", "Diagnostics", 25000)
        d3 = service.register_doctor("Dr. Leonard McCoy", "General Medicine", 10000)
        doc_ids = [d.id for d in [d1, d2, d3] if d.id is not None]
        print(f" -> Added {len(doc_ids)} doctors.")
    else:
        doc_ids = [d.id for d in existing_docs if d.id is not None]
        print(f" -> Doctors already exist ({len(doc_ids)} found).")

    existing_pats = service.list_patients()
    pat_ids: list[int] = []
    if not existing_pats:
        p1 = service.admit_patient("John Doe", "1988-04-12", "555-0101")
        p2 = service.admit_patient("Jane Smith", "1994-09-23", "555-0102")
        p3 = service.admit_patient("Robert Paulson", "1980-01-15", "555-0103")
        pat_ids = [p.id for p in [p1, p2, p3] if p.id is not None]
        print(f" -> Admitted {len(pat_ids)} patients.")
    else:
        pat_ids = [p.id for p in existing_pats if p.id is not None]
        print(f" -> Patients already exist ({len(pat_ids)} found).")

    if doc_ids and pat_ids:
        try:
            service.book_appointment(
                doctor_id=doc_ids[0],
                patient_id=pat_ids[0],
                slot_datetime="2026-11-05 10:00",
            )
            print(" -> Booked appointment for patient 1 with doctor 1")
        except DoubleBookingError:
            pass

        if len(doc_ids) > 1 and len(pat_ids) > 1:
            try:
                service.book_appointment(
                    doctor_id=doc_ids[1],
                    patient_id=pat_ids[1],
                    slot_datetime="2026-11-05 11:00",
                )
                print(" -> Booked appointment for patient 2 with doctor 2")
            except DoubleBookingError:
                pass

    if pat_ids:
        bills = repo.list_bills_for_patient(pat_ids[0])
        if not bills:
            b1 = service.generate_bill(
                patient_id=pat_ids[0],
                room_charge_cents=5000,
                doctor_fee_cents=15000,
                medicine_fee_cents=2500,
            )
            if b1.id is not None:
                service.settle_bill(b1.id)
                print(f" -> Generated and settled bill for patient {pat_ids[0]}")

        if len(pat_ids) > 2:
            b2 = repo.list_bills_for_patient(pat_ids[2])
            if not b2:
                service.generate_bill(
                    patient_id=pat_ids[2],
                    room_charge_cents=10000,
                    doctor_fee_cents=20000,
                    medicine_fee_cents=5000,
                )
                print(f" -> Generated unpaid bill for patient {pat_ids[2]}")

    print("Hospital Management System seeding complete.")


if __name__ == "__main__":
    seed_data()
