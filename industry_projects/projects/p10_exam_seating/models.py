"""Data models for Exam Seating Arrangement System."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Student:
    """Represents an enrolled student registered for courses."""

    roll_number: str
    name: str
    course_code: str
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.roll_number.strip():
            raise ValueError("Roll number cannot be empty.")
        if not self.name.strip():
            raise ValueError("Student name cannot be empty.")
        if not self.course_code.strip():
            raise ValueError("Course code cannot be empty.")


@dataclass(frozen=True)
class Room:
    """Represents an exam hall with a 2D seating matrix (rows x columns)."""

    room_number: str
    rows: int
    cols: int
    total_capacity: int
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.room_number.strip():
            raise ValueError("Room number cannot be empty.")
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("Rows and columns must be strictly positive.")
        if self.total_capacity != self.rows * self.cols:
            raise ValueError("Total capacity must equal rows * cols.")


@dataclass(frozen=True)
class Exam:
    """Represents a scheduled exam session for a course."""

    course_code: str
    exam_name: str
    exam_date: str  # YYYY-MM-DD
    slot: str  # MORNING, AFTERNOON
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.course_code.strip():
            raise ValueError("Course code cannot be empty.")
        if not self.exam_name.strip():
            raise ValueError("Exam name cannot be empty.")
        if not self.slot.strip():
            raise ValueError("Exam slot cannot be empty.")


@dataclass(frozen=True)
class SeatAllocation:
    """Represents a specific seat assigned to a student for an exam."""

    exam_id: int
    student_id: int
    room_id: int
    seat_label: str  # e.g. R1C1, R1C2
    id: int | None = None

    def __post_init__(self) -> None:
        if self.exam_id <= 0:
            raise ValueError("Invalid exam ID.")
        if self.student_id <= 0:
            raise ValueError("Invalid student ID.")
        if self.room_id <= 0:
            raise ValueError("Invalid room ID.")
        if not self.seat_label.strip():
            raise ValueError("Seat label cannot be empty.")


@dataclass(frozen=True)
class AllocatedSeatView:
    """Composite display record of a student's assigned exam seat."""

    roll_number: str
    student_name: str
    course_code: str
    exam_name: str
    room_number: str
    seat_label: str
