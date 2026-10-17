import re

from ids import hash_token, new_session_id, new_token
from money import format_minor, to_minor
from schemas import ItemOut
from sessions import find_problems


def test_to_minor_converts_decimal_amounts():
    assert to_minor(14.0) == 1400
    assert to_minor(14.5) == 1450
    assert to_minor(0.07) == 7


def test_to_minor_rounds_half_up_without_float_error():
    # 10.005 is 10.00499999... in binary floats; the decimal string gives the expected 1001.
    assert to_minor(10.005) == 1001


def test_to_minor_passes_none_through():
    assert to_minor(None) is None


def test_format_minor_shows_two_decimals():
    assert format_minor(1450) == "14.50"
    assert format_minor(7) == "0.07"
    assert format_minor(-5) == "-0.05"


def test_session_id_is_11_url_safe_characters():
    for _ in range(1000):
        assert re.fullmatch(r"[A-Za-z0-9_-]{11}", new_session_id())


def test_session_ids_do_not_repeat_in_a_sample():
    ids = {new_session_id() for _ in range(10_000)}
    assert len(ids) == 10_000


def test_token_hash_is_deterministic_and_not_the_token():
    token = new_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
    assert len(hash_token(token)) == 64


def item(name="Tea", total=100, missing=(), quantity=1, split_equally=False):
    return ItemOut(
        id=1,
        position=1,
        name=name,
        quantity=quantity,
        unit_price_minor=total,
        total_minor=total,
        missing=list(missing),
        preassigned_names=[],
        split_equally=split_equally,
        split_count=None,
        remaining=quantity,
        claims=[],
    )


def problems(items, currency="KGS", subtotal=100, tax=None, tip=None, total=100):
    return find_problems(
        items=items,
        currency=currency,
        subtotal_minor=subtotal,
        tax_minor=tax,
        tip_minor=tip,
        total_minor=total,
    )


def test_consistent_receipt_has_no_problems():
    assert problems([item(total=100)]) == []


def test_tax_and_tip_count_toward_the_total():
    assert problems([item(total=100)], tax=10, tip=5, total=115) == []


def test_missing_fields_are_reported_per_item():
    assert problems([item("Tea", missing=["qty"])]) == ["'Tea' is missing: qty."]


def test_fractional_quantity_is_reported():
    assert problems([item("Cheese", quantity=0.75)]) == [
        "'Cheese' has quantity 0.75. Claims need whole numbers: "
        "set the quantity to 1 and enter the line total."
    ]


def test_zero_quantity_is_reported():
    assert problems([item("Free", quantity=0)]) == [
        "'Free' has no quantity. Set it to 1 or more."
    ]


def test_items_must_add_up_to_the_subtotal():
    assert problems([item(total=90)], subtotal=100, total=100) == [
        "Items add up to 0.90 but the subtotal is 1.00."
    ]


def test_total_must_match_subtotal_tax_and_tip():
    assert problems([item(total=100)], tax=10, total=100) == [
        "Subtotal, tax and tip add up to 1.10 but the total is 1.00."
    ]


def test_unset_currency_subtotal_and_total_are_reported():
    assert problems([item(total=100)], currency=None, subtotal=None, total=None) == [
        "Currency is not set.",
        "Subtotal is not set.",
        "Total is not set.",
    ]


def test_receipt_without_items_is_reported():
    assert problems([], subtotal=0, total=0) == ["The receipt has no items."]


def test_fractional_quantity_is_fine_for_an_equal_split():
    problems = find_problems(
        items=[item(quantity=0.5, split_equally=True)],
        currency="EUR",
        subtotal_minor=100,
        tax_minor=0,
        tip_minor=0,
        total_minor=100,
    )

    assert problems == []
