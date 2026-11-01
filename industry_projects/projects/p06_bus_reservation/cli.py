"""CLI interface for Bus Reservation System."""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display, parse_money_to_cents
from common.tables import format_table
from projects.p06_bus_reservation.repository import BusRepository
from projects.p06_bus_reservation.service import (
    BookingAlreadyCancelledError,
    BookingNotFoundError,
    BusError,
    BusService,
    InvalidSeatError,
    ScheduleNotFoundError,
    SeatAlreadyBookedError,
)


def get_default_service() -> BusService:
    db_path = Path(__file__).resolve().parent / "data" / "bus_reservation.db"
    repo = BusRepository.from_path(db_path)
    return BusService(repo)


def display_menu() -> None:
    print("\n" + "=" * 50)
    print("           BUS RESERVATION SYSTEM                 ")
    print("=" * 50)
    print(" 1. View Available Schedules & Fares")
    print(" 2. View Visual Seat Layout")
    print(" 3. Book a Seat")
    print(" 4. Cancel Booking & Claim Refund")
    print(" 5. View / Save Ticket Receipt")
    print(" 6. Register New Bus (Fleet Admin)")
    print(" 7. Add Route (Fleet Admin)")
    print(" 8. Schedule Trip (Fleet Admin)")
    print(" 0. Exit")
    print("=" * 50)


def view_schedules(service: BusService) -> None:
    schedules = service.list_schedules()
    if not schedules:
        print("\nNo bus trips currently scheduled.")
        return

    headers = [
        "Sch ID",
        "Bus",
        "Type",
        "Route",
        "Departure",
        "Arrival",
        "Fare",
        "Available",
    ]
    rows: list[list[str]] = []
    for s in schedules:
        rows.append(
            [
                str(s.schedule_id),
                s.bus_number,
                s.bus_type,
                f"{s.origin} -> {s.destination}",
                s.departure_time,
                s.arrival_time,
                cents_to_display(s.fare_cents),
                f"{s.available_seats} / {s.total_seats}",
            ]
        )
    print("\n" + format_table(headers, rows))


def view_seat_map(service: BusService) -> None:
    try:
        sch_id = prompt_int("Enter Schedule ID: ")
        layout = service.get_seat_layout(sch_id)
        print("\n" + layout)
    except (ScheduleNotFoundError, BusError) as e:
        print(f"[ERROR] {e}")


def book_seat(service: BusService) -> None:
    try:
        sch_id = prompt_int("Enter Schedule ID: ")
        layout = service.get_seat_layout(sch_id)
        print("\n" + layout)

        name = safe_input("Passenger Full Name: ")
        phone = safe_input("Passenger Phone Number: ")
        seat_num = prompt_int("Desired Seat Number: ")

        booking = service.book_seat(sch_id, name, phone, seat_num)
        print(f"\n[SUCCESS] Seat #{seat_num} reserved successfully!")
        print(f"Booking Reference ID: #{booking.id}")
        print(f"Fare Charged: {cents_to_display(booking.fare_paid_cents)}")

        if confirm_action("Would you like to print/save your ticket receipt?"):
            receipt = service.get_ticket_receipt(booking.id or 0)
            print("\n" + service.format_ticket(receipt))

            if confirm_action("Save a copy to local text file?"):
                tickets_dir = Path(__file__).resolve().parent / "data" / "tickets"
                saved_path = service.save_ticket_to_file(receipt, tickets_dir)
                print(f"[SAVED] Ticket receipt saved to: {saved_path}")

    except (InvalidSeatError, SeatAlreadyBookedError, ScheduleNotFoundError, BusError) as e:
        print(f"[ERROR] {e}")


def cancel_booking(service: BusService) -> None:
    try:
        booking_id = prompt_int("Enter Booking ID to Cancel: ")
        if not confirm_action(f"Are you sure you want to cancel Booking #{booking_id}?"):
            print("Cancellation aborted.")
            return

        refund = service.cancel_booking(booking_id)
        print(f"\n[SUCCESS] Booking #{booking_id} has been cancelled.")
        print(f"Refund Processed: {cents_to_display(refund)}")
    except (BookingNotFoundError, BookingAlreadyCancelledError, BusError) as e:
        print(f"[ERROR] {e}")


def view_ticket(service: BusService) -> None:
    try:
        booking_id = prompt_int("Enter Booking ID: ")
        receipt = service.get_ticket_receipt(booking_id)
        print("\n" + service.format_ticket(receipt))

        if confirm_action("Save a copy to local text file?"):
            tickets_dir = Path(__file__).resolve().parent / "data" / "tickets"
            saved_path = service.save_ticket_to_file(receipt, tickets_dir)
            print(f"[SAVED] Ticket receipt saved to: {saved_path}")
    except (BookingNotFoundError, BusError) as e:
        print(f"[ERROR] {e}")


def register_bus(service: BusService) -> None:
    try:
        bus_no = safe_input("Enter Bus Number (e.g. BUS-101): ")
        bus_type = safe_input("Enter Bus Type (e.g. AC_SLEEPER, EXPRESS): ")
        capacity = prompt_int("Enter Total Seat Capacity: ")
        bus = service.register_bus(bus_no, bus_type, capacity)
        print(f"[SUCCESS] Bus '{bus.bus_number}' registered with ID #{bus.id}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def add_route(service: BusService) -> None:
    try:
        origin = safe_input("Enter Origin City: ")
        destination = safe_input("Enter Destination City: ")
        dist_str = safe_input("Enter Distance in km (e.g. 350.5): ")
        dist = float(dist_str)
        route = service.add_route(origin, destination, dist)
        print(f"[SUCCESS] Route {route.origin} -> {route.destination} added with ID #{route.id}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def schedule_trip(service: BusService) -> None:
    try:
        bus_id = prompt_int("Enter Bus ID: ")
        route_id = prompt_int("Enter Route ID: ")
        dep = safe_input("Enter Departure (YYYY-MM-DDTHH:MM:SS): ")
        arr = safe_input("Enter Arrival (YYYY-MM-DDTHH:MM:SS): ")
        fare_dollars = safe_input("Enter Fare ($): ")
        fare_cents = parse_money_to_cents(fare_dollars)

        sch = service.schedule_trip(bus_id, route_id, dep, arr, fare_cents)
        print(f"[SUCCESS] Trip scheduled with ID #{sch.id}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def run_cli(service: BusService | None = None) -> None:
    svc = service if service is not None else get_default_service()

    while True:
        try:
            display_menu()
            choice = safe_input("Enter choice (0-8): ").strip()
            if choice == "1":
                view_schedules(svc)
            elif choice == "2":
                view_seat_map(svc)
            elif choice == "3":
                book_seat(svc)
            elif choice == "4":
                cancel_booking(svc)
            elif choice == "5":
                view_ticket(svc)
            elif choice == "6":
                register_bus(svc)
            elif choice == "7":
                add_route(svc)
            elif choice == "8":
                schedule_trip(svc)
            elif choice == "0":
                print("Thank you for using Bus Reservation System. Safe travels!")
                break
            else:
                print("Invalid option. Please select 0 through 8.")
        except UserExitException:
            print("\nSession terminated. Goodbye!")
            break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    run_cli()
