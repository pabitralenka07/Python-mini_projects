"""Seed script for Airport Management System with gates, flights, and passengers."""

from pathlib import Path

from projects.p07_airport_management.models import FlightStatus
from projects.p07_airport_management.repository import AirportRepository
from projects.p07_airport_management.service import (
    AirportService,
    SeatAlreadyAssignedError,
)


def seed_data(repo: AirportRepository | None = None) -> None:
    if repo is None:
        db_path = Path(__file__).resolve().parent / "data" / "airport.db"
        repo = AirportRepository.from_path(db_path)

    service = AirportService(repo)
    print("Seeding Airport Management System...")

    # 1. Gates
    gates = service.list_gates()
    gate_map: dict[str, int] = {g.gate_number: g.id for g in gates if g.id is not None}
    if not gate_map:
        g1 = service.register_gate("A1", "Terminal 1")
        g2 = service.register_gate("A2", "Terminal 1")
        g3 = service.register_gate("B1", "Terminal 2")
        if g1.id and g2.id and g3.id:
            gate_map["A1"] = g1.id
            gate_map["A2"] = g2.id
            gate_map["B1"] = g3.id
        print(" -> Added gates A1, A2, and B1.")
    else:
        print(f" -> Gates already exist ({len(gate_map)} found).")

    # 2. Flights
    f1 = repo.get_flight_by_number("AA-101")
    f2 = repo.get_flight_by_number("DL-202")
    f3 = repo.get_flight_by_number("UA-303")

    if not f1:
        f1 = service.schedule_flight(
            flight_number="AA-101",
            airline="American Airlines",
            origin="JFK",
            destination="LHR (London Heathrow)",
            departure_time="2026-11-20T10:00:00",
            arrival_time="2026-11-20T22:00:00",
            gate_id=gate_map.get("A1"),
        )
        service.update_flight_status(f1.id or 0, FlightStatus.BOARDING)
        print(" -> Added flight AA-101 (London Heathrow) at Gate A1 [BOARDING].")

    if not f2:
        f2 = service.schedule_flight(
            flight_number="DL-202",
            airline="Delta Airlines",
            origin="JFK",
            destination="CDG (Paris Charles de Gaulle)",
            departure_time="2026-11-20T14:30:00",
            arrival_time="2026-11-21T03:00:00",
            gate_id=gate_map.get("A1"),
        )
        print(" -> Added flight DL-202 (Paris) at Gate A1 [SCHEDULED].")

    if not f3:
        f3 = service.schedule_flight(
            flight_number="UA-303",
            airline="United Airlines",
            origin="JFK",
            destination="SFO (San Francisco)",
            departure_time="2026-11-20T11:15:00",
            arrival_time="2026-11-20T14:45:00",
            gate_id=gate_map.get("B1"),
        )
        print(" -> Added flight UA-303 (San Francisco) at Gate B1 [SCHEDULED].")

    # 3. Passengers
    if f1 and f1.id:
        p1 = repo.get_passenger_by_passport(f1.id, "USA-998811")
        if not p1:
            p1 = service.register_passenger("Eleanor Vance", "USA-998811", f1.id)
            try:
                service.check_in(p1.id or 0, "12A")
                print(" -> Checked in Eleanor Vance to seat 12A on AA-101.")
            except SeatAlreadyAssignedError:
                pass

        p2 = repo.get_passenger_by_passport(f1.id, "USA-998822")
        if not p2:
            p2 = service.register_passenger("Luke Sanderson", "USA-998822", f1.id)
            try:
                service.check_in(p2.id or 0, "12B")
                print(" -> Checked in Luke Sanderson to seat 12B on AA-101.")
            except SeatAlreadyAssignedError:
                pass

    if f2 and f2.id:
        p3 = repo.get_passenger_by_passport(f2.id, "USA-774433")
        if not p3:
            service.register_passenger("Theodora Crain", "USA-774433", f2.id)
            print(" -> Registered ticketed passenger Theodora Crain on DL-202.")

    print("Airport Management System seeding complete.")


if __name__ == "__main__":
    seed_data()
