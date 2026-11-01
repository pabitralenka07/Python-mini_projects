"""CLI interface for Hospital Management System.

================================================================================
Concepts used:
1. Double-Booking Constraint: Uses database UNIQUE constraints and service
   validation to prevent scheduling multiple patients for the same doctor slot.
2. Invariant Enforcement: Blocks patient discharge until all accumulated billing
   invoices are marked as paid.
3. Educational Admin Simulation: Illustrates role-gated administrative features
   with password hashing and lockout safeguards.
================================================================================
"""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display, parse_money_to_cents
from common.security import prompt_password
from common.tables import format_table
from projects.p05_hospital_management.repository import HospitalRepository
from projects.p05_hospital_management.service import (
    HospitalError,
    HospitalService,
)


def get_default_service() -> HospitalService:
    db_path = Path(__file__).resolve().parent / "data" / "hospital.db"
    repo = HospitalRepository.from_path(db_path)
    return HospitalService(repo)


def display_menu(current_admin: str | None) -> None:
    admin_status = f"Logged in as: {current_admin}" if current_admin else "Not Logged In (Guest)"
    print("\n" + "=" * 48)
    print("         HOSPITAL MANAGEMENT SYSTEM             ")
    print(f"  [{admin_status}]")
    print("=" * 48)
    print(" 1. Admin Login / Logout")
    print(" 2. Register Doctor")
    print(" 3. Admit Patient")
    print(" 4. Book Appointment (No Double-Booking)")
    print(" 5. Generate Patient Bill")
    print(" 6. Settle (Pay) Patient Bill")
    print(" 7. Discharge Patient (Unpaid Check)")
    print(" 8. View Appointments Schedule")
    print(" 9. View Patients Directory")
    print(" 10. View Doctors Directory")
    print(" 0. Exit")
    print("=" * 48)


def run_cli(service: HospitalService | None = None) -> None:
    if service is None:
        service = get_default_service()

    current_admin: str | None = None

    while True:
        try:
            display_menu(current_admin)
            choice = prompt_int("Enter option (0-10)", min_val=0, max_val=10)
        except UserExitException:
            print("\nGoodbye! Exiting Hospital Management System.")
            break

        if choice == 0:
            print("\nGoodbye! Exiting Hospital Management System.")
            break

        try:
            if choice == 1:
                current_admin = _handle_admin_auth(service, current_admin)
            elif choice == 2:
                _handle_register_doctor(service)
            elif choice == 3:
                _handle_admit_patient(service)
            elif choice == 4:
                _handle_book_appointment(service)
            elif choice == 5:
                _handle_generate_bill(service)
            elif choice == 6:
                _handle_settle_bill(service)
            elif choice == 7:
                _handle_discharge(service)
            elif choice == 8:
                _handle_view_appointments(service)
            elif choice == 9:
                _handle_view_patients(service)
            elif choice == 10:
                _handle_view_doctors(service)
        except UserExitException:
            print("\nReturning to main menu...")
        except HospitalError as err:
            print(f"\n[Hospital Error] {err}")
        except Exception as err:
            print(f"\n[Unexpected Error] {err}")


def _handle_admin_auth(service: HospitalService, current_admin: str | None) -> str | None:
    if current_admin:
        if confirm_action(f"Currently logged in as {current_admin}. Log out?"):
            print("\nLogged out successfully.")
            return None
        return current_admin

    print("\n--- Admin Login (Educational Simulation) ---")
    user = safe_input("Username: ")
    pwd = prompt_password("Password: ")
    admin = service.authenticate_admin(user, pwd)
    print(f"\nSuccess: Authenticated as admin '{admin.username}'!")
    return admin.username


def _handle_register_doctor(service: HospitalService) -> None:
    print("\n--- Register Doctor ---")
    name = safe_input("Doctor Name: ")
    spec = safe_input("Specialization (e.g., Cardiology): ")
    fee_str = safe_input("Consultation Fee (e.g. $150.00): ")
    fee_cents = parse_money_to_cents(fee_str)

    doc = service.register_doctor(name, spec, fee_cents)
    print(f"\nSuccess: Dr. {doc.name} ({doc.specialization}) registered with ID {doc.id}!")


