"""Integer minor-unit financial arithmetic and formatting utilities."""

import math


def cents_to_display(cents: int, symbol: str = "$") -> str:
    """Format integer cents into a two-decimal currency string (e.g. 1250 -> '$12.50')."""
    if not isinstance(cents, int):
        raise TypeError(f"Cents must be an integer, got {type(cents).__name__}")
    is_negative = cents < 0
    abs_cents = abs(cents)
    dollars = abs_cents // 100
    remainder = abs_cents % 100
    formatted = f"{symbol}{dollars:,}.{remainder:02d}"
    return f"-{formatted}" if is_negative else formatted


def parse_money_to_cents(amount_str: str, allow_negative: bool = False) -> int:
    """Parse user currency string into integer cents without float precision loss."""
    raw = amount_str.strip().lstrip("$").replace(",", "").strip()
    if not raw:
        raise ValueError("Amount cannot be empty.")

    try:
        val_float = float(raw)
    except ValueError as err:
        raise ValueError(f"Invalid numeric input '{amount_str}'.") from err

    if not math.isfinite(val_float):
        raise ValueError("Amount must be a finite number (NaN and Inf are not permitted).")

    if not allow_negative and val_float < 0:
        raise ValueError("Negative amounts are not permitted.")

    if "." in raw:
        parts = raw.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid decimal format '{amount_str}'.")
        whole_str, frac_str = parts
        if len(frac_str) > 2:
            raise ValueError("Amount cannot specify more than 2 decimal places.")
        frac_str = frac_str.ljust(2, "0")
        is_neg = whole_str.startswith("-")
        whole = int(whole_str.lstrip("-") or "0")
        cents = whole * 100 + int(frac_str)
        return -cents if is_neg else cents
    else:
        is_neg = raw.startswith("-")
        whole = int(raw.lstrip("-") or "0")
        cents = whole * 100
        return -cents if is_neg else cents
