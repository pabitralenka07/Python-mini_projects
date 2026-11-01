"""Tests for common.input_helpers module."""

import pytest

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_choice,
    prompt_float,
    prompt_int,
    safe_input,
)


def test_safe_input_strips_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "   hello world   ")
    assert safe_input("Prompt: ") == "hello world"


def test_safe_input_rejects_overlong(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = iter(["a" * 50, "valid"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert safe_input("Prompt: ", max_length=10) == "valid"


def test_safe_input_eof_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_eof(_: str) -> str:
        raise EOFError()

    monkeypatch.setattr("builtins.input", raise_eof)
    with pytest.raises(UserExitException):
        safe_input("Prompt: ")


def test_prompt_int_range_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = iter(["not_a_num", "1", "15", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    res = prompt_int("Enter int", min_val=2, max_val=10)
    assert res == 5


def test_prompt_float_rejects_nan_inf(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = iter(["nan", "inf", "-inf", "4.5"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    res = prompt_float("Enter float", min_val=0.0)
    assert res == 4.5


def test_prompt_choice_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = iter(["invalid", "SAVINGS"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert prompt_choice("Account type", ["savings", "current"]) == "savings"


def test_confirm_action(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert confirm_action("Proceed?") is True

    monkeypatch.setattr("builtins.input", lambda _: "YES")
    assert confirm_action("Proceed?") is True

    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert confirm_action("Proceed?") is False

    monkeypatch.setattr("builtins.input", lambda _: "random")
    assert confirm_action("Proceed?") is False

    def raise_eof(_: str) -> str:
        raise EOFError()

    monkeypatch.setattr("builtins.input", raise_eof)
    assert confirm_action("Proceed?") is False
