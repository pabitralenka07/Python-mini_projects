"""6. Bus Reservation System - seat map, double-booking protection, cancellation."""
import sqlite3
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from common import (AppError, CrudFrame, Database, Field, choice_id, fill_tree, guarded, launch,
                    make_tree, options, parse_date, refresh_on_tab_change, selected_id)

SCHEMA = """
CREATE TABLE IF NOT EXISTS buses(id INTEGER PRIMARY KEY, name TEXT NOT NULL, route_from TEXT NOT NULL,
    route_to TEXT NOT NULL, depart_time TEXT NOT NULL, fare REAL NOT NULL, seats INTEGER NOT NULL CHECK(seats > 0));
CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, bus_id INTEGER NOT NULL REFERENCES buses(id),
    travel_date TEXT NOT NULL, seat_no INTEGER NOT NULL, passenger TEXT NOT NULL, phone TEXT,
    UNIQUE(bus_id, travel_date, seat_no));
"""


class BusSystem:
    def __init__(self, db):
        self.db = db

    def booked(self, bus_id, travel_date):
        return {r["seat_no"] for r in self.db.query(
            "SELECT seat_no FROM bookings WHERE bus_id=? AND travel_date=?", (bus_id, travel_date))}

    def book(self, bus_id, travel_date, seat, passenger, phone=""):
        bus = self.db.one("SELECT * FROM buses WHERE id=?", (bus_id,))
        if bus is None:
            raise AppError("Bus not found")
        if parse_date(travel_date) < date.today():
            raise AppError("Travel date is in the past")
        if not 1 <= seat <= bus["seats"]:
            raise AppError(f"Seat must be between 1 and {bus['seats']}")
        if not passenger.strip():
            raise AppError("Passenger name is required")
        try:
            self.db.execute("INSERT INTO bookings(bus_id, travel_date, seat_no, passenger, phone) VALUES(?,?,?,?,?)",
                            (bus_id, travel_date, seat, passenger.strip(), phone.strip()))
        except sqlite3.IntegrityError:
            raise AppError(f"Seat {seat} is already booked")
        return bus["fare"]

    def cancel(self, booking_id):
        self.db.execute("DELETE FROM bookings WHERE id=?", (booking_id,))


class App:
    def __init__(self, root):
        self.db = Database("bus.db", SCHEMA)
        self.sys = BusSystem(self.db)
        self.chosen = None
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.buses = CrudFrame(nb, self.db, "buses", [
            Field("name"), Field("route_from", "From"), Field("route_to", "To"),
            Field("depart_time", "Departure (HH:MM)"), Field("fare", kind="float"), Field("seats", kind="int")])
        nb.add(self.buses, text="Buses")

        book = ttk.Frame(nb)
        nb.add(book, text="Book ticket")
        top = ttk.Frame(book)
        top.pack(fill="x", padx=8, pady=6)
        self.bus_cb = ttk.Combobox(top, width=38, state="readonly", postcommand=lambda: self.bus_cb.configure(
            values=options(self.db, "SELECT id, name || ' (' || route_from || ' > ' || route_to || ')' FROM buses")()))
        self.bus_cb.pack(side="left")
        self.date_e = ttk.Entry(top, width=12)
        self.date_e.insert(0, date.today().isoformat())
        self.date_e.pack(side="left", padx=6)
        ttk.Button(top, text="Show seats", command=self.show_seats).pack(side="left")
        ttk.Label(book, text="Green = free, red = booked, blue = your choice").pack()
        self.grid = ttk.Frame(book)
        self.grid.pack(pady=8)
        who = ttk.Frame(book)
        who.pack(pady=4)
        self.name_e, self.phone_e = ttk.Entry(who, width=22), ttk.Entry(who, width=16)
        for label, w in (("Passenger", self.name_e), ("Phone", self.phone_e)):
            ttk.Label(who, text=label).pack(side="left", padx=4)
            w.pack(side="left")
        ttk.Button(who, text="Book selected seat", command=self.book).pack(side="left", padx=8)

        mine = ttk.Frame(nb)
        nb.add(mine, text="Bookings")
        ttk.Button(mine, text="Cancel selected booking", command=self.cancel).pack(anchor="w", padx=8, pady=6)
        holder = ttk.Frame(mine)
        holder.pack(fill="both", expand=True, padx=8)
        self.tree = make_tree(holder)
        self.mine = mine
        refresh_on_tab_change(nb, self.buses, self)
        self.refresh()

    def refresh(self):
        cols, rows = self.db.columns_and_rows(
            "SELECT k.id, b.name AS bus, b.route_from || ' > ' || b.route_to AS route, k.travel_date, "
            "k.seat_no, k.passenger, b.fare FROM bookings k JOIN buses b ON b.id=k.bus_id "
            "ORDER BY k.travel_date, k.id")
        fill_tree(self.tree, cols, rows)

    @guarded
    def show_seats(self):
        bus_id = choice_id(self.bus_cb.get())
        travel = self.date_e.get().strip()
        parse_date(travel)
        seats = self.db.one("SELECT seats FROM buses WHERE id=?", (bus_id,))["seats"]
        taken = self.sys.booked(bus_id, travel)
        self.chosen = None
        for w in self.grid.winfo_children():
            w.destroy()
        self.buttons = {}
        for n in range(1, seats + 1):
            b = tk.Button(self.grid, text=str(n), width=4, bg="#c62828" if n in taken else "#2e7d32", fg="white",
                          state="disabled" if n in taken else "normal", command=lambda n=n: self.pick(n))
            b.grid(row=(n - 1) // 4, column=(n - 1) % 4 + ((n - 1) % 4 > 1), padx=3, pady=3)
            self.buttons[n] = b

    def pick(self, seat):
        if self.chosen:
            self.buttons[self.chosen].config(bg="#2e7d32")
        self.chosen = seat
        self.buttons[seat].config(bg="#1565c0")

    @guarded
    def book(self):
        if not self.chosen:
            raise AppError("Click a free seat first")
        fare = self.sys.book(choice_id(self.bus_cb.get()), self.date_e.get().strip(), self.chosen,
                             self.name_e.get(), self.phone_e.get())
        messagebox.showinfo("Booked", f"Seat {self.chosen} confirmed. Fare: {fare:.2f}")
        self.show_seats()
        self.refresh()

    @guarded
    def cancel(self):
        self.sys.cancel(selected_id(self.tree, "booking"))
        self.refresh()


if __name__ == "__main__":
    launch(App, "Bus Reservation System", "1000x640")