def _handle_admit_patient(service: HospitalService) -> None:
    print("\n--- Admit Patient ---")
    name = safe_input("Patient Full Name: ")
    dob = safe_input("Date of Birth (YYYY-MM-DD): ")
    phone = safe_input("Phone Number: ")

    patient = service.admit_patient(name, dob, phone)
    print(f"\nSuccess: Patient '{patient.name}' admitted with ID {patient.id}!")


def _handle_book_appointment(service: HospitalService) -> None:
    print("\n--- Book Doctor Appointment ---")
    doc_id = prompt_int("Enter Doctor ID", min_val=1)
    pat_id = prompt_int("Enter Patient ID", min_val=1)
    slot = safe_input("Appointment Slot (e.g. 2026-06-15 10:00): ")

    app_id = service.book_appointment(doc_id, pat_id, slot)
    print(f"\nSuccess: Appointment confirmed! ID: {app_id} for slot {slot}.")


def _handle_generate_bill(service: HospitalService) -> None:
    print("\n--- Generate Patient Invoice ---")
    pat_id = prompt_int("Enter Patient ID", min_val=1)

    room_str = safe_input("Room Charges: ")
    room_cents = parse_money_to_cents(room_str)

    doc_str = safe_input("Doctor Fees: ")
    doc_cents = parse_money_to_cents(doc_str)

    med_str = safe_input("Pharmacy / Medicine: ")
    med_cents = parse_money_to_cents(med_str)

    bill = service.generate_bill(pat_id, room_cents, doc_cents, med_cents)
    print(
        f"\nInvoice Generated! Bill ID: {bill.id} | "
        f"Total Amount: {cents_to_display(bill.total_cents)} (UNPAID)"
    )


def _handle_settle_bill(service: HospitalService) -> None:
    print("\n--- Settle Bill ---")
    bill_id = prompt_int("Enter Bill ID to pay", min_val=1)
    service.settle_bill(bill_id)
    print(f"\nSuccess: Bill ID {bill_id} marked as PAID in full.")


def _handle_discharge(service: HospitalService) -> None:
    print("\n--- Discharge Patient ---")
    pat_id = prompt_int("Enter Patient ID to discharge", min_val=1)
    if not confirm_action(f"Confirm discharge for Patient ID {pat_id}?"):
        print("Discharge cancelled.")
        return

    service.discharge_patient(pat_id)
    print(f"\nSuccess: Patient ID {pat_id} has been safely discharged (all bills settled).")


def _handle_view_appointments(service: HospitalService) -> None:
    print("\n--- Scheduled Appointments ---")
    appointments = service.list_appointments()
    headers = ["App ID", "Doctor", "Specialization", "Patient", "Slot", "Status"]
    rows = [
        [
            a.appointment_id,
            a.doctor_name,
            a.specialization,
            a.patient_name,
            a.slot_datetime,
            a.status,
        ]
        for a in appointments
    ]
    alignments = ["R", "L", "L", "L", "L", "L"]
    print(format_table(headers, rows, alignments))


def _handle_view_patients(service: HospitalService) -> None:
    print("\n--- Patients Directory ---")
    patients = service.list_patients()
    headers = ["ID", "Name", "DOB", "Phone", "Admitted", "Status"]
    rows = [[p.id, p.name, p.dob, p.phone, p.admission_date, p.status] for p in patients]
    print(format_table(headers, rows, ["R", "L", "L", "L", "L", "L"]))


def _handle_view_doctors(service: HospitalService) -> None:
    print("\n--- Doctors Directory ---")
    doctors = service.list_doctors()
    headers = ["ID", "Name", "Specialization", "Consultation Fee"]
    rows = [
        [d.id, d.name, d.specialization, cents_to_display(d.consultation_fee_cents)]
        for d in doctors
    ]
    print(format_table(headers, rows, ["R", "L", "L", "R"]))
