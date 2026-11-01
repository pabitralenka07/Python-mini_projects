"""Database repository for Exam Seating Arrangement System."""

from pathlib import Path

from common.db import DatabaseError, DatabaseManager
from projects.p10_exam_seating.models import (
    AllocatedSeatView,
    Exam,
    Room,
    SeatAllocation,
    Student,
)

EXAM_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_number TEXT NOT NULL UNIQUE CHECK(length(trim(roll_number)) > 0),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    course_code TEXT NOT NULL CHECK(length(trim(course_code)) > 0)
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL UNIQUE CHECK(length(trim(room_number)) > 0),
    rows INTEGER NOT NULL CHECK(rows > 0),
    cols INTEGER NOT NULL CHECK(cols > 0),
    total_capacity INTEGER NOT NULL CHECK(total_capacity > 0)
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL CHECK(length(trim(course_code)) > 0),
    exam_name TEXT NOT NULL CHECK(length(trim(exam_name)) > 0),
    exam_date TEXT NOT NULL,
    slot TEXT NOT NULL CHECK(slot IN ('MORNING', 'AFTERNOON')),
    UNIQUE(course_code, exam_date, slot)
);

CREATE TABLE IF NOT EXISTS seat_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    seat_label TEXT NOT NULL CHECK(length(trim(seat_label)) > 0),
    UNIQUE(exam_id, student_id),
    UNIQUE(exam_id, room_id, seat_label)
);

