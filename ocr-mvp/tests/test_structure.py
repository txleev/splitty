import json
from types import SimpleNamespace

import httpx
import pytest
from groq import BadRequestError

from structure import StructureError, structure_receipt


class FakeCompletions:
    """Returns queued responses in order and records every request it receives."""

    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.contents.pop(0)
        if isinstance(content, Exception):
            raise content
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_client(contents):
    completions = FakeCompletions(contents)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


VALID = {
    "items": [
        {"name": "Salad", "qty": 1, "unit_price": 14.0, "total_price": 14.0, "assigned_to": []},
        {"name": "Steak", "qty": 1, "unit_price": 32.0, "total_price": 32.0, "assigned_to": []},
    ],
    "subtotal": 46.0,
    "tax": 3.5,
    "tip": None,
    "total": 49.5,
    "currency": "USD",
    "warnings": [],
}


def test_valid_json_is_parsed_and_passes_reconciliation():
    client, completions = fake_client([json.dumps(VALID)])

    receipt = structure_receipt(client, ["1x Salad | 14.00", "Steak | 32.00"], note=None, model="m")

    assert [i.name for i in receipt.items] == ["Salad", "Steak"]
    assert receipt.total == 49.5
    assert receipt.warnings == []
    assert completions.calls[0]["temperature"] == 0
    assert completions.calls[0]["response_format"] == {"type": "json_object"}


def test_invalid_json_is_repaired_with_one_retry():
    client, completions = fake_client(["not json at all", json.dumps(VALID)])

    receipt = structure_receipt(client, ["Salad | 14.00"], model="m")

    assert len(completions.calls) == 2
    assert "did not match the schema" in completions.calls[1]["messages"][-1]["content"]
    assert len(receipt.items) == 2


def test_two_invalid_answers_raise_structure_error():
    client, _ = fake_client(["bad", "still bad"])

    with pytest.raises(StructureError):
        structure_receipt(client, ["Salad | 14.00"], model="m")


def test_totals_mismatch_becomes_warning_not_error():
    broken = dict(VALID, total=60.0)
    client, _ = fake_client([json.dumps(broken)])

    receipt = structure_receipt(client, ["Salad | 14.00"], model="m")

    assert len(receipt.warnings) == 1
    assert "total is 60.00" in receipt.warnings[0]


def test_note_is_sent_to_the_model():
    client, completions = fake_client([json.dumps(VALID)])

    structure_receipt(client, ["Salad | 14.00"], note="Jack and I had the salad", model="m")

    user_message = completions.calls[0]["messages"][1]["content"]
    assert "Jack and I had the salad" in user_message


def test_json_mode_rejection_falls_back_to_plain_reply():
    rejection = BadRequestError(
        "Failed to validate JSON",
        response=httpx.Response(400, request=httpx.Request("POST", "https://example.test")),
        body={"error": {"code": "json_validate_failed", "failed_generation": ""}},
    )
    client, completions = fake_client([rejection, json.dumps(VALID)])

    receipt = structure_receipt(client, ["Salad | 14.00"], model="m")

    assert "response_format" in completions.calls[0]
    assert "response_format" not in completions.calls[1]
    assert len(receipt.items) == 2


def test_json_wrapped_in_code_fence_is_extracted():
    fenced = "```json\n" + json.dumps(VALID) + "\n```"
    client, _ = fake_client([fenced])

    receipt = structure_receipt(client, ["Salad | 14.00"], model="m")

    assert [i.name for i in receipt.items] == ["Salad", "Steak"]


def test_missing_qty_is_derived_from_total_and_unit_price():
    item = {"name": "Chips", "qty": 0, "unit_price": 185, "total_price": 370,
            "assigned_to": [], "missing": ["qty"]}
    totals = {"subtotal": None, "tax": None, "tip": None, "total": None}
    client, _ = fake_client([json.dumps(dict(VALID, items=[item], **totals))])

    receipt = structure_receipt(client, ["Chips | 370"], model="m")

    assert receipt.items[0].qty == 2
    assert receipt.items[0].missing == []
    assert receipt.warnings == []


def test_qty_times_unit_price_mismatch_is_a_warning():
    item = {"name": "Chips", "qty": 2, "unit_price": 185, "total_price": 400,
            "assigned_to": [], "missing": []}
    client, _ = fake_client([json.dumps(dict(VALID, items=[item]))])

    receipt = structure_receipt(client, ["Chips | 400"], model="m")

    assert any("Chips" in w and "= 370.00" in w for w in receipt.warnings)
