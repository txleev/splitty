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


# Stands in for whatever nobody has claimed yet. It is larger than any member id, so on a tie
# the guests get the odd cent and the unclaimed part does not.
UNCLAIMED = 2**62


def compute_shares(
    *,
    items: list[tuple],
    member_ids: list[int],
    tax_minor: int,
    tip_minor: int,
) -> dict[int, Share]:
    """Each listed guest's share of the bill, whoever else has claimed so far.

    `items` holds (line total, {member_id: claimed quantity}) pairs, with an optional third value:
    the number of units on the line. With it, units nobody has claimed yet stay unclaimed instead
    of being spread over the guests who did claim, so a guest's amount does not move while
    others are still choosing. Without it the claims are taken to cover the whole line, as for an
    equal split, where every claim has the same weight.

    Tax and tip are split in proportion to each guest's subtotal, with the unclaimed part of the
    bill counted too. When everything is claimed, the parts add up to the bill exactly.
    """
    subtotal: dict[int, int] = {member_id: 0 for member_id in member_ids}
    bill_subtotal = 0
    for line_total, claims, *rest in items:
        bill_subtotal += line_total
        units = rest[0] if rest else None
        weights = dict(claims)
        if units is not None and units > sum(claims.values()):
            weights[UNCLAIMED] = units - sum(claims.values())
        if not weights:
            continue
        for key, amount in split_by(line_total, weights).items():
            if key != UNCLAIMED:
                subtotal[key] = subtotal.get(key, 0) + amount

    unclaimed = max(bill_subtotal - sum(subtotal.values()), 0)
    tax = split_by(tax_minor, {**subtotal, UNCLAIMED: unclaimed}, fallback=member_ids)
    tip = split_by(tip_minor, {**subtotal, UNCLAIMED: unclaimed}, fallback=member_ids)
    return {
        member_id: Share(subtotal=subtotal[member_id], tax=tax[member_id], tip=tip[member_id])
        for member_id in member_ids
    }
