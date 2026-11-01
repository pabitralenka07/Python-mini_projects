"""8. Zoo Management System - enclosures, animals, staff, ticket sales."""
from tkinter import ttk

from common import AppError, CrudFrame, Database, Field, launch, options, refresh_on_tab_change

SCHEMA = """
CREATE TABLE IF NOT EXISTS enclosures(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, habitat TEXT NOT NULL,
    capacity INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS animals(id INTEGER PRIMARY KEY, name TEXT NOT NULL, species TEXT NOT NULL, age INTEGER,
    enclosure_id INTEGER NOT NULL REFERENCES enclosures(id), health TEXT NOT NULL DEFAULT 'Healthy', diet TEXT);
CREATE TABLE IF NOT EXISTS staff(id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, phone TEXT,
    enclosure_id INTEGER REFERENCES enclosures(id));
CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY, visitor TEXT NOT NULL, adults INTEGER NOT NULL,
    children INTEGER NOT NULL, visit_date TEXT NOT NULL, total REAL NOT NULL);
"""
ADULT_PRICE, CHILD_PRICE = 100.0, 50.0


class App:
    def __init__(self, root):
        self.db = Database("zoo.db", SCHEMA)
        enc = options(self.db, "SELECT id, name FROM enclosures")
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.enclosures = CrudFrame(nb, self.db, "enclosures", [
            Field("name"), Field("habitat", kind="choice", choices=["Savannah", "Forest", "Aquatic", "Aviary", "Reptile house"]),
            Field("capacity", kind="int")],
            list_sql="SELECT id, name, habitat, capacity, (SELECT COUNT(*) FROM animals WHERE enclosure_id=enclosures.id) "
                     "AS occupants FROM enclosures")
        self.animals = CrudFrame(nb, self.db, "animals", [
            Field("name"), Field("species"), Field("age", kind="int", required=False),
            Field("enclosure_id", "Enclosure", "choice", enc, fk=True),
            Field("health", kind="choice", choices=["Healthy", "Under observation", "Sick", "Quarantine"]),
            Field("diet", required=False)],
            list_sql="SELECT a.id, a.name, a.species, a.age, e.name AS enclosure, a.health, a.diet "
                     "FROM animals a JOIN enclosures e ON e.id=a.enclosure_id", validator=self.check_capacity)
        self.staff = CrudFrame(nb, self.db, "staff", [
            Field("name"), Field("role", kind="choice", choices=["Keeper", "Vet", "Guide", "Ticketing", "Manager"]),
            Field("phone", required=False), Field("enclosure_id", "Assigned enclosure", "choice", enc, required=False, fk=True)],
            list_sql="SELECT s.id, s.name, s.role, s.phone, COALESCE(e.name,'-') AS enclosure FROM staff s "
                     "LEFT JOIN enclosures e ON e.id=s.enclosure_id")
        self.tickets = CrudFrame(nb, self.db, "tickets", [
            Field("visitor"), Field("adults", kind="int"), Field("children", kind="int"),
            Field("visit_date", kind="date")],
            list_sql="SELECT id, visitor, adults, children, visit_date, total FROM tickets ORDER BY id DESC",
            validator=self.price, title=f"Ticket sales (adult {ADULT_PRICE:.0f}, child {CHILD_PRICE:.0f})")
        frames = (self.enclosures, self.animals, self.staff, self.tickets)
        for f, t in zip(frames, ("Enclosures", "Animals", "Staff", "Tickets")):
            nb.add(f, text=t)
        refresh_on_tab_change(nb, *frames)

    def check_capacity(self, data, editing_id):
        enc = self.db.one("SELECT * FROM enclosures WHERE id=?", (data["enclosure_id"],))
        n = self.db.one("SELECT COUNT(*) AS n FROM animals WHERE enclosure_id=? AND id IS NOT ?",
                        (data["enclosure_id"], editing_id))["n"]
        if n >= enc["capacity"]:
            raise AppError(f"{enc['name']} is full (capacity {enc['capacity']})")

    @staticmethod
    def price(data, _editing_id):
        if data["adults"] + data["children"] == 0:
            raise AppError("At least one visitor is required")
        data["total"] = data["adults"] * ADULT_PRICE + data["children"] * CHILD_PRICE


if __name__ == "__main__":
    launch(App, "Zoo Management System", "1000x640")
