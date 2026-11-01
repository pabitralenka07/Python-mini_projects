"""Run: xvfb-run -a python test_gui.py   (launches every app headlessly and pokes at it)"""
import importlib, tkinter as tk
from tkinter import messagebox
errors = []
messagebox.showerror = lambda t, m, **k: errors.append(m)
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True

MODS = ["contact_management", "bank_management", "atm_system", "library_management", "hospital_management",
        "bus_reservation", "airport_management", "zoo_management", "electricity_bill", "exam_seating",
        "snake_game", "website_blocker", "image_downloader"]
apps = {}
for name in MODS:
    root = tk.Tk(); app = importlib.import_module(name).App(root); root.update()
    apps[name] = (root, app); print("launched", name)

def fill(frame, **vals):
    for k, v in vals.items():
        w = frame.widgets[k]
        (w.set if hasattr(w, "set") else lambda x: (w.delete(0, "end"), w.insert(0, x)))(v)

# contacts: add, validation, search
root, app = apps["contact_management"]
fill(app.crud, name="Asha", phone="9876543210"); app.crud.add()
fill(app.crud, name="Bad", phone="12"); app.crud.add()
assert len(app.crud.tree.get_children()) == 1 and "7-15 digits" in errors.pop()

# hospital: double booking blocked
root, app = apps["hospital_management"]
fill(app.patients, name="P", age="30", gender="Male"); app.patients.add()
fill(app.doctors, name="Dr X", specialization="ENT", fee="500"); app.doctors.add()
appt = dict(patient_id="1 - P", doctor_id="1 - Dr X", date="2030-01-01", time="10:00", status="Scheduled")
fill(app.appts, **appt); app.appts.add()
fill(app.appts, **appt); app.appts.add()
assert len(app.appts.tree.get_children()) == 1 and "already booked" in errors.pop()

# zoo: capacity + ticket total
root, app = apps["zoo_management"]
fill(app.enclosures, name="Lions", habitat="Savannah", capacity="1"); app.enclosures.add()
fill(app.animals, name="Leo", species="Lion", enclosure_id="1 - Lions", health="Healthy"); app.animals.add()
fill(app.animals, name="Lea", species="Lion", enclosure_id="1 - Lions", health="Healthy"); app.animals.add()
assert "full" in errors.pop()
fill(app.tickets, visitor="V", adults="2", children="1", visit_date="2030-01-01"); app.tickets.add()
assert float(app.tickets.tree.item(app.tickets.tree.get_children()[0], "values")[5]) == 250.0

# airport: duplicate seat rejected by DB, friendly message
root, app = apps["airport_management"]
fill(app.flights, flight_no="AI1", airline="AI", origin="bbi", destination="del", departure="2030-01-01 10:00",
     arrival="2030-01-01 12:00", capacity="2", status="Scheduled"); app.flights.add()
for n in ("A", "B"):
    fill(app.passengers, name=n, passport="P" + n); app.passengers.add()
fill(app.tickets, flight_id="1 - AI1", passenger_id="1 - A", seat="1A", travel_class="Economy"); app.tickets.add()
fill(app.tickets, flight_id="1 - AI1", passenger_id="2 - B", seat="1A", travel_class="Economy"); app.tickets.add()
assert errors and "Duplicate" in errors.pop()

# bus: seat map + booking
root, app = apps["bus_reservation"]
fill(app.buses, name="Exp", route_from="A", route_to="B", depart_time="09:00", fare="100", seats="8"); app.buses.add()
app.bus_cb.set("1 - Exp (A > B)"); app.show_seats(); app.pick(2)
app.name_e.insert(0, "Kim"); app.book(); app.show_seats()
assert str(app.buttons[2]["state"]) == "disabled" and len(app.tree.get_children()) == 1

# library issue/return via GUI
root, app = apps["library_management"]
fill(app.books, title="T", author="A", copies="1"); app.books.add()
fill(app.members, name="M"); app.members.add()
app.book_cb.set("1 - T"); app.member_cb.set("1 - M"); app.issue()
assert len(app.loan_tree.get_children()) == 1
app.loan_tree.selection_set(app.loan_tree.get_children()[0]); app.return_book()

# electricity bill via GUI
root, app = apps["electricity_bill"]
fill(app.customers, meter_no="M1", name="C", category="Domestic", initial_reading="0"); app.customers.add()
app.cust_cb.set("1 - C [M1]"); app.read_e.insert(0, "250"); app.generate()
assert "1205.00" in app.text.get("1.0", "end")

# exam seating via GUI
root, app = apps["exam_seating"]
app.sample(); app.add_room(); app.run()
assert "neighbour: 0" in app.status.cget("text"), app.status.cget("text")

# bank + ATM share bank.db
root, app = apps["bank_management"]
app.new["Holder name"].insert(0, "Zed"); app.new["4-digit PIN"].insert(0, "9999"); app.open_account()
root, app = apps["atm_system"]
app.acc.insert(0, "1"); app.pin.insert(0, "1234"); app.login()
app.balance(); assert "5000.00" in app.out.get("1.0", "end")

# snake keypress + tick
root, app = apps["snake_game"]
class E: keysym = "Up"
app.on_key(E()); root.update()

assert not errors, errors
print("GUI TESTS PASSED")
