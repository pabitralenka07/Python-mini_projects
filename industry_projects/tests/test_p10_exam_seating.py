"""Tests for Project 10: Exam Seating Arrangement System."""

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from projects.p10_exam_seating.cli import run_cli
from projects.p10_exam_seating.repository import ExamRepository
from projects.p10_exam_seating.service import (
    CapacityExceededError,
    ExamSeatingService,
    NoStudentsToAllocateError,
)


@pytest.fixture
def exam_setup() -> tuple[ExamRepository, ExamSeatingService]:
    repo = ExamRepository.in_memory()
    service = ExamSeatingService(repo)
    return repo, service


def test_room_and_student_registration(
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    _, service = exam_setup
    student = service.register_student("ST-001", "Gordon Freeman", "PHYS101")
    room = service.register_room("HALL-A", rows=2, cols=3)

    assert student.id is not None
    assert room.id is not None
    assert room.total_capacity == 6


def test_capacity_exceeded_error(
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    _, service = exam_setup
    service.register_room("TINY-ROOM", rows=2, cols=2)
    service.schedule_exam("CS101", "Intro CS", "2026-12-15", "MORNING")

    for i in range(1, 6):
        service.register_student(f"CS-00{i}", f"Student {i}", "CS101")

    with pytest.raises(CapacityExceededError, match="exceeds total available hall capacity"):
        service.allocate_exam_session("2026-12-15", "MORNING")


def test_no_students_enrolled_error(
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    _, service = exam_setup
    service.register_room("HALL-B", rows=3, cols=3)
    service.schedule_exam("HIST101", "World History", "2026-12-15", "AFTERNOON")

    with pytest.raises(NoStudentsToAllocateError, match="No students found enrolled"):
        service.allocate_exam_session("2026-12-15", "AFTERNOON")


def test_deterministic_alternating_course_allocation(
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    repo, service = exam_setup
    room = service.register_room("MAIN-HALL", rows=2, cols=4)
    assert room.id is not None

    e1 = service.schedule_exam("CS101", "Computer Science", "2026-12-10", "MORNING")
    e2 = service.schedule_exam("MA201", "Mathematics", "2026-12-10", "MORNING")
    assert e1.id is not None
    assert e2.id is not None

    for i in range(1, 5):
        service.register_student(f"CS-0{i}", f"CS Student {i}", "CS101")
        service.register_student(f"MA-0{i}", f"MA Student {i}", "MA201")

    count = service.allocate_exam_session("2026-12-10", "MORNING", seed=42)
    assert count == 8

    allocations = repo.get_allocations_for_room(room.id, [e1.id, e2.id])
    assert len(allocations) == 8

    alloc_map = {a.seat_label: a for a in allocations}
    assert alloc_map["R1C1"].course_code != alloc_map["R1C2"].course_code
    assert alloc_map["R1C2"].course_code != alloc_map["R1C3"].course_code
    assert alloc_map["R1C3"].course_code != alloc_map["R1C4"].course_code


def test_reproducibility_with_seed(
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    repo, service = exam_setup
    room = service.register_room("TEST-HALL", rows=2, cols=3)
    assert room.id is not None

    e1 = service.schedule_exam("BIO101", "Biology", "2026-12-20", "MORNING")
    e2 = service.schedule_exam("CHEM101", "Chemistry", "2026-12-20", "MORNING")
    assert e1.id is not None
    assert e2.id is not None

    for i in range(1, 4):
        service.register_student(f"BIO-{i}", f"Bio {i}", "BIO101")
        service.register_student(f"CHEM-{i}", f"Chem {i}", "CHEM101")

    service.allocate_exam_session("2026-12-20", "MORNING", seed=99)
    run1 = repo.get_allocations_for_room(room.id, [e1.id, e2.id])

    service.allocate_exam_session("2026-12-20", "MORNING", seed=99)
    run2 = repo.get_allocations_for_room(room.id, [e1.id, e2.id])

    assert [(a.seat_label, a.roll_number) for a in run1] == [
        (a.seat_label, a.roll_number) for a in run2
    ]


def test_csv_export_and_chart_rendering(
    tmp_path: Path,
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    _, service = exam_setup
    room = service.register_room("EXPORT-HALL", rows=2, cols=2)
    assert room.id is not None

    e = service.schedule_exam("ENG101", "English", "2026-12-22", "MORNING")
    assert e.id is not None

    service.register_student("ENG-1", "Shakespeare", "ENG101")
    service.register_student("ENG-2", "Chaucer", "ENG101")

    service.allocate_exam_session("2026-12-22", "MORNING")

    chart = service.format_room_chart(room.id, [e.id])
    assert "SEATING CHART: ROOM EXPORT-HALL" in chart
    assert "ENG101 ENG-1" in chart
    assert "EMPTY" in chart

    csv_file = tmp_path / "test_seating.csv"
    exported_path = service.export_allocations_to_csv([e.id], csv_file)
    assert exported_path.exists()

    with open(exported_path, encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert reader[0] == ["Room", "Seat", "Course", "RollNumber", "StudentName", "ExamName"]
        assert len(reader) == 3


def test_cli_handles_eof_gracefully(
    exam_setup: tuple[ExamRepository, ExamSeatingService],
) -> None:
    _, service = exam_setup
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)
