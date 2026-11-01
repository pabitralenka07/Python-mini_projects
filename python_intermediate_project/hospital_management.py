"""5. Hospital Management System - patients, doctors, appointments (no double booking)."""
from tkinter import ttk

from common import AppError, CrudFrame, Database, Field, launch, options, refresh_on_tab_change

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
    gender TEXT NOT NULL, phone TEXT, condition_notes TEXT);
CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY, name TEXT NOT NULL, specialization TEXT NOT NULL,
    phone TEXT, fee REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id), doctor_id INTEGER NOT NULL REFERENCES doctors(id),
    date TEXT NOT NULL, time TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Scheduled');
"""
SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 17) for m in (0, 30)]


class App:
    def __init__(self, root):
        self.db = Database("hospital.db", SCHEMA)
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.patients = CrudFrame(nb, self.db, "patients", [
            Field("name"), Field("age", kind="int"), Field("gender", kind="choice", choices=["Male", "Female", "Other"]),
            Field("phone", required=False), Field("condition_notes", "Condition / notes", required=False)])
        self.doctors = CrudFrame(nb, self.db, "doctors", [
            Field("name"), Field("specialization"), Field("phone", required=False), Field("fee", kind="float")])
        sql = ("SELECT a.id, p.name AS patient, d.name AS doctor, d.specialization, a.date, a.time, "
               "a.status, d.fee AS bill FROM appointments a JOIN patients p ON p.id=a.patient_id "
               "JOIN doctors d ON d.id=a.doctor_id ORDER BY a.date, a.time")
        self.appts = CrudFrame(nb, self.db, "appointments", [
            Field("patient_id", "Patient", "choice", options(self.db, "SELECT id, name FROM patients"), fk=True),
            Field("doctor_id", "Doctor", "choice", options(self.db, "SELECT id, name FROM doctors"), fk=True),
            Field("date", kind="date"), Field("time", kind="choice", choices=SLOTS),
            Field("status", kind="choice", choices=["Scheduled", "Completed", "Cancelled"])],
            list_sql=sql, validator=self.check_slot)
        for frame, text in ((self.patients, "Patients"), (self.doctors, "Doctors"), (self.appts, "Appointments")):
            nb.add(frame, text=text)
        refresh_on_tab_change(nb, self.patients, self.doctors, self.appts)

    def check_slot(self, data, editing_id):
        if data["status"] == "Cancelled":
            return
        clash = self.db.one(
            "SELECT id FROM appointments WHERE doctor_id=? AND date=? AND time=? "
            "AND status!='Cancelled' AND id IS NOT ?",
            (data["doctor_id"], data["date"], data["time"], editing_id))
        if clash:
            raise AppError("That doctor is already booked at this date and time")


if __name__ == "__main__":
    launch(App, "Hospital Management System", "1000x640")
