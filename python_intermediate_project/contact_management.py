"""1. Contact Management System - CRUD, search, CSV import/export."""
import csv
import re
from tkinter import filedialog, messagebox, ttk

from common import AppError, CrudFrame, Database, Field, guarded, launch

SCHEMA = """CREATE TABLE IF NOT EXISTS contacts(
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
    email TEXT, address TEXT);"""
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def validate(data, _editing_id):
    digits = re.sub(r"[\s\-+()]", "", data["phone"])
    if not digits.isdigit() or not 7 <= len(digits) <= 15:
        raise AppError("Phone must contain 7-15 digits")
    if data["email"] and not EMAIL.fullmatch(data["email"]):
        raise AppError("Email address looks invalid")


class App:
    def __init__(self, root):
        self.db = Database("contacts.db", SCHEMA)
        fields = [Field("name"), Field("phone"),
                  Field("email", required=False), Field("address", required=False)]
        self.crud = CrudFrame(root, self.db, "contacts", fields, validator=validate)
        self.crud.pack(fill="both", expand=True)
        bar = ttk.Frame(root)
        bar.pack(fill="x", padx=8, pady=4)
        ttk.Button(bar, text="Export CSV", command=self.export_csv).pack(side="left")
        ttk.Button(bar, text="Import CSV", command=self.import_csv).pack(side="left", padx=4)

    @guarded
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            rows = self.db.query("SELECT name, phone, email, address FROM contacts ORDER BY name")
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["name", "phone", "email", "address"])
                w.writerows([list(r) for r in rows])
            messagebox.showinfo("Export", f"Exported {len(rows)} contacts")

    @guarded
    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        added = skipped = 0
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    data = {k: (row.get(k) or "").strip() or None for k in ("name", "phone", "email", "address")}
                    if not data["name"] or not data["phone"]:
                        raise AppError("missing name/phone")
                    validate(data, None)
                    self.db.execute("INSERT INTO contacts(name, phone, email, address) VALUES(?,?,?,?)",
                                    (data["name"], data["phone"], data["email"], data["address"]))
                    added += 1
                except Exception:
                    skipped += 1
        self.crud.refresh()
        messagebox.showinfo("Import", f"Added {added}, skipped {skipped} (invalid or duplicate)")


if __name__ == "__main__":
    launch(App, "Contact Management System", "900x600")
