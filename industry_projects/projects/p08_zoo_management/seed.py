"""Seed script for Zoo Management System with habitats, animals, keepers, and ticket sales."""

from pathlib import Path

from projects.p08_zoo_management.models import TicketType
from projects.p08_zoo_management.repository import ZooRepository
from projects.p08_zoo_management.service import (
    EnclosureCapacityExceededError,
    ZooService,
)


def seed_data(repo: ZooRepository | None = None) -> None:
    if repo is None:
        db_path = Path(__file__).resolve().parent / "data" / "zoo.db"
        repo = ZooRepository.from_path(db_path)

    service = ZooService(repo)
    print("Seeding Zoo Management System...")

    e1 = repo.get_enclosure_by_name("Savannah Plains")
    e2 = repo.get_enclosure_by_name("Tropical Aviary")
    e3 = repo.get_enclosure_by_name("Arctic Tundra")

    if not e1:
        e1 = service.create_enclosure("Savannah Plains", "SAVANNAH", 4)
        print(" -> Created enclosure: Savannah Plains (Capacity: 4)")
    if not e2:
        e2 = service.create_enclosure("Tropical Aviary", "AVIARY", 6)
        print(" -> Created enclosure: Tropical Aviary (Capacity: 6)")
    if not e3:
        e3 = service.create_enclosure("Arctic Tundra", "ARCTIC", 2)
        print(" -> Created enclosure: Arctic Tundra (Capacity: 2)")

    keepers = service.list_keepers()
    if not keepers:
        service.register_keeper("Jane Goodall", "EMP-001", e1.id)
        service.register_keeper("Steve Irwin", "EMP-002", e2.id)
        print(" -> Registered staff keepers: Jane Goodall and Steve Irwin.")
    else:
        print(f" -> Keepers already exist ({len(keepers)} found).")

    timetable = service.get_feeding_schedule()
    if not timetable and e1 and e2 and e3 and e1.id and e2.id and e3.id:
        try:
            service.add_animal("Simba", "African Lion", 5, "CARNIVORE", e1.id, "11:00")
            service.add_animal("Rafiki", "Olive Baboon", 8, "OMNIVORE", e1.id, "09:30")
            service.add_animal("Polly", "Scarlet Macaw", 3, "HERBIVORE", e2.id, "08:30")
            service.add_animal("Nanook", "Polar Bear", 6, "CARNIVORE", e3.id, "14:00")
            print(" -> Added 4 resident animals: Simba, Rafiki, Polly, and Nanook.")
        except EnclosureCapacityExceededError:
            pass
    else:
        print(f" -> Animals already exist ({len(timetable)} found).")

    today_report = service.get_daily_revenue_report()
    if today_report.total_tickets == 0:
        service.sell_tickets(TicketType.ADULT, 3)
        service.sell_tickets(TicketType.CHILD, 2)
        service.sell_tickets(TicketType.SENIOR, 1)
        print(" -> Recorded sample ticket sales: 3 Adult, 2 Child, 1 Senior.")
    else:
        print(f" -> Ticket sales already recorded ({today_report.total_tickets} tickets found).")

    print("Zoo Management System seeding complete.")


if __name__ == "__main__":
    seed_data()
