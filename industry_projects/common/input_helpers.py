"""Input handling helpers with clean EOF/KeyboardInterrupt exits and strict validation."""

import math
from typing import TypeVar

T = TypeVar("T")


class UserExitException(Exception):
    """Raised when user terminates input via EOF (Ctrl+D / Ctrl+Z) or KeyboardInterrupt."""

    pass


def safe_input(prompt: str, max_length: int = 120, allow_empty: bool = False) -> str:
    """Prompt user for text, validating length and handling EOF gracefully."""
    while True:
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nExiting input...")
            raise UserExitException("Input stream closed by user.") from None

        stripped = line.strip()
        if len(stripped) > max_length:
            msg = (
                f"Error: Input is too long ({len(stripped)} chars). "
                f"Maximum allowed is {max_length}."
            )
            print(msg)
            continue

        if not allow_empty and not stripped:
            print("Error: Input cannot be empty. Please enter a value.")
            continue

        return stripped


def prompt_int(
    prompt: str,
    min_val: int | None = None,
    max_val: int | None = None,
    default: int | None = None,
) -> int:
    """Prompt user for an integer within an optional range [min_val, max_val]."""
    suffix = f" [{default}]" if default is not None else ""
    full_prompt = f"{prompt}{suffix}: "

    while True:
        raw = safe_input(full_prompt, max_length=20, allow_empty=(default is not None))
        if not raw and default is not None:
            return default

        try:
            val = int(raw)
        except ValueError:
            print("Error: Invalid integer. Please enter whole numbers only.")
            continue

        if min_val is not None and val < min_val:
            print(f"Error: Value must be at least {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"Error: Value must be at most {max_val}.")
            continue

        return val


def prompt_float(
    prompt: str,
    min_val: float | None = None,
    max_val: float | None = None,
    default: float | None = None,
) -> float:
    """Prompt user for a finite float within an optional range."""
    suffix = f" [{default}]" if default is not None else ""
    full_prompt = f"{prompt}{suffix}: "

    while True:
        raw = safe_input(full_prompt, max_length=30, allow_empty=(default is not None))
        if not raw and default is not None:
            return default

        try:
            val = float(raw)
        except ValueError:
            print("Error: Invalid number format.")
            continue

        if not math.isfinite(val):
            print("Error: Value must be finite (NaN and Inf are not allowed).")
            continue

        if min_val is not None and val < min_val:
            print(f"Error: Value must be at least {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"Error: Value must be at most {max_val}.")
            continue

        return val


def prompt_choice(prompt: str, choices: list[str]) -> str:
    """Prompt user to select from a list of valid choices (case-insensitive matching)."""
    normalized_map = {c.strip().lower(): c for c in choices}
    display_choices = "/".join(choices)
    full_prompt = f"{prompt} ({display_choices}): "

    while True:
        raw = safe_input(full_prompt, max_length=50)
        match = normalized_map.get(raw.lower())
        if match is not None:
            return match
        print(f"Error: Invalid choice '{raw}'. Expected one of: {', '.join(choices)}.")


def confirm_action(prompt: str) -> bool:
    """Prompt user for confirmation of a destructive action.

    Accepts only 'y' or 'yes' (case-insensitive).
    EOF or any other input is strictly treated as 'no'.
    """
    full_prompt = f"{prompt} (yes/no): "
    try:
        line = input(full_prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nOperation cancelled.")
        return False

    return line in ("y", "yes")
