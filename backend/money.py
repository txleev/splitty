from decimal import ROUND_HALF_UP, Decimal


def to_minor(amount: float | None) -> int | None:
    """Convert a decimal amount from the parser (14.5) to minor units (1450), rounding half up.

    Going through str() keeps the decimal value the parser wrote, so 10.005 becomes 1001
    instead of inheriting binary float error.
    """
    if amount is None:
        return None
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_minor(amount: int) -> str:
    """Minor units to a display string: 1450 -> "14.50"."""
    return f"{Decimal(amount) / 100:.2f}"
