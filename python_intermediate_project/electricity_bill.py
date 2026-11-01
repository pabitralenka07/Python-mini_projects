"""9. Electricity Bill System - slab tariff, bill generation, text bill export."""
import os
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from common import (DATA_DIR, AppError, CrudFrame, Database, Field, choice_id, fill_tree, guarded,
                    launch, make_tree, options, parse_number, refresh_on_tab_change, selected_id)

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, meter_no TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    address TEXT, category TEXT NOT NULL DEFAULT 'Domestic', initial_reading REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS bills(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
    month TEXT NOT NULL, prev_reading REAL NOT NULL, curr_reading REAL NOT NULL, units REAL NOT NULL,
    energy REAL NOT NULL, fixed REAL NOT NULL, tax REAL NOT NULL, total REAL NOT NULL, paid INTEGER NOT NULL DEFAULT 0,
    UNIQUE(customer_id, month));
"""
# Sample tariff (editable): (slab width in units, rate per unit); None = all remaining units
TARIFF = {
    "Domestic": {"slabs": [(100, 3.5), (200, 5.0), (None, 7.0)], "fixed": 50.0},
    "Commercial": {"slabs": [(200, 6.0), (None, 8.5)], "fixed": 150.0},
}
TAX_RATE = 0.05


def calculate_bill(category, units):
    plan = TARIFF[category]
    remaining, energy, lines = units, 0.0, []
    for width, rate in plan["slabs"]:
        used = remaining if width is None else min(remaining, width)
        if used > 0:
            lines.append((used, rate, used * rate))
            energy += used * rate
            remaining -= used
    tax = round(energy * TAX_RATE, 2)
    return {"units": units, "lines": lines, "energy": round(energy, 2), "fixed": plan["fixed"],
            "tax": tax, "total": round(energy + plan["fixed"] + tax, 2)}


def render_bill(customer, month, prev, curr, calc):
    out = ["=" * 44, "        ELECTRICITY BILL", "=" * 44,
           f"Customer : {customer['name']}", f"Meter no : {customer['meter_no']}",
           f"Category : {customer['category']}", f"Month    : {month}",
           f"Reading  : {prev:g} -> {curr:g}  ({calc['units']:g} units)", "-" * 44]
    out += [f"  {u:>7g} units @ {r:<5g} = {amt:>10.2f}" for u, r, amt in calc["lines"]]
    out += [f"Energy charge      : {calc['energy']:>10.2f}", f"Fixed charge       : {calc['fixed']:>10.2f}",
            f"Tax ({TAX_RATE:.0%})          : {calc['tax']:>10.2f}", "-" * 44,
            f"TOTAL PAYABLE      : {calc['total']:>10.2f}", "=" * 44]
    return "\n".join(out)


class App:
    def __init__(self, root):
        self.db = Database("electricity.db", SCHEMA)
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.customers = CrudFrame(nb, self.db, "customers", [
            Field("meter_no"), Field("name"), Field("address", required=False),
            Field("category", kind="choice", choices=list(TARIFF)),
            Field("initial_reading", kind="float")])
        nb.add(self.customers, text="Customers")

        tab = ttk.Frame(nb)
        nb.add(tab, text="Generate bill")
        box = ttk.LabelFrame(tab, text="New bill")
        box.pack(fill="x", padx=8, pady=6)
        self.cust_cb = ttk.Combobox(box, width=34, state="readonly", postcommand=lambda: self.cust_cb.configure(
            values=options(self.db, "SELECT id, name || ' [' || meter_no || ']' FROM customers")()))
        self.month_e, self.read_e = ttk.Entry(box, width=12), ttk.Entry(box, width=12)
        self.month_e.insert(0, date.today().strftime("%Y-%m"))
        for i, (lab, w) in enumerate((("Customer", self.cust_cb), ("Month (YYYY-MM)", self.month_e),
                                      ("Current reading", self.read_e))):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=3)
            w.grid(row=i, column=1, sticky="w", padx=4)
        bar = ttk.Frame(box)
        bar.grid(row=3, column=1, sticky="w", pady=4)
        ttk.Button(bar, text="Generate", command=self.generate).pack(side="left")
        ttk.Button(bar, text="Save bill as .txt", command=self.save).pack(side="left", padx=4)
        ttk.Button(bar, text="Mark selected paid", command=self.mark_paid).pack(side="left")
        self.text = tk.Text(tab, height=14, font=("Consolas", 10))
        self.text.pack(fill="x", padx=8)
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree = make_tree(holder, 6)
        self.last = None
        refresh_on_tab_change(nb, self.customers, self)
        self.refresh()

    def refresh(self):
        cols, rows = self.db.columns_and_rows(
            "SELECT b.id, c.name AS customer, b.month, b.units, b.total, "
            "CASE b.paid WHEN 1 THEN 'Paid' ELSE 'Due' END AS status FROM bills b "
            "JOIN customers c ON c.id=b.customer_id ORDER BY b.id DESC")
        fill_tree(self.tree, cols, rows)

    @guarded
    def generate(self):
        cust = self.db.one("SELECT * FROM customers WHERE id=?", (choice_id(self.cust_cb.get()),))
        month = self.month_e.get().strip()
        if len(month) != 7 or month[4] != "-" or not (month[:4] + month[5:]).isdigit() or not 1 <= int(month[5:]) <= 12:
            raise AppError("Month must be YYYY-MM")
        curr = parse_number(self.read_e.get(), "Current reading", float, 0)
        last = self.db.one("SELECT curr_reading FROM bills WHERE customer_id=? ORDER BY month DESC LIMIT 1", (cust["id"],))
        prev = last["curr_reading"] if last else cust["initial_reading"]
        if curr < prev:
            raise AppError(f"Current reading cannot be below the previous reading ({prev:g})")
        calc = calculate_bill(cust["category"], curr - prev)
        self.db.execute("INSERT INTO bills(customer_id, month, prev_reading, curr_reading, units, energy, fixed, tax, total) "
                        "VALUES(?,?,?,?,?,?,?,?,?)", (cust["id"], month, prev, curr, calc["units"], calc["energy"],
                                                      calc["fixed"], calc["tax"], calc["total"]))
        self.last = (cust, month, render_bill(cust, month, prev, curr, calc))
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.last[2])
        self.refresh()

    @guarded
    def save(self):
        if not self.last:
            raise AppError("Generate a bill first")
        cust, month, body = self.last
        os.makedirs(os.path.join(DATA_DIR, "bills"), exist_ok=True)
        path = filedialog.asksaveasfilename(initialdir=os.path.join(DATA_DIR, "bills"),
                                            initialfile=f"bill_{cust['meter_no']}_{month}.txt")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
            messagebox.showinfo("Saved", path)

    @guarded
    def mark_paid(self):
        self.db.execute("UPDATE bills SET paid=1 WHERE id=?", (selected_id(self.tree, "bill"),))
        self.refresh()


if __name__ == "__main__":
    launch(App, "Electricity Bill System", "900x720")
