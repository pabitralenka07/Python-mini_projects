"""Shared helpers: SQLite wrapper, Tk widget helpers and a generic CRUD tab."""
import functools
import os
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


class AppError(Exception):
    """A business-rule error that is safe to show to the user."""


class Database:
    def __init__(self, name, schema):
        path = name if name == ":memory:" else os.path.join(DATA_DIR, name)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(schema)

    def query(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def execute(self, sql, params=()):
        with self.conn:  # commit on success, rollback on error
            return self.conn.execute(sql, params).lastrowid

    def columns_and_rows(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return [d[0] for d in cur.description], cur.fetchall()


# ---------- validation / parsing ----------
def guarded(fn):
    """Show errors in a message box instead of crashing the GUI."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AppError as e:
            messagebox.showerror("Error", str(e))
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Data rule violated",
                                 f"Duplicate value, or the record is in use.\n({e})")
        except sqlite3.Error as e:
            messagebox.showerror("Database error", str(e))
    return wrapper


def parse_date(text, label="Date"):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise AppError(f"{label} must be in YYYY-MM-DD format")


def parse_number(text, label, kind=float, minimum=None):
    try:
        value = kind(str(text).strip())
    except ValueError:
        raise AppError(f"{label} must be a valid {'whole ' if kind is int else ''}number")
    if minimum is not None and value < minimum:
        raise AppError(f"{label} must be at least {minimum}")
    return value


def choice_id(text):
    if not text:
        raise AppError("Please select an item from the list")
    return int(str(text).split(" - ")[0])


def options(db, sql):
    """Return a callable giving ['1 - Label', ...] from a 2-column query."""
    return lambda: [f"{r[0]} - {r[1]}" for r in db.query(sql)]


# ---------- widgets ----------
def form_entries(parent, labels, width=24):
    entries = {}
    for i, label in enumerate(labels):
        ttk.Label(parent, text=label).grid(row=i, column=0, sticky="e", padx=4, pady=3)
        e = ttk.Entry(parent, width=width)
        e.grid(row=i, column=1, sticky="w", padx=4, pady=3)
        entries[label] = e
    return entries


def make_tree(parent, height=10):
    tree = ttk.Treeview(parent, show="headings", height=height)
    sb = ttk.Scrollbar(parent, command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    return tree


def fill_tree(tree, columns, rows):
    tree["columns"] = list(columns)
    for c in columns:
        tree.heading(c, text=c)
        tree.column(c, width=max(70, min(180, 11 * len(c))), anchor="w")
    tree.delete(*tree.get_children())
    for r in rows:
        tree.insert("", "end", values=list(r))


def selected_id(tree, what="row"):
    sel = tree.selection()
    if not sel:
        raise AppError(f"Select a {what} first")
    return int(tree.item(sel[0], "values")[0])


def launch(app_cls, title, size="1000x640"):
    root = tk.Tk()
    root.title(title)
    root.geometry(size)
    app_cls(root)
    root.mainloop()


# ---------- generic CRUD tab ----------
class Field:
    def __init__(self, name, label=None, kind="text", choices=None, required=True, fk=False):
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self.kind, self.choices, self.required, self.fk = kind, choices, required, fk

    def options(self):
        return list(self.choices() if callable(self.choices) else (self.choices or []))


def _set(widget, value):
    text = "" if value is None else str(value)
    if isinstance(widget, ttk.Combobox):
        widget.set(text)
    else:
        widget.delete(0, "end")
        widget.insert(0, text)


class CrudFrame(ttk.Frame):
    """Form + table + search for one table whose primary key is `id`.

    list_sql: optional SELECT (first column must be the id) used for display.
    validator(data, editing_id): may raise AppError and may add/modify values in `data`.
    """

    def __init__(self, parent, db, table, fields, list_sql=None, validator=None, title=None):
        super().__init__(parent)
        self.db, self.table, self.fields, self.validator = db, table, fields, validator
        self.list_sql = list_sql or f"SELECT id, {', '.join(f.name for f in fields)} FROM {table}"
        self.selected_id = None
        self.widgets = {}
        box = ttk.LabelFrame(self, text=title or table.replace("_", " ").title())
        box.pack(fill="x", padx=8, pady=6)
        for i, f in enumerate(fields):
            r, c = divmod(i, 2)
            ttk.Label(box, text=f.label + (" *" if f.required else "")).grid(
                row=r, column=c * 2, sticky="e", padx=4, pady=3)
            if f.kind == "choice":
                w = ttk.Combobox(box, width=27, state="readonly")
                w.configure(postcommand=lambda w=w, f=f: w.configure(values=f.options()))
            else:
                w = ttk.Entry(box, width=30)
            w.grid(row=r, column=c * 2 + 1, sticky="w", padx=4, pady=3)
            self.widgets[f.name] = w
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8)
        for text, cmd in (("Add", self.add), ("Update", self.update_row),
                          ("Delete", self.delete), ("Clear", self.clear)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3, pady=3)
        ttk.Label(bar, text="Search:").pack(side="left", padx=(20, 3))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(bar, textvariable=self.search_var, width=25).pack(side="left")
        holder = ttk.Frame(self)
        holder.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree = make_tree(holder)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.refresh()

    def read_form(self):
        data = {}
        for f in self.fields:
            raw = self.widgets[f.name].get().strip()
            if not raw:
                if f.required:
                    raise AppError(f"{f.label} is required")
                data[f.name] = None
                continue
            if f.kind == "int":
                data[f.name] = parse_number(raw, f.label, int, 0)
            elif f.kind == "float":
                data[f.name] = parse_number(raw, f.label, float, 0)
            elif f.kind == "date":
                parse_date(raw, f.label)
                data[f.name] = raw
            elif f.kind == "choice" and f.fk:
                data[f.name] = choice_id(raw)
            else:
                data[f.name] = raw
        return data

    @guarded
    def add(self):
        data = self.read_form()
        if self.validator:
            self.validator(data, None)
        marks = ", ".join("?" * len(data))
        self.db.execute(f"INSERT INTO {self.table}({', '.join(data)}) VALUES({marks})",
                        tuple(data.values()))
        self.clear()
        self.refresh()

    @guarded
    def update_row(self):
        if self.selected_id is None:
            raise AppError("Select a row to update")
        data = self.read_form()
        if self.validator:
            self.validator(data, self.selected_id)
        sets = ", ".join(f"{k}=?" for k in data)
        self.db.execute(f"UPDATE {self.table} SET {sets} WHERE id=?",
                        (*data.values(), self.selected_id))
        self.refresh()

    @guarded
    def delete(self):
        if self.selected_id is None:
            raise AppError("Select a row to delete")
        if messagebox.askyesno("Confirm", "Delete the selected record?"):
            self.db.execute(f"DELETE FROM {self.table} WHERE id=?", (self.selected_id,))
            self.clear()
            self.refresh()

    def clear(self):
        self.selected_id = None
        for f in self.fields:
            _set(self.widgets[f.name], "")
        self.tree.selection_remove(self.tree.selection())

    def refresh(self):
        cols, rows = self.db.columns_and_rows(self.list_sql)
        term = self.search_var.get().strip().lower()
        if term:
            rows = [r for r in rows if any(term in str(v).lower() for v in r)]
        fill_tree(self.tree, cols, rows)

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(self.tree.item(sel[0], "values")[0])
        row = self.db.one(f"SELECT * FROM {self.table} WHERE id=?", (self.selected_id,))
        if row is None:
            return
        for f in self.fields:
            v = row[f.name]
            if f.kind == "choice" and f.fk and v is not None:
                v = next((o for o in f.options() if o.startswith(f"{v} - ")), v)
            _set(self.widgets[f.name], v)


def refresh_on_tab_change(notebook, *frames):
    notebook.bind("<<NotebookTabChanged>>",
                  lambda _e: [f.refresh() for f in frames])
