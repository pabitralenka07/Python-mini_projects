"""Tests for Project 01: Contact Management System.

Covers:
- Add, search, edit, delete contacts
- Deduplication and validation rules
- CSV export formula injection neutralization (=, +, -, @)
- CSV import handling and error reporting
- Headless GUI controller operations
- CLI execution and EOF exit handling
"""

import subprocess
import sys
from pathlib import Path

import pytest

from projects.p01_contact_management.gui_app import ContactGUIController
from projects.p01_contact_management.repository import ContactRepository
from projects.p01_contact_management.service import (
    ContactService,
    DuplicateContactError,
    ValidationError,
    sanitize_csv_cell,
)


@pytest.fixture
def repo(tmp_path: Path) -> ContactRepository:
    db_file = tmp_path / "test_contacts.db"
    return ContactRepository.from_path(db_file)


@pytest.fixture
def service(repo: ContactRepository) -> ContactService:
    return ContactService(repo)


def test_add_and_list_contacts(service: ContactService) -> None:
    c = service.add_contact("Alan Turing", "+1-555-1111", "alan@example.com", "Bletchley")
    assert c.id is not None
    assert c.name == "Alan Turing"

    all_contacts = service.list_contacts()
    assert len(all_contacts) == 1
    assert all_contacts[0].email == "alan@example.com"


def test_duplicate_rejection(service: ContactService) -> None:
    service.add_contact("User One", "+1-555-1111", "one@example.com")

    with pytest.raises(DuplicateContactError, match="already exists"):
        service.add_contact("User Two", "+1-555-1111", "two@example.com")

    with pytest.raises(DuplicateContactError, match="already exists"):
        service.add_contact("User Three", "+1-555-2222", "one@example.com")


def test_field_validation(service: ContactService) -> None:
    with pytest.raises(ValidationError, match="Name cannot be empty"):
        service.add_contact("   ", "+1-555-1111", "valid@example.com")

    with pytest.raises(ValidationError, match="must contain between 7 and 15 digits"):
        service.add_contact("User", "123", "valid@example.com")

    with pytest.raises(ValidationError, match="not a valid email"):
        service.add_contact("User", "+1-555-1111", "invalid_email_no_at")


def test_edit_and_delete_contact(service: ContactService) -> None:
    c = service.add_contact("Grace Hopper", "+1-555-3333", "grace@example.com")
    assert c.id is not None

    updated = service.edit_contact(c.id, "Grace M. Hopper", "+1-555-3333", "grace_m@example.com")
    assert updated.name == "Grace M. Hopper"

    service.delete_contact(c.id)
    assert len(service.list_contacts()) == 0


def test_csv_formula_injection_neutralization(tmp_path: Path, service: ContactService) -> None:
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-10") == "'-10"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("Safe Name") == "Safe Name"

    service.add_contact("=MaliciousFormula", "+1-555-4444", "malicious@example.com")
    export_file = tmp_path / "contacts_out.csv"
    count = service.export_csv(export_file)
    assert count == 1

    content = export_file.read_text(encoding="utf-8")
    assert "'=MaliciousFormula" in content


def test_csv_import_success_and_skips(tmp_path: Path, service: ContactService) -> None:
    csv_file = tmp_path / "contacts_in.csv"
    csv_file.write_text(
        "name,phone,email,address\n"
        "Alice,+1-555-6666,alice@example.com,Wonderland\n"
        "Bob,invalid_phone,bob@example.com,Builder St\n"
        "Charlie,+1-555-7777,charlie@example.com,Factory\n"
        "Duplicate Alice,+1-555-6666,alice2@example.com,Duplicate Phone\n",
        encoding="utf-8",
    )

    imported, skipped, errors = service.import_csv(csv_file)
    assert imported == 2
    assert skipped == 2
    assert len(errors) == 2


def test_gui_controller_operations(service: ContactService) -> None:
    ctrl = ContactGUIController(service)
    c = ctrl.add_contact("GUI User", "+1-555-8888", "gui@example.com", "GUI Lane")
    assert c.id is not None
    assert len(ctrl.list_contacts()) == 1

    search_res = ctrl.search_contacts("GUI")
    assert len(search_res) == 1

    ctrl.delete_contact(c.id)
    assert len(ctrl.list_contacts()) == 0


def test_cli_eof_clean_exit() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "projects.p01_contact_management"],
        cwd=root_dir,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Goodbye" in proc.stdout or "Exiting" in proc.stdout
