"""CLI interface for Electricity Bill Management System."""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_choice,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display
from common.tables import format_table
from projects.p09_electricity_bill.repository import ElectricityRepository
from projects.p09_electricity_bill.service import (
    BillAlreadyPaidError,
    BillNotFoundError,
    ConsumerNotFoundError,
    ElectricityError,
    ElectricityService,
    NonMonotonicReadingError,
)


def get_default_service() -> ElectricityService:
    db_path = Path(__file__).resolve().parent / "data" / "electricity.db"
    repo = ElectricityRepository.from_path(db_path)
    return ElectricityService(repo)


def display_menu() -> None:
    print("\n" + "=" * 54)
    print("        ELECTRICITY BILL MANAGEMENT SYSTEM            ")
    print("=" * 54)
    print(" 1. View Consumer Accounts")
    print(" 2. Register New Consumer Account")
    print(" 3. Enter Meter Reading & Generate Bill")
    print(" 4. View Itemized Bill Breakdown")
    print(" 5. Settle (Pay) Utility Bill")
    print(" 6. View All Invoices (Bill History)")
    print(" 0. Exit")
    print("=" * 54)


def view_consumers(service: ElectricityService) -> None:
    consumers = service.list_consumers()
    if not consumers:
        print("\nNo consumers registered.")
        return

    headers = ["ID", "Consumer #", "Full Name", "Meter #", "Tariff Category", "Address"]
    rows: list[list[str]] = []
    for c in consumers:
        rows.append(
            [
                str(c.id),
                c.consumer_number,
                c.name,
                c.meter_number,
                c.tariff_category,
                c.address,
            ]
        )
    print("\n" + format_table(headers, rows))


def register_consumer(service: ElectricityService) -> None:
    try:
        c_num = safe_input("Consumer Number (e.g. CON-1001): ")
        name = safe_input("Full Name: ")
        addr = safe_input("Service Address: ")
        m_num = safe_input("Meter Number (e.g. MTR-5001): ")
        cat = prompt_choice("Tariff Category: ", ["RESIDENTIAL", "COMMERCIAL"])
        init_reading = prompt_int("Initial Meter Reading (kWh, e.g. 0): ")

        c = service.register_consumer(c_num, name, addr, m_num, cat, init_reading)
        print(f"\n[SUCCESS] Consumer account '{c.consumer_number}' registered for {c.name}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def generate_bill(service: ElectricityService) -> None:
    try:
        c_num = safe_input("Enter Consumer Number: ")
        consumer = service.get_consumer_by_number(c_num)
        if not consumer or consumer.id is None:
            return

        latest = service.repo.get_latest_meter_reading(consumer.id)
        prev_val = latest.reading_value if latest else 0
        print(f"Previous Recorded Meter Reading: {prev_val} kWh")

        current_val = prompt_int("Enter Current Meter Reading (kWh): ")
        bill = service.generate_bill(consumer.id, current_val)

        print("\n[SUCCESS] Invoice Generated Successfully!")
        print(f"Invoice Number : {bill.bill_number}")
        print(f"Units Consumed : {bill.units_consumed} kWh")
        print(f"Energy Charge  : {cents_to_display(bill.energy_charge_cents)}")
        print(f"Fixed Charge   : {cents_to_display(bill.fixed_charge_cents)}")
        print(f"Utility Tax    : {cents_to_display(bill.tax_cents)}")
        print(f"Total Amount   : {cents_to_display(bill.total_cents)}")
        print(f"Due Date       : {bill.due_date}")
    except (NonMonotonicReadingError, ConsumerNotFoundError, ElectricityError) as e:
        print(f"[ERROR] {e}")


def view_bill_breakdown(service: ElectricityService) -> None:
    try:
        bill_id = prompt_int("Enter Bill ID: ")
        detail = service.get_bill_detail(bill_id)

        print("\n" + "=" * 54)
        print("           ITEMIZED ELECTRICITY INVOICE               ")
        print("=" * 54)
        print(f" Invoice #        : {detail.bill_number} [{detail.status}]")
        print(f" Consumer         : {detail.consumer_name} ({detail.consumer_number})")
        print(f" Meter Number     : {detail.meter_number}")
        print(f" Tariff Category  : {detail.tariff_category}")
        print(f" Previous Reading : {detail.previous_reading} kWh")
        print(f" Current Reading  : {detail.current_reading} kWh")
        print(f" Total Units      : {detail.units_consumed} kWh")
        print("-" * 54)
        print(" Tiered Slab Breakdown:")
        for s in detail.slabs:
            rate_str = cents_to_display(s.rate_per_unit_cents)
            amt_str = cents_to_display(s.amount_cents)
            print(
                f"   * {s.slab_label:<16} : {s.units_in_slab:>3} kWh @ {rate_str}/kWh = {amt_str}"
            )
        print("-" * 54)
        print(f" Energy Charges   : {cents_to_display(detail.energy_charge_cents)}")
        print(f" Fixed Charges    : {cents_to_display(detail.fixed_charge_cents)}")
        print(f" Utility Tax (5%) : {cents_to_display(detail.tax_cents)}")
        print(f" TOTAL DUE        : {cents_to_display(detail.total_cents)}")
        print(f" Due Date         : {detail.due_date}")
        if detail.paid_at:
            print(f" Paid At          : {detail.paid_at}")
        print("=" * 54)
    except (BillNotFoundError, ElectricityError) as e:
        print(f"[ERROR] {e}")


def pay_bill(service: ElectricityService) -> None:
    try:
        bill_id = prompt_int("Enter Bill ID to Pay: ")
        detail = service.get_bill_detail(bill_id)
        if detail.status == "PAID":
            print(f"[INFO] Bill #{detail.bill_number} is already paid.")
            return

        print(f"Invoice : #{detail.bill_number}")
        print(f"Consumer: {detail.consumer_name}")
        print(f"Amount  : {cents_to_display(detail.total_cents)}")

        if not confirm_action("Confirm payment settlement?"):
            print("Payment cancelled.")
            return

        service.pay_bill(bill_id)
        print(f"\n[SUCCESS] Payment settled for Bill #{detail.bill_number}!")
    except (BillNotFoundError, BillAlreadyPaidError, ElectricityError) as e:
        print(f"[ERROR] {e}")


def list_bills(service: ElectricityService) -> None:
    bills = service.list_all_bills()
    if not bills:
        print("\nNo bills recorded in system.")
        return

    headers = ["ID", "Bill #", "Consumer", "Units", "Total Due", "Due Date", "Status"]
    rows: list[list[str]] = []
    for b in bills:
        rows.append(
            [
                str(b.bill_id),
                b.bill_number,
                b.consumer_name,
                f"{b.units_consumed} kWh",
                cents_to_display(b.total_cents),
                b.due_date,
                b.status,
            ]
        )
    print("\n" + format_table(headers, rows))


def run_cli(service: ElectricityService | None = None) -> None:
    svc = service if service is not None else get_default_service()

    while True:
        try:
            display_menu()
            choice = safe_input("Enter choice (0-6): ").strip()
            if choice == "1":
                view_consumers(svc)
            elif choice == "2":
                register_consumer(svc)
            elif choice == "3":
                generate_bill(svc)
            elif choice == "4":
                view_bill_breakdown(svc)
            elif choice == "5":
                pay_bill(svc)
            elif choice == "6":
                list_bills(svc)
            elif choice == "0":
                print("Thank you for using Electricity Bill Management System.")
                break
            else:
                print("Invalid option. Please choose between 0 and 6.")
        except UserExitException:
            print("\nSession terminated. Goodbye!")
            break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    run_cli()
