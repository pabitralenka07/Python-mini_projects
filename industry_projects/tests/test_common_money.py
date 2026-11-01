"""Tests for common.money module."""

import pytest

from common.money import cents_to_display, parse_money_to_cents


def test_cents_to_display() -> None:
    assert cents_to_display(0) == "$0.00"
    assert cents_to_display(150) == "$1.50"
    assert cents_to_display(125000) == "$1,250.00"
    assert cents_to_display(-450) == "-$4.50"


def test_parse_money_valid_formats() -> None:
    assert parse_money_to_cents("10") == 1000
    assert parse_money_to_cents("10.5") == 1050
    assert parse_money_to_cents("10.50") == 1050
    assert parse_money_to_cents("$1,250.99") == 125099
    assert parse_money_to_cents("0") == 0


def test_parse_money_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_money_to_cents("   ")

    with pytest.raises(ValueError, match="Invalid numeric input"):
        parse_money_to_cents("abc")

    with pytest.raises(ValueError, match="finite number"):
        parse_money_to_cents("nan")

    with pytest.raises(ValueError, match="finite number"):
        parse_money_to_cents("inf")

    with pytest.raises(ValueError, match="Negative amounts"):
        parse_money_to_cents("-10.00")

    with pytest.raises(ValueError, match="more than 2 decimal places"):
        parse_money_to_cents("10.555")
