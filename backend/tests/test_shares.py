import random
from fractions import Fraction

import pytest

from shares import compute_shares, split_by


def test_split_by_follows_the_weights():
    assert split_by(1000, {1: 1, 2: 3}) == {1: 250, 2: 750}


def test_three_ways_gives_the_extra_cent_to_the_earlier_member():
    assert split_by(1000, {1: 1, 2: 1, 3: 1}) == {1: 334, 2: 333, 3: 333}


def test_zero_weight_gets_nothing():
    assert split_by(100, {1: 0, 2: 1}) == {1: 0, 2: 100}


def test_equal_fallback_when_no_weight_is_positive():
    assert split_by(10, {1: 0, 2: 0}, fallback=[1, 2]) == {1: 5, 2: 5}


def test_nothing_to_split_between_is_an_error():
    with pytest.raises(ValueError):
        split_by(10, {})


def test_every_split_adds_up_and_no_part_is_more_than_a_cent_off():
    rng = random.Random(7)
    for _ in range(3000):
        total = rng.randint(-50_000, 50_000)
        weights = {key: rng.randint(0, 9) for key in range(1, rng.randint(2, 7))}
        if sum(weights.values()) == 0:
            weights[1] = 1

        parts = split_by(total, weights)

        assert sum(parts.values()) == total
        weight_sum = sum(weights.values())
        for key, weight in weights.items():
            exact = Fraction(total * weight, weight_sum)
            assert abs(parts[key] - exact) < 1


def test_bill_from_the_claims_example():
    # Salad 14.00 for Ana, Steak 2 x 16.00 for Ben, tax 3.50. Ana's tax share rounds up.
    shares = compute_shares(
        items=[(1400, {1: 1}), (3200, {2: 2})],
        member_ids=[1, 2],
        tax_minor=350,
        tip_minor=0,
    )

    assert (shares[1].subtotal, shares[1].tax, shares[1].total) == (1400, 107, 1507)
    assert (shares[2].subtotal, shares[2].tax, shares[2].total) == (3200, 243, 3443)


def test_a_shared_line_is_split_by_claimed_quantity():
    # One line of 3 portions costs 10.00. Ana takes 2 and Ben takes 1.
    shares = compute_shares(
        items=[(1000, {1: 2, 2: 1})], member_ids=[1, 2], tax_minor=0, tip_minor=0
    )

    assert shares[1].subtotal == 667
    assert shares[2].subtotal == 333


def test_tax_and_tip_follow_each_guests_subtotal():
    shares = compute_shares(
        items=[(3000, {1: 1}), (1000, {2: 1})], member_ids=[1, 2], tax_minor=0, tip_minor=400
    )

    assert shares[1].tip == 300
    assert shares[2].tip == 100


def test_tax_is_split_evenly_when_nothing_has_a_subtotal():
    shares = compute_shares(
        items=[(0, {1: 1})], member_ids=[1, 2], tax_minor=10, tip_minor=0
    )

    assert [shares[1].tax, shares[2].tax] == [5, 5]


def test_random_bills_always_add_up_to_the_total():
    rng = random.Random(11)
    for _ in range(1000):
        member_ids = list(range(1, rng.randint(1, 5) + 1))
        items = []
        for _ in range(rng.randint(1, 6)):
            quantity = rng.randint(1, 5)
            claims = dict.fromkeys(member_ids, 0)
            for _ in range(quantity):
                claims[rng.choice(member_ids)] += 1
            items.append((rng.randint(0, 100_000), {m: q for m, q in claims.items() if q}))
        tax = rng.randint(0, 5_000)
        tip = rng.randint(0, 5_000)

        shares = compute_shares(
            items=items, member_ids=member_ids, tax_minor=tax, tip_minor=tip
        )

        subtotal = sum(total for total, _ in items)
        assert sum(s.subtotal for s in shares.values()) == subtotal
        assert sum(s.tax for s in shares.values()) == tax
        assert sum(s.tip for s in shares.values()) == tip
        assert sum(s.total for s in shares.values()) == subtotal + tax + tip


def test_unclaimed_units_do_not_raise_a_guests_share():
    # Two steaks at 16.00 each. Ana took one, and the other is still free.
    shares = compute_shares(
        items=[(3200, {1: 1}, 2)], member_ids=[1], tax_minor=0, tip_minor=0
    )

    assert shares[1].subtotal == 1600


def test_tax_and_tip_follow_the_whole_bill_not_only_the_claimed_part():
    # Ana has 1000 of a 4000 bill. She pays a quarter of the 400 tax and 200 tip.
    shares = compute_shares(
        items=[(1000, {1: 1}, 1), (3000, {}, 1)],
        member_ids=[1],
        tax_minor=400,
        tip_minor=200,
    )

    assert (shares[1].subtotal, shares[1].tax, shares[1].tip) == (1000, 100, 50)


def test_a_guest_amount_is_the_same_before_and_after_the_others_claim():
    alone = compute_shares(
        items=[(1000, {1: 1}, 1), (3000, {}, 3)],
        member_ids=[1],
        tax_minor=400,
        tip_minor=0,
    )
    everyone = compute_shares(
        items=[(1000, {1: 1}, 1), (3000, {2: 3}, 3)],
        member_ids=[1, 2],
        tax_minor=400,
        tip_minor=0,
    )

    assert alone[1] == everyone[1]
    assert everyone[1].total + everyone[2].total == 4400


def test_claims_from_a_name_that_is_not_listed_still_take_their_part():
    shares = compute_shares(
        items=[(3000, {1: 1, 2: 2}, 3)], member_ids=[1], tax_minor=0, tip_minor=0
    )

    assert shares[1].subtotal == 1000


def test_an_equal_split_with_nobody_in_charges_nobody():
    shares = compute_shares(items=[(900, {})], member_ids=[1], tax_minor=0, tip_minor=0)

    assert shares[1].subtotal == 0
