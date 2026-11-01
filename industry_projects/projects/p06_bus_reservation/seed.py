"""Seed script for Bus Reservation System with fleet, routes, and sample trips."""

from pathlib import Path

from projects.p06_bus_reservation.repository import BusRepository
from projects.p06_bus_reservation.service import (
    BusService,
    SeatAlreadyBookedError,
)


def seed_data(repo: BusRepository | None = None) -> None:
    if repo is None:
        db_path = Path(__file__).resolve().parent / "data" / "bus_reservation.db"
        repo = BusRepository.from_path(db_path)

    service = BusService(repo)
    print("Seeding Bus Reservation System...")

    # 1. Buses
    buses = repo.list_buses()
    bus_map: dict[str, int] = {b.bus_number: b.id for b in buses if b.id is not None}
    if not bus_map:
        b1 = service.register_bus("BUS-101", "AC_SLEEPER", 20)
        b2 = service.register_bus("BUS-202", "EXPRESS_SEATER", 32)
        if b1.id and b2.id:
            bus_map["BUS-101"] = b1.id
            bus_map["BUS-202"] = b2.id
        print(" -> Added buses BUS-101 and BUS-202.")
    else:
        print(f" -> Buses already exist ({len(bus_map)} found).")

    # 2. Routes
    routes = repo.list_routes()
    route_map: dict[str, int] = {
        f"{r.origin}->{r.destination}": r.id for r in routes if r.id is not None
    }
    if not route_map:
        r1 = service.add_route("New York", "Boston", 350.0)
        r2 = service.add_route("New York", "Washington DC", 365.0)
        if r1.id and r2.id:
            route_map["New York->Boston"] = r1.id
            route_map["New York->Washington DC"] = r2.id
        print(" -> Added routes NYC->Boston and NYC->DC.")
    else:
        print(f" -> Routes already exist ({len(route_map)} found).")

    # 3. Schedules
    schedules = service.list_schedules()
    sch_ids: list[int] = [s.schedule_id for s in schedules]
    if not schedules and "BUS-101" in bus_map and "New York->Boston" in route_map:
        s1 = service.schedule_trip(
            bus_id=bus_map["BUS-101"],
            route_id=route_map["New York->Boston"],
            departure_time="2026-11-15T08:00:00",
            arrival_time="2026-11-15T12:30:00",
            fare_cents=4500,
        )
        s2 = service.schedule_trip(
            bus_id=bus_map["BUS-202"],
            route_id=route_map["New York->Washington DC"],
            departure_time="2026-11-15T14:00:00",
            arrival_time="2026-11-15T18:45:00",
            fare_cents=5500,
        )
        if s1.id and s2.id:
            sch_ids = [s1.id, s2.id]
        print(" -> Added sample trips for NYC->Boston and NYC->DC.")
    else:
        print(f" -> Schedules already exist ({len(schedules)} found).")

    # 4. Bookings
    if sch_ids:
        try:
            service.book_seat(sch_ids[0], "Alice Cooper", "555-0111", 1)
            service.book_seat(sch_ids[0], "Bob Dylan", "555-0122", 2)
            print(" -> Booked seats 1 & 2 on trip 1.")
        except SeatAlreadyBookedError:
            pass

        if len(sch_ids) > 1:
            try:
                service.book_seat(sch_ids[1], "Charlie Parker", "555-0133", 5)
                print(" -> Booked seat 5 on trip 2.")
            except SeatAlreadyBookedError:
                pass

    print("Bus Reservation System seeding complete.")


if __name__ == "__main__":
    seed_data()
