"""Seed script for Exam Seating Arrangement System with halls, exams, and enrolled students."""

from pathlib import Path

from projects.p10_exam_seating.repository import ExamRepository
from projects.p10_exam_seating.service import (
    ExamSeatingError,
    ExamSeatingService,
)


def seed_data(repo: ExamRepository | None = None) -> None:
    if repo is None:
        db_path = Path(__file__).resolve().parent / "data" / "exam_seating.db"
        repo = ExamRepository.from_path(db_path)

    service = ExamSeatingService(repo)
    print("Seeding Exam Seating Arrangement System...")

    rooms = repo.list_rooms()
    if not rooms:
        service.register_room("HALL-101", rows=3, cols=4)
        service.register_room("HALL-102", rows=4, cols=4)
        print(" -> Configured exam halls: HALL-101 (12 seats) and HALL-102 (16 seats).")
    else:
        print(f" -> Exam rooms already exist ({len(rooms)} found).")

    exams = repo.list_all_exams()
    if not exams:
        service.schedule_exam("CS101", "Introduction to Programming", "2026-12-10", "MORNING")
        service.schedule_exam("MA201", "Linear Algebra & Matrices", "2026-12-10", "MORNING")
        print(" -> Scheduled concurrent morning exams: CS101 and MA201 on 2026-12-10.")
    else:
        print(f" -> Exams already exist ({len(exams)} found).")

    students = repo.list_all_students()
    if not students:
        cs_students = [
            ("CS-101", "Alan Turing"),
            ("CS-102", "Ada Lovelace"),
            ("CS-103", "Grace Hopper"),
            ("CS-104", "Donald Knuth"),
            ("CS-105", "Claude Shannon"),
            ("CS-106", "Margaret Hamilton"),
            ("CS-107", "Ken Thompson"),
            ("CS-108", "Dennis Ritchie"),
        ]
        for roll, name in cs_students:
            service.register_student(roll, name, "CS101")

        ma_students = [
            ("MA-201", "Leonhard Euler"),
            ("MA-202", "Carl Friedrich Gauss"),
            ("MA-203", "Bernhard Riemann"),
            ("MA-204", "Emmy Noether"),
            ("MA-205", "Henri Poincare"),
            ("MA-206", "David Hilbert"),
            ("MA-207", "Blaise Pascal"),
            ("MA-208", "Pierre de Fermat"),
        ]
        for roll, name in ma_students:
            service.register_student(roll, name, "MA201")

        print(" -> Enrolled 16 students across CS101 (8) and MA201 (8).")
    else:
        print(f" -> Students already exist ({len(students)} found).")

    try:
        count = service.allocate_exam_session("2026-12-10", "MORNING", seed=42)
        print(f" -> Generated seating allocation: {count} students seated across halls.")
    except ExamSeatingError as e:
        print(f" -> Allocation skipped: {e}")

    print("Exam Seating Arrangement System seeding complete.")


if __name__ == "__main__":
    seed_data()