CREATE INDEX IF NOT EXISTS idx_allocations_room ON seat_allocations(room_id);
CREATE INDEX IF NOT EXISTS idx_students_course ON students(course_code);
"""


class ExamRepository:
    """Manages SQLite queries for students, examination halls, schedules, and seat allocations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    @classmethod
    def from_path(cls, db_path: Path | str) -> "ExamRepository":
        manager = DatabaseManager(
            db_path=db_path,
            schema_sql=EXAM_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    @classmethod
    def in_memory(cls) -> "ExamRepository":
        manager = DatabaseManager(
            db_path=":memory:",
            schema_sql=EXAM_SCHEMA,
            expected_user_version=1,
        )
        return cls(manager)

    # --- Students ---

    def add_student(self, student: Student) -> Student:
        query = "INSERT INTO students (roll_number, name, course_code) VALUES (?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(query, (student.roll_number, student.name, student.course_code))
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for student.")
            st_id = int(cursor.lastrowid)

        return Student(
            id=st_id,
            roll_number=student.roll_number,
            name=student.name,
            course_code=student.course_code,
        )

    def list_all_students(self) -> list[Student]:
        query = (
            "SELECT id, roll_number, name, course_code FROM students "
            "ORDER BY course_code, roll_number;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Student(
                    id=r["id"],
                    roll_number=r["roll_number"],
                    name=r["name"],
                    course_code=r["course_code"],
                )
                for r in rows
            ]

    def list_students_by_course(self, course_code: str) -> list[Student]:
        query = (
            "SELECT id, roll_number, name, course_code FROM students "
            "WHERE course_code = ? ORDER BY roll_number;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (course_code,)).fetchall()
            return [
                Student(
                    id=r["id"],
                    roll_number=r["roll_number"],
                    name=r["name"],
                    course_code=r["course_code"],
                )
                for r in rows
            ]

    # --- Rooms ---

    def add_room(self, room: Room) -> Room:
        query = "INSERT INTO rooms (room_number, rows, cols, total_capacity) VALUES (?, ?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query, (room.room_number, room.rows, room.cols, room.total_capacity)
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for room.")
            rm_id = int(cursor.lastrowid)

        return Room(
            id=rm_id,
            room_number=room.room_number,
            rows=room.rows,
            cols=room.cols,
            total_capacity=room.total_capacity,
        )

    def get_room(self, room_id: int) -> Room | None:
        query = "SELECT id, room_number, rows, cols, total_capacity FROM rooms WHERE id = ?;"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (room_id,)).fetchone()
            if not row:
                return None
            return Room(
                id=row["id"],
                room_number=row["room_number"],
                rows=row["rows"],
                cols=row["cols"],
                total_capacity=row["total_capacity"],
            )

    def list_rooms(self) -> list[Room]:
        query = (
            "SELECT id, room_number, rows, cols, total_capacity FROM rooms ORDER BY room_number;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Room(
                    id=r["id"],
                    room_number=r["room_number"],
                    rows=r["rows"],
                    cols=r["cols"],
                    total_capacity=r["total_capacity"],
                )
                for r in rows
            ]

    # --- Exams ---

    def add_exam(self, exam: Exam) -> Exam:
        query = "INSERT INTO exams (course_code, exam_name, exam_date, slot) VALUES (?, ?, ?, ?);"
        with self.db.get_connection() as conn, conn:
            cursor = conn.execute(
                query, (exam.course_code, exam.exam_name, exam.exam_date, exam.slot)
            )
            if cursor.lastrowid is None:
                raise DatabaseError("Failed to obtain lastrowid for exam.")
            ex_id = int(cursor.lastrowid)

        return Exam(
            id=ex_id,
            course_code=exam.course_code,
            exam_name=exam.exam_name,
            exam_date=exam.exam_date,
            slot=exam.slot,
        )

    def list_exams_by_session(self, exam_date: str, slot: str) -> list[Exam]:
        query = """
            SELECT id, course_code, exam_name, exam_date, slot
            FROM exams WHERE exam_date = ? AND slot = ?
            ORDER BY course_code;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (exam_date, slot)).fetchall()
            return [
                Exam(
                    id=r["id"],
                    course_code=r["course_code"],
                    exam_name=r["exam_name"],
                    exam_date=r["exam_date"],
                    slot=r["slot"],
                )
                for r in rows
            ]

    def list_all_exams(self) -> list[Exam]:
        query = (
            "SELECT id, course_code, exam_name, exam_date, slot FROM exams "
            "ORDER BY exam_date, slot, course_code;"
        )
        with self.db.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Exam(
                    id=r["id"],
                    course_code=r["course_code"],
                    exam_name=r["exam_name"],
                    exam_date=r["exam_date"],
                    slot=r["slot"],
                )
                for r in rows
            ]

    # --- Seat Allocations ---

    def clear_allocations_for_exams(self, exam_ids: list[int]) -> None:
        if not exam_ids:
            return
        placeholders = ",".join("?" for _ in exam_ids)
        query = f"DELETE FROM seat_allocations WHERE exam_id IN ({placeholders});"
        with self.db.get_connection() as conn, conn:
            conn.execute(query, tuple(exam_ids))

    def save_seat_allocations(self, allocations: list[SeatAllocation]) -> None:
        query = """
            INSERT INTO seat_allocations (exam_id, student_id, room_id, seat_label)
            VALUES (?, ?, ?, ?);
        """
        with self.db.get_connection() as conn, conn:
            for sa in allocations:
                conn.execute(query, (sa.exam_id, sa.student_id, sa.room_id, sa.seat_label))

    def get_allocations_for_room(
        self, room_id: int, exam_ids: list[int]
    ) -> list[AllocatedSeatView]:
        if not exam_ids:
            return []
        placeholders = ",".join("?" for _ in exam_ids)
        query = f"""
            SELECT
                s.roll_number,
                s.name as student_name,
                s.course_code,
                e.exam_name,
                r.room_number,
                sa.seat_label
            FROM seat_allocations sa
            JOIN students s ON sa.student_id = s.id
            JOIN exams e ON sa.exam_id = e.id
            JOIN rooms r ON sa.room_id = r.id
            WHERE sa.room_id = ? AND sa.exam_id IN ({placeholders})
            ORDER BY sa.seat_label;
        """
        params: list[int] = [room_id, *exam_ids]
        with self.db.get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                AllocatedSeatView(
                    roll_number=r["roll_number"],
                    student_name=r["student_name"],
                    course_code=r["course_code"],
                    exam_name=r["exam_name"],
                    room_number=r["room_number"],
                    seat_label=r["seat_label"],
                )
                for r in rows
            ]

    def get_all_allocations_for_session(self, exam_ids: list[int]) -> list[AllocatedSeatView]:
        if not exam_ids:
            return []
        placeholders = ",".join("?" for _ in exam_ids)
        query = f"""
            SELECT
                s.roll_number,
                s.name as student_name,
                s.course_code,
                e.exam_name,
                r.room_number,
                sa.seat_label
            FROM seat_allocations sa
            JOIN students s ON sa.student_id = s.id
            JOIN exams e ON sa.exam_id = e.id
            JOIN rooms r ON sa.room_id = r.id
            WHERE sa.exam_id IN ({placeholders})
            ORDER BY r.room_number, sa.seat_label;
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, tuple(exam_ids)).fetchall()
            return [
                AllocatedSeatView(
                    roll_number=r["roll_number"],
                    student_name=r["student_name"],
                    course_code=r["course_code"],
                    exam_name=r["exam_name"],
                    room_number=r["room_number"],
                    seat_label=r["seat_label"],
                )
                for r in rows
            ]
