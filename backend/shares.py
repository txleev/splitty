"""Splitting a fully claimed bill into each guest's share. All amounts are integer minor units."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Share:
    subtotal: int
    tax: int
    tip: int

    @property
    def total(self) -> int:
        return self.subtotal + self.tax + self.tip


def split_by(
    total: int, weights: dict[int, int], fallback: list[int] | None = None
) -> dict[int, int]:
    """Split `total` in proportion to `weights`. The parts always add up to `total` exactly.

    Each part starts at its exact share rounded down. The leftover minor units go to the parts
    with the largest remainders. Ties go to the lower key, so the earlier joiner gets the extra cent.
    If no weight is positive, `fallback` keys share the total equally.
    """
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        if not fallback:
            raise ValueError("Nothing to split the amount between")
        weights = {key: 1 for key in fallback}
        weight_sum = len(fallback)

    parts = {key: total * weight // weight_sum for key, weight in weights.items()}
    leftover = total - sum(parts.values())
    by_remainder = sorted(weights, key=lambda key: (-(total * weights[key] % weight_sum), key))
    for key in by_remainder[:leftover]:
        parts[key] += 1
    return parts


def compute_shares(
    *,
    items: list[tuple[int, dict[int, int]]],
    member_ids: list[int],
    tax_minor: int,
    tip_minor: int,
) -> dict[int, Share]:
    """Each guest's share of a bill where every item is fully claimed.

    `items` holds (line total, {member_id: claimed quantity}) pairs. A guest's part of a line is
    their claimed quantity over the line's quantity, times the line total. Tax and tip are split
    in proportion to each guest's subtotal.
    """
    subtotal = {member_id: 0 for member_id in member_ids}
    for line_total, claims in items:
        for member_id, amount in split_by(line_total, claims).items():
            subtotal[member_id] += amount

    tax = split_by(tax_minor, subtotal, fallback=member_ids)
    tip = split_by(tip_minor, subtotal, fallback=member_ids)
    return {
        member_id: Share(subtotal=subtotal[member_id], tax=tax[member_id], tip=tip[member_id])
        for member_id in member_ids
    }
