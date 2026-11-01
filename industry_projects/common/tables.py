"""Aligned plain-text table formatter for clean console displays."""

from collections.abc import Sequence
from typing import Any


def format_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    alignments: Sequence[str] | None = None,
) -> str:
    """Format headers and rows into an aligned ASCII/Unicode text table.

    Args:
        headers: Column titles.
        rows: Sequence of rows, each containing cell data.
        alignments: Optional sequence of 'L' (left) or 'R' (right) alignments.
                    Defaults to 'L' for non-numeric and 'R' for numeric.
    """
    if not headers:
        return ""

    num_cols = len(headers)
    string_rows: list[list[str]] = []
    for row in rows:
        str_row = [str(item) if item is not None else "" for item in row]
        # Pad or truncate row to match num_cols
        if len(str_row) < num_cols:
            str_row.extend([""] * (num_cols - len(str_row)))
        else:
            str_row = str_row[:num_cols]
        string_rows.append(str_row)

    # Determine column widths
    col_widths = [len(h) for h in headers]
    for str_row in string_rows:
        for idx, cell in enumerate(str_row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    # Determine alignment if not provided
    if alignments is None:
        align_list = ["L"] * num_cols
    else:
        align_list = [a.upper() for a in alignments]
        if len(align_list) < num_cols:
            align_list.extend(["L"] * (num_cols - len(align_list)))

    def pad_cell(text: str, width: int, align: str) -> str:
        if align == "R":
            return text.rjust(width)
        return text.ljust(width)

    # Build border line
    sep_line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Header line
    header_line = (
        "| " + " | ".join(pad_cell(h, col_widths[i], "L") for i, h in enumerate(headers)) + " |"
    )

    lines = [sep_line, header_line, sep_line]

    if not string_rows:
        empty_msg = "(No records found)"
        total_inner = sum(col_widths) + 3 * (num_cols - 1)
        lines.append("| " + empty_msg.center(total_inner) + " |")
    else:
        for str_row in string_rows:
            row_str = (
                "| "
                + " | ".join(
                    pad_cell(str_row[i], col_widths[i], align_list[i]) for i in range(num_cols)
                )
                + " |"
            )
            lines.append(row_str)

    lines.append(sep_line)
    return "\n".join(lines)
