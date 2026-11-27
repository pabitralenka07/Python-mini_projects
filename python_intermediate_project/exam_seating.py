"""10. Exam Seating Arrangement System - constraint-based allocation (no same class side by side / front-back)."""
import csv
import random
import tkinter as tk
from collections import defaultdict, deque
from tkinter import filedialog, messagebox, ttk

from common import AppError, guarded, launch, parse_number


def _neighbours_ok(placed, key, cls):
    ri, r, c = key
    return placed.get((ri, r, c - 1)) != cls and placed.get((ri, r - 1, c)) != cls


def _search(seats, counts, limit, budget=200_000):
    """Backtracking over class labels (students of a class are interchangeable). None if infeasible."""
    placed, choice, options, i, nodes = {}, [None] * limit, [None] * limit, 0, 0
    while 0 <= i < limit:
        if choice[i] is not None:
            counts[choice[i]] += 1
            del placed[seats[i]]
            choice[i] = None
        if options[i] is None:
            options[i] = sorted((k for k, v in counts.items() if v > 0 and _neighbours_ok(placed, seats[i], k)),
                                key=lambda k: -counts[k])
        if options[i]:
            k = options[i].pop(0)
            counts[k] -= 1
            placed[seats[i]], choice[i] = k, k
            i += 1
            nodes += 1
            if nodes > budget:
                return None
        else:
            options[i] = None
            i -= 1
    return placed if i == limit else None


def _greedy(seats, counts, limit):
    placed, conflicts = {}, 0
    for key in seats[:limit]:
        live = [k for k, v in counts.items() if v > 0]
        ok = [k for k in live if _neighbours_ok(placed, key, k)]
        if not ok:
            ok, conflicts = live, conflicts + 1
        pick = max(ok, key=lambda k: counts[k])
        counts[pick] -= 1
        placed[key] = pick
    return placed, conflicts


def allocate(students, rooms):
    """students: [{'roll','name','cls'}]; rooms: [(name, rows, cols)].
    Seats students so that no two share a class left-right or front-back whenever that is possible
    (backtracking search); otherwise falls back to a greedy fill and reports the unavoidable conflicts.
    Returns (layout {room: grid}, unplaced students, number of seats that had to break the rule)."""
    pools = defaultdict(deque)
    for s in sorted(students, key=lambda s: str(s["roll"])):
        pools[s["cls"]].append(s)
    seats = [(ri, r, c) for ri, (_, rows, cols) in enumerate(rooms) for r in range(rows) for c in range(cols)]
    limit = min(len(seats), len(students))
    counts = {k: len(q) for k, q in pools.items()}
    placed = _search(seats, dict(counts), limit)
    conflicts = 0
    if placed is None:
        placed, conflicts = _greedy(seats, dict(counts), limit)
    layout = {name: [[None] * cols for _ in range(rows)] for name, rows, cols in rooms}
    for (ri, r, c), cls in placed.items():
        layout[rooms[ri][0]][r][c] = pools[cls].popleft()
    return layout, [s for q in pools.values() for s in q], conflicts


def render(grid):
    cells = [[f"{s['roll']}({s['cls']})" if s else "--" for s in row] for row in grid]
    w = max(len(c) for row in cells for c in row) + 2
    return "\n".join("".join(c.ljust(w) for c in row) for row in cells)


class App:
    def __init__(self, root):
        self.students, self.rooms, self.layout = [], [], {}
        left = ttk.Frame(root, padding=8)
        left.pack(side="left", fill="y")
        box = ttk.LabelFrame(left, text="Rooms")
        box.pack(fill="x")
        self.room_e = {}
        for i, (lab, default) in enumerate((("Name", "Room 101"), ("Rows", "5"), ("Columns", "6"))):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            e = ttk.Entry(box, width=14)
            e.insert(0, default)
            e.grid(row=i, column=1, padx=4)
            self.room_e[lab] = e
        ttk.Button(box, text="Add room", command=self.add_room).grid(row=3, column=1, sticky="w", pady=4)
        self.room_list = tk.Listbox(left, height=6, width=28)
        self.room_list.pack(pady=4)
        ttk.Button(left, text="Clear rooms", command=self.clear_rooms).pack(anchor="w")
        box = ttk.LabelFrame(left, text="Students")
        box.pack(fill="x", pady=8)
        ttk.Button(box, text="Load CSV (roll,name,class)", command=self.load_csv).pack(fill="x", padx=4, pady=2)
        ttk.Button(box, text="Generate 60 sample students", command=self.sample).pack(fill="x", padx=4, pady=2)
        self.count = ttk.Label(box, text="0 students loaded")
        self.count.pack()
        ttk.Button(left, text="Allocate seats", command=self.run).pack(fill="x", pady=4)
        ttk.Button(left, text="Export CSV", command=self.export).pack(fill="x")
        self.status = ttk.Label(left, text="", wraplength=200)
        self.status.pack(pady=6)
        self.nb = ttk.Notebook(root)
        self.nb.pack(side="right", fill="both", expand=True, padx=6, pady=6)

    @guarded
    def add_room(self):
        name = self.room_e["Name"].get().strip()
        if not name:
            raise AppError("Room name required")
        r = parse_number(self.room_e["Rows"].get(), "Rows", int, 1)
        c = parse_number(self.room_e["Columns"].get(), "Columns", int, 1)
        self.rooms.append((name, r, c))
        self.room_list.insert("end", f"{name}  ({r}x{c} = {r * c} seats)")

    def clear_rooms(self):
        self.rooms.clear()
        self.room_list.delete(0, "end")

    @guarded
    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, newline="", encoding="utf-8") as fh:
                rows = [{"roll": r["roll"].strip(), "name": r["name"].strip(), "cls": r["class"].strip()}
                        for r in csv.DictReader(fh)]
            self.students = rows
            self.count.config(text=f"{len(rows)} students loaded")

    def sample(self):
        classes = ["CSE", "ECE", "MECH"]
        self.students = [{"roll": f"{c}{i:02d}", "name": f"Student {c}{i}", "cls": c}
                         for c in classes for i in range(1, 21)]
        random.shuffle(self.students)
        self.count.config(text=f"{len(self.students)} students loaded")

    @guarded
    def run(self):
        if not self.rooms or not self.students:
            raise AppError("Add at least one room and load students first")
        self.layout, unplaced, conflicts = allocate(self.students, self.rooms)
        for tab in self.nb.tabs():
            self.nb.forget(tab)
        for name, grid in self.layout.items():
            t = tk.Text(self.nb, font=("Consolas", 10), wrap="none")
            t.insert("1.0", f"{name} - front of room at top\n\n{render(grid)}")
            t.config(state="disabled")
            self.nb.add(t, text=name)
        msg = f"Seated {len(self.students) - len(unplaced)}/{len(self.students)}. Seats with an unavoidable same-class neighbour: {conflicts}."
        if unplaced:
            msg += f" {len(unplaced)} students have no seat - add rooms."
        self.status.config(text=msg)

    @guarded
    def export(self):
        if not self.layout:
            raise AppError("Allocate seats first")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["room", "row", "column", "roll", "name", "class"])
                for room, grid in self.layout.items():
                    for r, row in enumerate(grid, 1):
                        for c, s in enumerate(row, 1):
                            if s:
                                w.writerow([room, r, c, s["roll"], s["name"], s["cls"]])
            messagebox.showinfo("Exported", path)


if __name__ == "__main__":
    launch(App, "Exam Seating Arrangement System", "1000x560")
