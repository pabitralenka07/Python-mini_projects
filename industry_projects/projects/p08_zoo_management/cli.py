"""CLI interface for Zoo Management System."""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    prompt_choice,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display
from common.tables import format_table
from projects.p08_zoo_management.models import TICKET_PRICING_CENTS, TicketType
from projects.p08_zoo_management.repository import ZooRepository
from projects.p08_zoo_management.service import (
    EnclosureCapacityExceededError,
    EnclosureNotFoundError,
    InvalidTicketSaleError,
    ZooError,
    ZooService,
)


def get_default_service() -> ZooService:
    db_path = Path(__file__).resolve().parent / "data" / "zoo.db"
    repo = ZooRepository.from_path(db_path)
    return ZooService(repo)


def display_menu() -> None:
    print("\n" + "=" * 52)
    print("             ZOO MANAGEMENT SYSTEM               ")
    print("=" * 52)
    print(" 1. View Zoo Enclosures & Occupancy")
    print(" 2. View Daily Animal Feeding Timetable")
    print(" 3. Add Animal Resident (Capacity Enforced)")
    print(" 4. Create Habitat Enclosure")
    print(" 5. Staff Keepers Management")
    print(" 6. Sell Admission Tickets")
    print(" 7. View Daily Revenue & Sales Report")
    print(" 0. Exit")
    print("=" * 52)


def view_enclosures(service: ZooService) -> None:
    enclosures = service.list_enclosures()
    if not enclosures:
        print("\nNo enclosures registered in the zoo.")
        return

    headers = ["ID", "Enclosure Name", "Habitat", "Capacity", "Occupancy", "Available"]
    rows: list[list[str]] = []
    for e in enclosures:
        rows.append(
            [
                str(e.enclosure_id),
                e.name,
                e.habitat_type,
                str(e.max_capacity),
                str(e.current_animals),
                str(e.available_capacity),
            ]
        )
    print("\n" + format_table(headers, rows))


def view_feeding_schedule(service: ZooService) -> None:
    timetable = service.get_feeding_schedule()
    if not timetable:
        print("\nNo animals registered for feeding schedule.")
        return

    headers = ["Feeding Time", "Animal Name", "Species", "Diet Category", "Enclosure"]
    rows: list[list[str]] = []
    for entry in timetable:
        rows.append(
            [
                entry.feeding_time,
                entry.animal_name,
                entry.species,
                entry.dietary_category,
                entry.enclosure_name,
            ]
        )
    print("\n" + format_table(headers, rows))


def add_animal(service: ZooService) -> None:
    try:
        view_enclosures(service)
        enc_id = prompt_int("Enter Target Enclosure ID: ")
        name = safe_input("Animal Name (e.g. Leo): ")
        species = safe_input("Species (e.g. African Lion): ")
        age = prompt_int("Age (in years): ")
        diet = prompt_choice("Dietary Category: ", ["CARNIVORE", "HERBIVORE", "OMNIVORE"])
        feed_time = safe_input("Scheduled Feeding Time (e.g. 10:30): ")

        animal = service.add_animal(name, species, age, diet, enc_id, feed_time)
        print(
            f"\n[SUCCESS] Animal '{animal.name}' ({animal.species}) admitted with ID #{animal.id}."
        )
    except (EnclosureCapacityExceededError, EnclosureNotFoundError, ZooError) as e:
        print(f"[ERROR] {e}")


