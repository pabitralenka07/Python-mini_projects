"""CLI interface for Airport Management System."""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    prompt_int,
    safe_input,
)
from common.tables import format_table
from projects.p07_airport_management.repository import AirportRepository
from projects.p07_airport_management.service import (
    AirportError,
    AirportService,
    CheckInNotAllowedError,
    FlightNotFoundError,
    GateConflictError,
    InvalidFlightStatusTransitionError,
    SeatAlreadyAssignedError,
)


def get_default_service() -> AirportService:
    db_path = Path(__file__).resolve().parent / "data" / "airport.db"
    repo = AirportRepository.from_path(db_path)
    return AirportService(repo)


def display_menu() -> None:
    print("\n" + "=" * 52)
    print("           AIRPORT MANAGEMENT SYSTEM             ")
    print("=" * 52)
    print(" 1. View Airport Flight Board (Departures)")
    print(" 2. Passenger Check-In & Seat Assignment")
    print(" 3. Assign Gate to Flight (Overlap Detection)")
    print(" 4. Update Flight Status (State Machine)")
    print(" 5. Schedule New Commercial Flight")
    print(" 6. Register Boarding Gate")
    print(" 7. Register Ticketed Passenger")
    print(" 0. Exit")
    print("=" * 52)


def view_board(service: AirportService) -> None:
    entries = service.get_departure_board()
    if not entries:
        print("\nNo flights scheduled on the departure board.")
        return

    headers = ["Flight", "Airline", "Destination", "Departure", "Gate", "Status"]
    rows: list[list[str]] = []
    for e in entries:
        rows.append(
            [
                e.flight_number,
                e.airline,
                e.destination,
                e.departure_time,
                e.gate,
                e.status,
            ]
        )
    print("\n" + format_table(headers, rows))


def passenger_check_in(service: AirportService) -> None:
    try:
        flight_no = safe_input("Enter Flight Number (e.g. AA-101): ")
        flight = service.get_flight_by_number(flight_no)
        passport = safe_input("Enter Passenger Passport Number: ").strip().upper()

        passenger = service.repo.get_passenger_by_passport(flight.id or 0, passport)
        if not passenger:
            print(
                f"[ERROR] No ticketed passenger found with passport '{passport}' "
                f"on flight {flight.flight_number}."
            )
            return

        if passenger.checked_in:
            print(
                f"[INFO] Passenger {passenger.full_name} is already checked in "
                f"to seat {passenger.seat_number}."
            )
            return

        seat_no = safe_input("Enter Desired Seat (e.g. 14B, 22C): ")
        service.check_in(passenger.id or 0, seat_no)
        print("\n[SUCCESS] Boarding Pass Issued!")
        print(f"Passenger : {passenger.full_name}")
        print(f"Flight    : {flight.flight_number} -> {flight.destination}")
        print(f"Seat      : {seat_no.upper()}")
        print(f"Departure : {flight.departure_time}")
    except (CheckInNotAllowedError, SeatAlreadyAssignedError, AirportError) as e:
        print(f"[ERROR] {e}")


def assign_gate(service: AirportService) -> None:
    try:
        flight_id = prompt_int("Enter Flight ID: ")
        gates = service.list_gates()
        if not gates:
            print("[ERROR] No gates registered in airport.")
            return

        print("\nAvailable Gates:")
        for g in gates:
            print(f"  ID #{g.id} -> Gate {g.gate_number} ({g.terminal})")

        gate_id = prompt_int("Enter Gate ID to assign: ")
        service.assign_gate(flight_id, gate_id)
        print(f"[SUCCESS] Gate ID #{gate_id} successfully assigned to Flight #{flight_id}.")
    except (GateConflictError, FlightNotFoundError, AirportError) as e:
        print(f"[ERROR] {e}")


def update_flight_status(service: AirportService) -> None:
    try:
        flight_id = prompt_int("Enter Flight ID: ")
        flight = service.get_flight(flight_id)
        print(f"Current Status of {flight.flight_number}: {flight.status}")
        new_status = safe_input("Enter Target Status (BOARDING, DEPARTED, DELAYED, CANCELLED): ")
        service.update_flight_status(flight_id, new_status)
        print(f"[SUCCESS] Flight {flight.flight_number} updated to {new_status.upper()}.")
    except (InvalidFlightStatusTransitionError, FlightNotFoundError, AirportError) as e:
        print(f"[ERROR] {e}")


def schedule_flight(service: AirportService) -> None:
    try:
        fl_no = safe_input("Flight Number (e.g. UA-404): ")
        airline = safe_input("Airline (e.g. United): ")
        orig = safe_input("Origin (e.g. JFK): ")
        dest = safe_input("Destination (e.g. LAX): ")
        dep = safe_input("Departure Time (YYYY-MM-DDTHH:MM:SS): ")
        arr = safe_input("Arrival Time (YYYY-MM-DDTHH:MM:SS): ")

        fl = service.schedule_flight(fl_no, airline, orig, dest, dep, arr)
        print(f"[SUCCESS] Flight '{fl.flight_number}' scheduled with ID #{fl.id}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def register_gate(service: AirportService) -> None:
    try:
        gate_no = safe_input("Gate Number (e.g. B12): ")
        terminal = safe_input("Terminal (e.g. Terminal 2): ")
        gate = service.register_gate(gate_no, terminal)
        print(f"[SUCCESS] Gate '{gate.gate_number}' registered with ID #{gate.id}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def register_passenger(service: AirportService) -> None:
    try:
        fl_no = safe_input("Enter Flight Number: ")
        flight = service.get_flight_by_number(fl_no)
        name = safe_input("Passenger Full Name: ")
        passport = safe_input("Passport Number: ")
        passenger = service.register_passenger(name, passport, flight.id or 0)
        print(f"[SUCCESS] Ticket registered for {passenger.full_name} on {flight.flight_number}.")
    except Exception as e:
        print(f"[ERROR] {e}")


def run_cli(service: AirportService | None = None) -> None:
    svc = service if service is not None else get_default_service()

    while True:
        try:
            display_menu()
            choice = safe_input("Enter choice (0-7): ").strip()
            if choice == "1":
                view_board(svc)
            elif choice == "2":
                passenger_check_in(svc)
            elif choice == "3":
                assign_gate(svc)
            elif choice == "4":
                update_flight_status(svc)
            elif choice == "5":
                schedule_flight(svc)
            elif choice == "6":
                register_gate(svc)
            elif choice == "7":
                register_passenger(svc)
            elif choice == "0":
                print("Thank you for using Airport Management System. Clear skies!")
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
