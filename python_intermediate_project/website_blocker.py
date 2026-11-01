"""12. Website Blocker - edits the hosts file between markers, with an optional daily schedule.
Needs Administrator (Windows) / sudo (Linux, macOS). Set BLOCKER_HOSTS=/some/file to test safely."""
import json
import os
import re
import sys
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from common import DATA_DIR, AppError, guarded, launch

START, END = "# >>> WEBSITE BLOCKER START >>>", "# <<< WEBSITE BLOCKER END <<<"
REDIRECT = "127.0.0.1"
CONFIG = os.path.join(DATA_DIR, "blocker.json")


def hosts_path():
    default = r"C:\Windows\System32\drivers\etc\hosts" if os.name == "nt" else "/etc/hosts"
    return os.environ.get("BLOCKER_HOSTS", default)


def normalise(site):
    site = re.sub(r"^\w+://", "", site.strip().lower()).split("/")[0]
    return site[4:] if site.startswith("www.") else site


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except PermissionError:
        raise AppError("Permission denied. Run as Administrator (Windows) or with sudo (Linux/macOS).")


def _write(path, text):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except PermissionError:
        raise AppError("Permission denied. Run as Administrator (Windows) or with sudo (Linux/macOS).")


def _strip(text):
    return re.sub(rf"\n*{re.escape(START)}.*?{re.escape(END)}\n?", "\n", text, flags=re.S).rstrip()


def block(sites, path=None):
    path = path or hosts_path()
    lines = [f"{REDIRECT} {s}\n{REDIRECT} www.{s}" for s in dict.fromkeys(normalise(x) for x in sites) if s]
    _write(path, _strip(_read(path)) + f"\n\n{START}\n" + "\n".join(lines) + f"\n{END}\n")


def unblock(path=None):
    path = path or hosts_path()
    _write(path, _strip(_read(path)) + "\n")


def is_blocked(path=None):
    return START in _read(path or hosts_path())


def in_window(now, start, end):
    """now/start/end are 'HH:MM' strings; handles overnight windows like 22:00-06:00."""
    return start <= now < end if start <= end else (now >= start or now < end)


def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"sites": ["facebook.com", "youtube.com"], "start": "09:00", "end": "17:00"}


def save_config(cfg):
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def apply_schedule(cfg):
    want = in_window(datetime.now().strftime("%H:%M"), cfg["start"], cfg["end"])
    if want != is_blocked():
        block(cfg["sites"]) if want else unblock()
    return want


class App:
    def __init__(self, root):
        self.root, self.cfg = root, load_config()
        f = ttk.Frame(root, padding=10)
        f.pack(fill="both", expand=True)
        self.lb = tk.Listbox(f, height=10, width=36)
        self.lb.grid(row=0, column=0, rowspan=4, padx=6)
        for s in self.cfg["sites"]:
            self.lb.insert("end", s)
        self.site_e = ttk.Entry(f, width=24)
        self.site_e.grid(row=0, column=1, columnspan=2, sticky="w")
        ttk.Button(f, text="Add site", command=self.add).grid(row=1, column=1, sticky="w")
        ttk.Button(f, text="Remove selected", command=self.remove).grid(row=1, column=2, sticky="w")
        sched = ttk.LabelFrame(f, text="Daily schedule (24h HH:MM)")
        sched.grid(row=2, column=1, columnspan=2, pady=8, sticky="w")
        self.start_e, self.end_e = ttk.Entry(sched, width=7), ttk.Entry(sched, width=7)
        self.start_e.insert(0, self.cfg["start"])
        self.end_e.insert(0, self.cfg["end"])
        for w in (ttk.Label(sched, text="From"), self.start_e, ttk.Label(sched, text="to"), self.end_e):
            w.pack(side="left", padx=3)
        self.auto = tk.BooleanVar()
        ttk.Checkbutton(f, text="Block automatically during schedule", variable=self.auto,
                        command=self.toggle_auto).grid(row=3, column=1, columnspan=2, sticky="w")
        bar = ttk.Frame(f)
        bar.grid(row=4, column=0, columnspan=3, pady=8)
        ttk.Button(bar, text="Block now", command=self.block_now).pack(side="left", padx=4)
        ttk.Button(bar, text="Unblock now", command=self.unblock_now).pack(side="left", padx=4)
        self.status = ttk.Label(f, text="Status: -", wraplength=520)
        self.status.grid(row=5, column=0, columnspan=3)
        self.refresh_status()

    def sites(self):
        return list(self.lb.get(0, "end"))

    def persist(self):
        self.cfg.update(sites=self.sites(), start=self.start_e.get().strip(), end=self.end_e.get().strip())
        save_config(self.cfg)

    def refresh_status(self, note=""):
        try:
            state = "BLOCKING" if is_blocked() else "not blocking"
        except AppError as e:
            state = str(e)
        self.status.config(text=f"Status: {state}  {note}")

    def add(self):
        s = normalise(self.site_e.get())
        if s and s not in self.sites():
            self.lb.insert("end", s)
            self.site_e.delete(0, "end")
            self.persist()

    def remove(self):
        for i in reversed(self.lb.curselection()):
            self.lb.delete(i)
        self.persist()

    def _check_times(self):
        for t in (self.start_e.get().strip(), self.end_e.get().strip()):
            try:
                time.strptime(t, "%H:%M")
            except ValueError:
                raise AppError("Times must be HH:MM (24-hour)")

    @guarded
    def block_now(self):
        self.persist()
        block(self.sites())
        self.refresh_status("(restart your browser / flush DNS if sites still load)")

    @guarded
    def unblock_now(self):
        self.auto.set(False)
        unblock()
        self.refresh_status()

    @guarded
    def toggle_auto(self):
        if self.auto.get():
            self._check_times()
            self.persist()
            self.tick()

    def tick(self):
        if not self.auto.get():
            return
        try:
            apply_schedule(self.cfg)
            self.refresh_status("(schedule on)")
        except AppError as e:
            self.auto.set(False)
            self.status.config(text=f"Status: {e}")
            return
        self.root.after(30000, self.tick)


def daemon():
    """Headless mode: python website_blocker.py --daemon (run with admin rights)."""
    cfg = load_config()
    while True:
        apply_schedule(cfg)
        time.sleep(30)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon()
    elif "--unblock" in sys.argv:
        unblock()
    else:
        launch(App, "Website Blocker", "620x420")
