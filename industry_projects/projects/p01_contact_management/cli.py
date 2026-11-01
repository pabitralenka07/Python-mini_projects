"""CLI interface for Contact Management System.

================================================================================
Concepts used:
1. Input Sanitization & Formula Escaping: CSV cells starting with '=', '+', '-',
   or '@' are neutralized to prevent spreadsheet injection vulnerabilities.
2. Safe Confirmation Prompts: Critical actions (delete) require explicit 'y' or
   'yes'; EOF or any other response defaults strictly to aborting the operation.
3. Layered Presentation: CLI formats database outputs into aligned text tables
   without directly touching SQL queries.
================================================================================
"""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_int,
    safe_input,
)
from common.tables import format_table
from projects.p01_contact_management.repository import ContactRepository
from projects.p01_contact_management.service import (
    ContactError,
    ContactService,
)


def get_default_service() -> ContactService:
    db_path = Path(__file__).resolve().parent / "data" / "contacts.db"
    repo = ContactRepository.from_path(db_path)
    return ContactService(repo)


def display_menu() -> None:
    print("\n" + "=" * 45)
    print("      CONTACT MANAGEMENT SYSTEM      ")
    print("=" * 45)
    print(" 1. Add New Contact")
    print(" 2. Search Contacts")
    print(" 3. List All Contacts")
    print(" 4. Edit Contact")
    print(" 5. Delete Contact")
    print(" 6. Import Contacts from CSV")
    print(" 7. Export Contacts to CSV")
    print(" 0. Exit")
    print("=" * 45)


def run_cli(service: ContactService | None = None) -> None:
    if service is None:
        service = get_default_service()

    while True:
        try:
            display_menu()
            choice = prompt_int("Enter option (0-7)", min_val=0, max_val=7)
        except UserExitException:
            print("\nGoodbye! Exiting Contact Management System.")
            break

        if choice == 0:
            print("\nGoodbye! Exiting Contact Management System.")
            break

        try:
            if choice == 1:
                _handle_add(service)
            elif choice == 2:
                _handle_search(service)
            elif choice == 3:
                _handle_list(service)
            elif choice == 4:
                _handle_edit(service)
            elif choice == 5:
                _handle_delete(service)
            elif choice == 6:
                _handle_import(service)
            elif choice == 7:
                _handle_export(service)
        except UserExitException:
            print("\nReturning to main menu...")
        except ContactError as err:
            print(f"\n[Error] {err}")
        except Exception as err:
            print(f"\n[Unexpected Error] {err}")


def _handle_add(service: ContactService) -> None:
    print("\n--- Add New Contact ---")
    name = safe_input("Enter Full Name: ")
    phone = safe_input("Enter Phone Number: ")
    email = safe_input("Enter Email: ")
    address = safe_input("Enter Address (optional): ", allow_empty=True)

    contact = service.add_contact(name=name, phone=phone, email=email, address=address)
    print(f"\nSuccess: Contact '{contact.name}' created with ID {contact.id}!")


def _handle_search(service: ContactService) -> None:
    print("\n--- Search Contacts ---")
    query = safe_input("Search term (Name, Phone, or Email): ")
    results = service.search_contacts(query)

    headers = ["ID", "Name", "Phone", "Email", "Address"]
    rows = [[c.id, c.name, c.phone, c.email, c.address] for c in results]
    alignments = ["R", "L", "L", "L", "L"]
    print(format_table(headers, rows, alignments))


def _handle_list(service: ContactService) -> None:
    print("\n--- All Contacts ---")
    contacts = service.list_contacts()
    headers = ["ID", "Name", "Phone", "Email", "Address"]
    rows = [[c.id, c.name, c.phone, c.email, c.address] for c in contacts]
    alignments = ["R", "L", "L", "L", "L"]
    print(format_table(headers, rows, alignments))


def _handle_edit(service: ContactService) -> None:
    print("\n--- Edit Contact ---")
    contact_id = prompt_int("Enter Contact ID to edit", min_val=1)
    name = safe_input("Enter New Name: ")
    phone = safe_input("Enter New Phone: ")
    email = safe_input("Enter New Email: ")
    address = safe_input("Enter New Address (optional): ", allow_empty=True)

    updated = service.edit_contact(
        contact_id=contact_id, name=name, phone=phone, email=email, address=address
    )
    print(f"\nSuccess: Contact ID {updated.id} updated!")


def _handle_delete(service: ContactService) -> None:
    print("\n--- Delete Contact ---")
    contact_id = prompt_int("Enter Contact ID to delete", min_val=1)
    if not confirm_action(f"Are you sure you want to permanently delete Contact ID {contact_id}?"):
        print("Deletion cancelled.")
        return

    service.delete_contact(contact_id)
    print(f"\nSuccess: Contact ID {contact_id} deleted successfully.")


def _handle_import(service: ContactService) -> None:
    print("\n--- Import Contacts from CSV ---")
    file_path = safe_input("Enter CSV file path: ")
    imported, skipped, errors = service.import_csv(file_path)
    print(f"\nImport Result: {imported} imported successfully, {skipped} skipped.")
    if errors:
        print("Skipped details:")
        for e in errors[:5]:
            print(f"  - {e}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more.")


def _handle_export(service: ContactService) -> None:
    print("\n--- Export Contacts to CSV ---")
    file_path = safe_input("Enter destination CSV path (e.g., data/contacts_export.csv): ")
    count = service.export_csv(file_path)
    print(f"\nSuccess: Exported {count} contacts to '{file_path}' (formula-safe).")