def create_enclosure(service: ZooService) -> None:
    try:
        name = safe_input("Enclosure Name (e.g. Serengeti Safari): ")
        habitat = safe_input("Habitat Type (e.g. SAVANNAH, AVIARY, ARCTIC): ")
        capacity = prompt_int("Maximum Animal Capacity: ")

        enc = service.create_enclosure(name, habitat, capacity)
        print(f"[SUCCESS] Enclosure '{enc.name}' created with ID #{enc.id}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def manage_keepers(service: ZooService) -> None:
    print("\nKeeper Management:")
    print(" 1. View Staff Keepers")
    print(" 2. Register New Keeper")
    print(" 3. Assign Keeper to Enclosure")
    choice = safe_input("Select (1-3): ").strip()

    if choice == "1":
        keepers = service.list_keepers()
        if not keepers:
            print("No keepers currently registered.")
            return
        headers = ["ID", "Name", "Employee ID", "Assigned Enclosure ID"]
        rows = [
            [str(k.id), k.name, k.employee_id, str(k.assigned_enclosure_id or "Unassigned")]
            for k in keepers
        ]
        print("\n" + format_table(headers, rows))
    elif choice == "2":
        name = safe_input("Keeper Name: ")
        emp_id = safe_input("Employee ID: ")
        k = service.register_keeper(name, emp_id)
        print(f"[SUCCESS] Keeper '{k.name}' registered with ID #{k.id}.")
    elif choice == "3":
        try:
            k_id = prompt_int("Enter Keeper ID: ")
            e_id = prompt_int("Enter Enclosure ID: ")
            service.assign_keeper_to_enclosure(k_id, e_id)
            print(f"[SUCCESS] Keeper #{k_id} assigned to Enclosure #{e_id}.")
        except Exception as e:
            print(f"[ERROR] {e}")


def sell_tickets(service: ZooService) -> None:
    try:
        print("\n--- ZOO TICKET ADMISSIONS ---")
        print(f" 1. ADULT  ({cents_to_display(TICKET_PRICING_CENTS[TicketType.ADULT])})")
        print(f" 2. CHILD  ({cents_to_display(TICKET_PRICING_CENTS[TicketType.CHILD])})")
        print(f" 3. SENIOR ({cents_to_display(TICKET_PRICING_CENTS[TicketType.SENIOR])})")

        tt_choice = prompt_choice("Select Ticket Category: ", ["1", "2", "3"])
        tt_map = {"1": TicketType.ADULT, "2": TicketType.CHILD, "3": TicketType.SENIOR}
        ticket_type = tt_map[tt_choice]

        qty = prompt_int("Number of Tickets to Purchase: ")
        sale = service.sell_tickets(ticket_type, qty)

        print("\n[SUCCESS] Admission Ticket Issued!")
        print(f"Category : {sale.ticket_type}")
        print(f"Quantity : {sale.quantity}")
        print(f"Unit Fare: {cents_to_display(sale.unit_price_cents)}")
        print(f"Total Due: {cents_to_display(sale.total_cents)}")
    except (InvalidTicketSaleError, ZooError) as e:
        print(f"[ERROR] {e}")


def view_daily_report(service: ZooService) -> None:
    try:
        date_str = safe_input(
            "Enter Date for Report (YYYY-MM-DD) or press Enter for Today: "
        ).strip()
        report = service.get_daily_revenue_report(date_str or None)

        print("\n========================================")
        print(f"    ZOO ADMISSIONS REPORT: {report.sale_date}   ")
        print("========================================")
        print(f" Adult Tickets Sold  : {report.adult_tickets}")
        print(f" Child Tickets Sold  : {report.child_tickets}")
        print(f" Senior Tickets Sold : {report.senior_tickets}")
        print(f" Total Tickets Sold  : {report.total_tickets}")
        print(f" Total Revenue       : {cents_to_display(report.total_revenue_cents)}")
        print("========================================")
    except Exception as e:
        print(f"[ERROR] {e}")


def run_cli(service: ZooService | None = None) -> None:
    svc = service if service is not None else get_default_service()

    while True:
        try:
            display_menu()
            choice = safe_input("Enter choice (0-7): ").strip()
            if choice == "1":
                view_enclosures(svc)
            elif choice == "2":
                view_feeding_schedule(svc)
            elif choice == "3":
                add_animal(svc)
            elif choice == "4":
                create_enclosure(svc)
            elif choice == "5":
                manage_keepers(svc)
            elif choice == "6":
                sell_tickets(svc)
            elif choice == "7":
                view_daily_report(svc)
            elif choice == "0":
                print("Thank you for visiting the Zoo Management System!")
                break
            else:
                print("Invalid option. Please choose between 0 and 7.")
        except UserExitException:
            print("\nSession terminated. Goodbye!")
            break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    run_cli()
