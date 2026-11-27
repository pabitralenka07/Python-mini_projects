"""7. Airport Management System - flights, passengers, tickets, live departures board."""
from datetime import datetime
from tkinter import ttk

from common import (AppError, CrudFrame, Database, Field, fill_tree, launch, make_tree, options,
                    refresh_on_tab_change)

SCHEMA = """
CREATE TABLE IF NOT EXISTS flights(id INTEGER PRIMARY KEY, flight_no TEXT NOT NULL UNIQUE, airline TEXT NOT NULL,
    origin TEXT NOT NULL, destination TEXT NOT NULL, departure TEXT NOT NULL, arrival TEXT NOT NULL,
    gate TEXT, capacity INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Scheduled');
CREATE TABLE IF NOT EXISTS passengers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, passport TEXT NOT NULL UNIQUE,
    nationality TEXT);
CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY, flight_id INTEGER NOT NULL REFERENCES flights(id),
    passenger_id INTEGER NOT NULL REFERENCES passengers(id), seat TEXT NOT NULL, travel_class TEXT NOT NULL,
    UNIQUE(flight_id, seat), UNIQUE(flight_id, passenger_id));
"""
STATUSES = ["Scheduled", "Boarding", "Delayed", "Departed", "Landed", "Cancelled"]
FMT = "%Y-%m-%d %H:%M"


def parse_dt(text, label):
    try:
        return datetime.strptime(text, FMT)
    except ValueError:
        raise AppError(f"{label} must look like 2026-12-31 14:30")


class App:
    def __init__(self, root):
        self.db = Database("airport.db", SCHEMA)
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.flights = CrudFrame(nb, self.db, "flights", [
            Field("flight_no"), Field("airline"), Field("origin", "Origin (IATA)"), Field("destination", "Destination (IATA)"),
            Field("departure", "Departure (YYYY-MM-DD HH:MM)"), Field("arrival", "Arrival (YYYY-MM-DD HH:MM)"),
            Field("gate", required=False), Field("capacity", kind="int"),
            Field("status", kind="choice", choices=STATUSES)],
            list_sql="SELECT id, flight_no, airline, origin, destination, departure, arrival, gate, capacity, status "
                     "FROM flights ORDER BY departure", validator=self.check_flight)
        self.passengers = CrudFrame(nb, self.db, "passengers", [
            Field("name"), Field("passport"), Field("nationality", required=False)])
        tickets_sql = ("SELECT t.id, f.flight_no, p.name AS passenger, t.seat, t.travel_class FROM tickets t "
                       "JOIN flights f ON f.id=t.flight_id JOIN passengers p ON p.id=t.passenger_id ORDER BY t.id DESC")
        self.tickets = CrudFrame(nb, self.db, "tickets", [
            Field("flight_id", "Flight", "choice", options(self.db, "SELECT id, flight_no FROM flights"), fk=True),
            Field("passenger_id", "Passenger", "choice", options(self.db, "SELECT id, name FROM passengers"), fk=True),
            Field("seat"), Field("travel_class", "Class", "choice", ["Economy", "Business", "First"])],
            list_sql=tickets_sql, validator=self.check_ticket)
        board = ttk.Frame(nb)
        holder = ttk.Frame(board)
        holder.pack(fill="both", expand=True, padx=8, pady=8)
        self.board_tree = make_tree(holder, 18)
        self.board = board
        for frame, text in ((self.flights, "Flights"), (self.passengers, "Passengers"),
                            (self.tickets, "Tickets"), (board, "Departures board")):
            nb.add(frame, text=text)
        refresh_on_tab_change(nb, self.flights, self.passengers, self.tickets, self)
        self.refresh()
        self.tick()

    def refresh(self):
        cols, rows = self.db.columns_and_rows(
            "SELECT f.flight_no, f.airline, f.origin || ' > ' || f.destination AS route, f.departure, "
            "COALESCE(f.gate,'TBA') AS gate, f.status, "
            "f.capacity - (SELECT COUNT(*) FROM tickets WHERE flight_id=f.id) AS seats_left "
            "FROM flights f WHERE f.status NOT IN ('Landed') ORDER BY f.departure")
        fill_tree(self.board_tree, cols, rows)

    def tick(self):
        self.refresh()
        self.board.after(10000, self.tick)

    def check_flight(self, data, _editing_id):
        if parse_dt(data["arrival"], "Arrival") <= parse_dt(data["departure"], "Departure"):
            raise AppError("Arrival must be after departure")
        if data["origin"].upper() == data["destination"].upper():
            raise AppError("Origin and destination must differ")
        data["origin"], data["destination"] = data["origin"].upper(), data["destination"].upper()

    def check_ticket(self, data, editing_id):
        flight = self.db.one("SELECT * FROM flights WHERE id=?", (data["flight_id"],))
        if flight["status"] in ("Cancelled", "Departed", "Landed"):
            raise AppError(f"Cannot sell tickets: flight is {flight['status']}")
        sold = self.db.one("SELECT COUNT(*) AS n FROM tickets WHERE flight_id=? AND id IS NOT ?",
                           (data["flight_id"], editing_id))["n"]
        if sold >= flight["capacity"]:
            raise AppError("Flight is full")


if __name__ == "__main__":
    launch(App, "Airport Management System", "1100x660")
