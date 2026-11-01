"""Tests for common.tables module."""

from common.tables import format_table


def test_format_table_renders_headers_and_rows() -> None:
    headers = ["ID", "Name", "Balance"]
    rows = [
        [1, "Alice", "$50.00"],
        [2, "Bob", "$120.50"],
    ]
    alignments = ["R", "L", "R"]
    table_str = format_table(headers, rows, alignments)
    assert "Alice" in table_str
    assert "Bob" in table_str
    assert "+---" in table_str


def test_format_table_empty_rows() -> None:
    headers = ["ID", "Name"]
    table_str = format_table(headers, [])
    assert "No records found" in table_str
