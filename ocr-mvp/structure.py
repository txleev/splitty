import logging
import os
from time import sleep
from typing import Optional

from groq import APITimeoutError, BadRequestError, Groq, RateLimitError
from pydantic import BaseModel, ValidationError

log = logging.getLogger("ocr.structure")

DEFAULT_MODEL = "openai/gpt-oss-20b"
TOTAL_TOLERANCE = 0.05


class StructureError(Exception):
    pass


class ReceiptItem(BaseModel):
    name: str
    qty: float = 1
    unit_price: Optional[float] = None
    total_price: float
    assigned_to: list[str] = []
    missing: list[str] = []


class ParsedReceipt(BaseModel):
    items: list[ReceiptItem]
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tip: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    warnings: list[str] = []


SYSTEM_PROMPT = """You extract structured data from OCR output of a receipt.
The input is a list of text lines. A line may hold an item name and its price separated by " | ".

Return ONLY a JSON object with this shape:
{
  "items": [{"name": string, "qty": number, "unit_price": number, "total_price": number, "assigned_to": [string], "missing": [string]}],
  "subtotal": number|null,
  "tax": number|null,
  "tip": number|null,
  "total": number|null,
  "currency": string|null,
  "warnings": [string]
}

Rules:
- Fix obvious OCR typos in item names. Never invent items or prices that are not on the receipt.
- Do not treat tax, service charge, subtotal, total, change, card or payment lines as items.
- Return plain numbers: no currency symbols, and convert decimal commas to dots.
- A space between digit groups ("1 799", "8 606") is a thousands separator, so the number is 1799 or 8606. It is not a quantity followed by a price.
- "assigned_to" is filled only when the user note explicitly says who ordered an item. Otherwise return [].
- An item line has the form "name | amount | tax code", or "name | qty | price | tax code". The amount on the item's own line is total_price, and it must be filled whenever such an amount is present.
- If the line ends with "qty=N unit_price=P", use N as qty and P as unit_price. Do not look for another quantity.
- If a priced line has no quantity and no qty= marker, use qty 1 and unit_price equal to total_price.
- If an item's qty, unit_price or total_price is not clearly on the receipt, set that field to 0 and list it in that item's "missing" array (for example ["qty", "unit_price"]). Do not guess a value to fill it. Use an empty "missing" array when all fields were found.
- If something is unclear or you had to guess, describe it in "warnings" instead of guessing silently.
"""


def make_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Put it in .env and restart the service.")
    return Groq(api_key=api_key)


def _build_user_message(grouped_lines, note):
    lines = "\n".join(grouped_lines) or "(no text recognized)"
    return f"Receipt lines:\n{lines}\n\nUser note (may be empty):\n{note or '(none)'}"


def _complete(client, messages, model, json_mode):
    kwargs = {"model": model, "messages": messages, "temperature": 0, "timeout": 20}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def _is_json_validation_error(error):
    inner = error.body.get("error") if isinstance(error.body, dict) else None
    return isinstance(inner, dict) and inner.get("code") == "json_validate_failed"


def _chat(client, messages, model):
    # Retry only transient failures. Each retry waits longer than the last.
    for attempt in range(3):
        try:
            try:
                return _complete(client, messages, model, json_mode=True)
            except BadRequestError as e:
                if not _is_json_validation_error(e):
                    raise
                # JSON mode rejected the reply. Ask again without it; the JSON is extracted later.
                log.warning("JSON mode rejected the reply, retrying without it: %s", e)
                return _complete(client, messages, model, json_mode=False)
        except (RateLimitError, APITimeoutError) as e:
            log.warning("Groq transient error on attempt %d: %s", attempt + 1, e)
            if attempt == 2:
                raise StructureError(f"Groq unavailable after retries: {e}") from e
            sleep(2**attempt)
    raise StructureError("unreachable")


def _extract_json(raw):
    """Take the JSON object out of a reply, even when it is wrapped in a code fence or prose."""
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start : end + 1] if 0 <= start < end else raw


def _fill_item(item, receipt):
    """Derive one missing field from the other two (qty x unit = total) and check the item."""
    qty, unit, total = item.qty, item.unit_price or 0, item.total_price
    derived = []
    if total and qty and not unit:
        unit, derived = total / qty, ["unit_price"]
    elif total and unit and not qty:
        qty, derived = total / unit, ["qty"]
    elif qty and unit and not total:
        total, derived = qty * unit, ["total_price"]

    if derived:
        item.qty, item.unit_price, item.total_price = round(qty, 3), round(unit, 2), round(total, 2)
        item.missing = [field for field in item.missing if field not in derived]

    if item.qty and item.unit_price and item.total_price:
        expected = item.qty * item.unit_price
        if abs(expected - item.total_price) > max(TOTAL_TOLERANCE, 0.005 * item.total_price):
            receipt.warnings.append(
                f"{item.name}: qty {item.qty:g} x unit price {item.unit_price:g} = {expected:.2f}, "
                f"but total is {item.total_price:g}"
            )


def _reconcile(receipt):
    """Check the arithmetic in code and record mismatches as warnings, not errors."""
    for item in receipt.items:
        _fill_item(item, receipt)

    items_sum = round(sum(item.total_price for item in receipt.items), 2)

    if receipt.subtotal is not None and abs(items_sum - receipt.subtotal) > TOTAL_TOLERANCE:
        receipt.warnings.append(
            f"Items sum to {items_sum:.2f} but subtotal is {receipt.subtotal:.2f}"
        )

    if receipt.total is not None:
        base = receipt.subtotal if receipt.subtotal is not None else items_sum
        expected = base + (receipt.tax or 0) + (receipt.tip or 0)
        if abs(expected - receipt.total) > TOTAL_TOLERANCE:
            receipt.warnings.append(
                f"Subtotal, tax and tip give {expected:.2f} but total is {receipt.total:.2f}"
            )
    return receipt


def structure_receipt(client, grouped_lines, note=None, model=None) -> ParsedReceipt:
    model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(grouped_lines, note)},
    ]

    # One repair attempt: send the validation error back so the model can fix its JSON.
    for attempt in range(2):
        raw = _chat(client, messages, model)
        try:
            receipt = ParsedReceipt.model_validate_json(_extract_json(raw))
        except ValidationError as e:
            log.warning("Invalid structured output on attempt %d: %s", attempt + 1, e)
            messages = messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": f"Your JSON did not match the schema:\n{e}\nReturn corrected JSON only.",
                },
            ]
            continue
        return _reconcile(receipt)

    raise StructureError("Model did not return valid receipt JSON after one repair attempt")
