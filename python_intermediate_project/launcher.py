"""Launcher: python launcher.py - opens any of the 13 projects."""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

PROJECTS = [
    ("1. Contact Management", "contact_management.py"), ("2. Bank Management", "bank_management.py"),
    ("3. ATM", "atm_system.py"), ("4. Library Management", "library_management.py"),
    ("5. Hospital Management", "hospital_management.py"), ("6. Bus Reservation", "bus_reservation.py"),
    ("7. Airport Management", "airport_management.py"), ("8. Zoo Management", "zoo_management.py"),
    ("9. Electricity Bill", "electricity_bill.py"), ("10. Exam Seating", "exam_seating.py"),
    ("11. Snake Game", "snake_game.py"), ("12. Website Blocker (needs admin)", "website_blocker.py"),
    ("13. Image Downloader", "image_downloader.py"),
]
HERE = os.path.dirname(os.path.abspath(__file__))

root = tk.Tk()
root.title("Python Projects - Group 2")
for i, (title, script) in enumerate(PROJECTS):
    ttk.Button(root, text=title, width=34,
               command=lambda s=script: subprocess.Popen([sys.executable, os.path.join(HERE, s)], cwd=HERE)
               ).grid(row=i // 2, column=i % 2, padx=6, pady=5)
root.mainloop()
