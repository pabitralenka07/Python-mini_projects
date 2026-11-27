"""Run: python test_logic.py   (logic only, no GUI shown)"""
import random
import sqlite3
from datetime import date, timedelta

from common import AppError, Database

from bank_core import SCHEMA as BS, Bank, BankError
bank = Bank(Database(":memory:", BS))
a = bank.open_account("Asha", "1234", 1000)
b = bank.open_account("Ravi", "4321", 0)
assert bank.transfer(a, b, 300) == 700 and bank.balance(b) == 300
for bad in (lambda: bank.withdraw(a, 5000), lambda: bank.transfer(a, a, 1), lambda: bank.transfer(a, 999, 100)):
    try: bad(); raise SystemExit("expected failure")
    except BankError: pass
assert bank.balance(a) == 700, "failed transfer must roll back"
for _ in range(3):
    try: bank.authenticate(a, "0000")
    except BankError: pass
try: bank.authenticate(a, "1234"); raise SystemExit("should be locked")
except BankError as e: assert "locked" in str(e)
bank.unlock(a); assert bank.authenticate(a, "1234") == "Asha"
from atm_system import ATMSession
s = ATMSession(bank, a)
try: s.withdraw(150); raise SystemExit("multiple of 100")
except BankError: pass
assert s.withdraw(200) == 500
print("bank/atm ok")

from library_management import SCHEMA as LS, Library
db = Database(":memory:", LS); lib = Library(db)
db.execute("INSERT INTO books(title,author,copies) VALUES('Dune','Herbert',1)")
db.execute("INSERT INTO members(name) VALUES('M1')")
t0 = date(2026, 1, 1)
lib.issue(1, 1, today=t0)
try: lib.issue(1, 1, today=t0); raise SystemExit("no copies")
except AppError: pass
assert lib.return_book(1, today=t0 + timedelta(days=19)) == 5 * 2.0
assert lib.available(1) == 1
print("library ok")

from bus_reservation import SCHEMA as BUS, BusSystem
db = Database(":memory:", BUS); bs = BusSystem(db)
db.execute("INSERT INTO buses(name,route_from,route_to,depart_time,fare,seats) VALUES('B1','A','B','10:00',250,8)")
d = (date.today() + timedelta(days=2)).isoformat()
bs.book(1, d, 3, "Kim")
try: bs.book(1, d, 3, "Lee"); raise SystemExit("double booking!")
except AppError as e: assert "already booked" in str(e)
try: bs.book(1, d, 9, "Lee"); raise SystemExit("seat range")
except AppError: pass
try: bs.book(1, "2000-01-01", 1, "Lee"); raise SystemExit("past")
except AppError: pass
assert bs.booked(1, d) == {3}
print("bus ok")

from electricity_bill import calculate_bill
c = calculate_bill("Domestic", 250)
assert (c["energy"], c["tax"], c["total"]) == (1100.0, 55.0, 1205.0), c
assert calculate_bill("Domestic", 400)["energy"] == 100*3.5 + 200*5 + 100*7
assert calculate_bill("Commercial", 0)["total"] == 150.0
print("electricity ok")

from exam_seating import allocate
studs = [{"roll": f"{c}{i}", "name": "x", "cls": c} for c in "ABC" for i in range(20)]
random.shuffle(studs)
layout, unplaced, conflicts = allocate(studs, [("R1", 5, 6), ("R2", 5, 6)])
assert not unplaced and conflicts == 0
for grid in layout.values():
    for r, row in enumerate(grid):
        for cc, st in enumerate(row):
            if st and cc and row[cc-1]: assert st["cls"] != row[cc-1]["cls"]
            if st and r and grid[r-1][cc]: assert st["cls"] != grid[r-1][cc]["cls"]
_, un, _ = allocate(studs, [("Small", 2, 2)]); assert len(un) == 56
print("seating ok")

from snake_game import SnakeModel
m = SnakeModel(10, 10, random.Random(1))
m.turn((-1, 0)); assert m.pending == (1, 0), "no reversal"
m.food = (m.snake[0][0] + 1, m.snake[0][1]); n = len(m.snake); m.step()
assert len(m.snake) == n + 1 and m.score == 10
for _ in range(20): m.step()
assert not m.alive, "wall collision"
print("snake ok")

import os, tempfile
tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".hosts"); tmp.write("127.0.0.1 localhost\n"); tmp.close()
os.environ["BLOCKER_HOSTS"] = tmp.name
import website_blocker as wb
wb.block(["https://www.Facebook.com/home", "youtube.com"])
t = open(tmp.name).read()
assert "127.0.0.1 facebook.com" in t and "127.0.0.1 www.youtube.com" in t and "localhost" in t
wb.block(["x.com"]); t = open(tmp.name).read()
assert t.count(wb.START) == 1 and "facebook" not in t, "re-block must replace, not duplicate"
wb.unblock(); t = open(tmp.name).read()
assert wb.START not in t and "localhost" in t
assert wb.in_window("10:00", "09:00", "17:00") and not wb.in_window("18:00", "09:00", "17:00")
assert wb.in_window("23:30", "22:00", "06:00") and wb.in_window("05:00", "22:00", "06:00") and not wb.in_window("12:00", "22:00", "06:00")
os.unlink(tmp.name)
print("blocker ok")
print("ALL LOGIC TESTS PASSED")
