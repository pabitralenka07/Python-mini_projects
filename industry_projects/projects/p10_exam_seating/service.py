"""Service layer for Exam Seating Arrangement System with course separation and chart rendering."""

import csv
import random
from pathlib import Path

from projects.p10_exam_seating.models import (
    AllocatedSeatView,
    Exam,
    Room,
    SeatAllocation,
    Student,
)
from projects.p10_exam_seating.repository import ExamRepository


class ExamSeatingError(Exception):
    """Base exception for exam seating arrangement operations."""

    pass


class RoomNotFoundError(ExamSeatingError):
    """Raised when an exam hall cannot be found."""

    pass


class CapacityExceededError(ExamSeatingError):
    """Raised when total students exceed the capacity of assigned exam halls."""

    pass


class NoStudentsToAllocateError(ExamSeatingError):
    """Raised when an exam session has no registered students."""

    pass


class ExamSeatingService:
    """Coordinates deterministic exam hall allocations, alternating course separation,
    and charts.
    """

    def __init__(self, repository: ExamRepository) -> None:
        self.repo = repository

    # --- Student & Room Registration ---

    def register_student(self, roll_number: str, name: str, course_code: str) -> Student:
        st = Student(
            roll_number=roll_number.strip().upper(),
            name=name.strip(),
            course_code=course_code.strip().upper(),
        )
        return self.repo.add_student(st)

    def register_room(self, room_number: str, rows: int, cols: int) -> Room:
        rm = Room(
            room_number=room_number.strip().upper(),
            rows=rows,
            cols=cols,
            total_capacity=rows * cols,
        )
        return self.repo.add_room(rm)

    def schedule_exam(self, course_code: str, exam_name: str, exam_date: str, slot: str) -> Exam:
        ex = Exam(
            course_code=course_code.strip().upper(),
            exam_name=exam_name.strip(),
            exam_date=exam_date.strip(),
            slot=slot.strip().upper(),
        )
        return self.repo.add_exam(ex)

    # --- Deterministic Seating Allocation Algorithm ---

    def allocate_exam_session(
        self,
        exam_date: str,
        slot: str,
        room_ids: list[int] | None = None,
        seed: int = 42,
    ) -> int:
        """Allocates students to rooms using deterministic seeded round-robin course interleaving.

        Ensures adjacent seats in the same row belong to different courses wherever possible.
        """
        exams = self.repo.list_exams_by_session(exam_date.strip(), slot.strip().upper())
        if not exams:
            raise ExamSeatingError(f"No exams scheduled for {exam_date} ({slot}).")

        # Map course code to exam object
        exam_by_course: dict[str, Exam] = {e.course_code: e for e in exams}
        exam_ids: list[int] = [e.id for e in exams if e.id is not None]

        # Gather students grouped by course
        course_queues: dict[str, list[Student]] = {}
        total_students = 0
        rng = random.Random(seed)

        for course_code in exam_by_course:
            students = self.repo.list_students_by_course(course_code)
            # Deterministic reproducible shuffle
            rng.shuffle(students)
            course_queues[course_code] = students
            total_students += len(students)

        if total_students == 0:
            raise NoStudentsToAllocateError(
                f"No students found enrolled for exams on {exam_date} ({slot})."
            )

        # Retrieve available rooms
        if room_ids:
            rooms: list[Room] = []
            for rid in room_ids:
                rm = self.repo.get_room(rid)
                if not rm:
                    raise RoomNotFoundError(f"Room ID {rid} not found.")
                rooms.append(rm)
        else:
            rooms = self.repo.list_rooms()

        if not rooms:
            raise RoomNotFoundError("No exam rooms available for allocation.")

        total_capacity = sum(r.total_capacity for r in rooms)
        if total_students > total_capacity:
            raise CapacityExceededError(
                f"Total students ({total_students}) exceeds total available hall capacity "
                f"({total_capacity}) across {len(rooms)} room(s)."
            )

        # Interleave students across distinct courses to maximize separation
        interleaved_students: list[Student] = []
        active_courses = [c for c in course_queues if course_queues[c]]

        while active_courses:
            next_active: list[str] = []
            for c in active_courses:
                if course_queues[c]:
                    interleaved_students.append(course_queues[c].pop(0))
                if course_queues[c]:
                    next_active.append(c)
            active_courses = next_active

        # Assign students to grid slots in rooms
        allocations: list[SeatAllocation] = []
        student_idx = 0

        for room in rooms:
            if room.id is None:
                continue

            for r in range(1, room.rows + 1):
                for col_idx in range(1, room.cols + 1):
                    if student_idx >= len(interleaved_students):
                        break

                    st = interleaved_students[student_idx]
                    student_idx += 1
                    target_exam = exam_by_course[st.course_code]

                    if st.id is not None and target_exam.id is not None:
                        seat_label = f"R{r}C{col_idx}"
                        allocations.append(
                            SeatAllocation(
                                exam_id=target_exam.id,
                                student_id=st.id,
                                room_id=room.id,
                                seat_label=seat_label,
                            )
                        )

                if student_idx >= len(interleaved_students):
                    break
            if student_idx >= len(interleaved_students):
                break

        # Save allocations atomically
        self.repo.clear_allocations_for_exams(exam_ids)
        self.repo.save_seat_allocations(allocations)

        return len(allocations)

    # --- Seating Chart Formatting & Export ---

    def format_room_chart(self, room_id: int, exam_ids: list[int]) -> str:
        room = self.repo.get_room(room_id)
        if not room:
            raise RoomNotFoundError(f"Room ID {room_id} not found.")

        allocations = self.repo.get_allocations_for_room(room_id, exam_ids)
        alloc_map: dict[str, AllocatedSeatView] = {a.seat_label: a for a in allocations}

        lines: list[str] = [
            f"=== SEATING CHART: ROOM {room.room_number} (Capacity: {room.total_capacity}) ===",
            f"Layout: {room.rows} Rows x {room.cols} Columns | Occupied: {len(allocations)}",
            " [ Blackboard / Invigilator Desk ]",
            "-" * (room.cols * 26),
        ]

        for r in range(1, room.rows + 1):
            row_cells: list[str] = []
            for c in range(1, room.cols + 1):
                seat_label = f"R{r}C{c}"
                if seat_label in alloc_map:
                    item = alloc_map[seat_label]
                    cell_text = f"[{seat_label}: {item.course_code} {item.roll_number}]"
                else:
                    cell_text = f"[{seat_label}: EMPTY]"
                row_cells.append(f"{cell_text:^24}")

            lines.append(" ".join(row_cells))

        lines.append("-" * (room.cols * 26))
        return "\n".join(lines)

    def export_allocations_to_csv(self, exam_ids: list[int], target_path: Path) -> Path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        allocations = self.repo.get_all_allocations_for_session(exam_ids)

        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Room", "Seat", "Course", "RollNumber", "StudentName", "ExamName"])
            for a in allocations:
                writer.writerow(
                    [
                        a.room_number,
                        a.seat_label,
                        a.course_code,
                        a.roll_number,
                        a.student_name,
                        a.exam_name,
                    ]
                )

        return target_path
