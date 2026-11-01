"""CLI interface for Exam Seating Arrangement System."""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    prompt_choice,
    prompt_int,
    safe_input,
)
from common.tables import format_table
from projects.p10_exam_seating.repository import ExamRepository
from projects.p10_exam_seating.service import (
    CapacityExceededError,
    ExamSeatingError,
    ExamSeatingService,
    NoStudentsToAllocateError,
    RoomNotFoundError,
)


def get_default_service() -> ExamSeatingService:
    db_path = Path(__file__).resolve().parent / "data" / "exam_seating.db"
    repo = ExamRepository.from_path(db_path)
    return ExamSeatingService(repo)


def display_menu() -> None:
    print("\n" + "=" * 54)
    print("        EXAM SEATING ARRANGEMENT SYSTEM               ")
    print("=" * 54)
    print(" 1. View Room Seating Chart (ASCII Grid)")
    print(" 2. Run Seating Allocation (Course Separation)")
    print(" 3. Export Seating Plan to CSV File")
    print(" 4. View Enrolled Students")
    print(" 5. View Examination Rooms")
    print(" 6. Add Student, Room, or Exam Session")
    print(" 0. Exit")
    print("=" * 54)


def view_chart(service: ExamSeatingService) -> None:
    try:
        rooms = service.repo.list_rooms()
        if not rooms:
            print("\nNo examination halls configured.")
            return

        print("\nAvailable Examination Rooms:")
        for r in rooms:
            print(
                f"  ID #{r.id} -> Room {r.room_number} "
                f"({r.rows}x{r.cols} = {r.total_capacity} seats)"
            )

        room_id = prompt_int("Enter Room ID to view: ")
        exams = service.repo.list_all_exams()
        exam_ids = [e.id for e in exams if e.id is not None]

        chart = service.format_room_chart(room_id, exam_ids)
        print("\n" + chart)
    except (RoomNotFoundError, ExamSeatingError) as e:
        print(f"[ERROR] {e}")


def run_allocation(service: ExamSeatingService) -> None:
    try:
        exam_date = safe_input("Enter Exam Date (YYYY-MM-DD): ").strip()
        slot = prompt_choice("Select Exam Slot: ", ["MORNING", "AFTERNOON"])
        seed_str = safe_input("Enter Deterministic RNG Seed (default 42): ").strip()
        seed = int(seed_str) if seed_str.isdigit() else 42

        count = service.allocate_exam_session(exam_date, slot, seed=seed)
        print(f"\n[SUCCESS] Successfully allocated {count} students into exam halls!")
        print("Adjacency course separation rules enforced.")
    except (CapacityExceededError, NoStudentsToAllocateError, ExamSeatingError) as e:
        print(f"[ERROR] {e}")


def export_csv(service: ExamSeatingService) -> None:
    try:
        exam_date = safe_input("Enter Exam Date (YYYY-MM-DD): ").strip()
        slot = prompt_choice("Select Exam Slot: ", ["MORNING", "AFTERNOON"])

        exams = service.repo.list_exams_by_session(exam_date, slot)
        exam_ids = [e.id for e in exams if e.id is not None]
        if not exam_ids:
            print(f"[ERROR] No exams found on {exam_date} ({slot}).")
            return

        filename = safe_input("Enter target CSV filename (e.g. seating_plan.csv): ").strip()
        if not filename.endswith(".csv"):
            filename += ".csv"

        target_dir = Path(__file__).resolve().parent / "data" / "exports"
        target_path = target_dir / filename
        saved_path = service.export_allocations_to_csv(exam_ids, target_path)
        print(f"\n[SUCCESS] Seating plan successfully exported to: {saved_path}")
    except Exception as e:
        print(f"[ERROR] {e}")


def view_students(service: ExamSeatingService) -> None:
    students = service.repo.list_all_students()
    if not students:
        print("\nNo students enrolled.")
        return

    headers = ["ID", "Roll Number", "Full Name", "Course Code"]
    rows = [[str(s.id), s.roll_number, s.name, s.course_code] for s in students]
    print("\n" + format_table(headers, rows))


def view_rooms(service: ExamSeatingService) -> None:
    rooms = service.repo.list_rooms()
    if not rooms:
        print("\nNo rooms configured.")
        return

    headers = ["ID", "Room #", "Rows", "Cols", "Total Capacity"]
    rows = [
        [str(r.id), r.room_number, str(r.rows), str(r.cols), str(r.total_capacity)] for r in rooms
    ]
    print("\n" + format_table(headers, rows))


def add_entity(service: ExamSeatingService) -> None:
    print("\nAdd Entity:")
    print(" 1. Enroll Student")
    print(" 2. Configure Exam Room")
    print(" 3. Schedule Exam Session")
    choice = safe_input("Select (1-3): ").strip()

    if choice == "1":
        roll = safe_input("Roll Number (e.g. CS-101): ")
        name = safe_input("Full Name: ")
        course = safe_input("Course Code (e.g. CS101): ")
        st = service.register_student(roll, name, course)
        print(f"[SUCCESS] Student '{st.name}' ({st.roll_number}) enrolled.")
    elif choice == "2":
        r_num = safe_input("Room Number (e.g. HALL-A): ")
        rows = prompt_int("Number of Rows: ")
        cols = prompt_int("Number of Columns: ")
        rm = service.register_room(r_num, rows, cols)
        print(f"[SUCCESS] Room '{rm.room_number}' configured with capacity {rm.total_capacity}.")
    elif choice == "3":
        course = safe_input("Course Code: ")
        name = safe_input("Exam Name: ")
        dt = safe_input("Exam Date (YYYY-MM-DD): ")
        slot = prompt_choice("Slot: ", ["MORNING", "AFTERNOON"])
        ex = service.schedule_exam(course, name, dt, slot)
        print(f"[SUCCESS] Exam '{ex.exam_name}' scheduled for {ex.exam_date} ({ex.slot}).")


def run_cli(service: ExamSeatingService | None = None) -> None:
    svc = service if service is not None else get_default_service()

    while True:
        try:
            display_menu()
            choice = safe_input("Enter choice (0-6): ").strip()
            if choice == "1":
                view_chart(svc)
            elif choice == "2":
                run_allocation(svc)
            elif choice == "3":
                export_csv(svc)
            elif choice == "4":
                view_students(svc)
            elif choice == "5":
                view_rooms(svc)
            elif choice == "6":
                add_entity(svc)
            elif choice == "0":
                print("Thank you for using Exam Seating Arrangement System.")
                break
            else:
                print("Invalid option. Please choose between 0 and 6.")
        except UserExitException:
            print("\nSession terminated. Goodbye!")
            break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    run_cli()
