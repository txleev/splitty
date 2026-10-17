import re
from statistics import mean, median

# A thousands-grouped number such as "1" or "1 234" or "1 234 567".
THOUSANDS_HEAD = re.compile(r"\d{1,3}(?: \d{3})*")
# The last group of a thousands split: exactly 3 digits, optional decimal part.
# A leading 0 is not allowed: "009" after a qty "13" is a unit price, not a thousands group.
THOUSANDS_TAIL = re.compile(r"[1-9]\d{2}(?:[.,]\d{1,2})?")
# A thousands-grouped number inside a cell. Not part of a longer digit string,
# card number or phone-like sequence ("20 123 4567").
THOUSANDS_IN_TEXT = re.compile(r"(?<![\w*])\d{1,3}(?: \d{3})+(?![\d*]| \d)")

# Max horizontal gap between two cells of one number, as a fraction of the row height.
THOUSANDS_GAP_RATIO = 0.8


def _y_center(item):
    return (item["box"][1] + item["box"][3]) / 2


def _is_thousands_split(left, right, gap_limit):
    return (
        THOUSANDS_HEAD.fullmatch(left["text"]) is not None
        and THOUSANDS_TAIL.fullmatch(right["text"]) is not None
        and right["box"][0] - left["box"][2] <= gap_limit
    )


def _merge_thousands(row, gap_limit):
    """Join cells that OCR split at a thousands space ("1" + "799" -> "1 799")."""
    merged = []
    for cell in row:
        if merged and _is_thousands_split(merged[-1], cell, gap_limit):
            prev = merged[-1]
            merged[-1] = {
                "text": f"{prev['text']} {cell['text']}",
                "box": [
                    prev["box"][0],
                    min(prev["box"][1], cell["box"][1]),
                    cell["box"][2],
                    max(prev["box"][3], cell["box"][3]),
                ],
            }
        else:
            merged.append(cell)
    return merged


def _normalize_amount(text):
    """Drop the spaces inside thousands-grouped numbers: "8 606 Ft" -> "8606 Ft"."""
    return THOUSANDS_IN_TEXT.sub(lambda m: m.group().replace(" ", ""), text)


def group_lines(items):
    """Merge OCR cells that sit on the same visual row into "left | right" strings.

    Cells belong to one row when their vertical centers are within half a median
    cell height of the row's average center. Cells inside a row are ordered left to right.
    A thousands space split across two cells is joined into one number.
    """
    if not items:
        return []

    heights = [item["box"][3] - item["box"][1] for item in items]
    median_height = median(heights)
    tolerance = 0.5 * median_height
    gap_limit = THOUSANDS_GAP_RATIO * median_height

    rows = []
    for item in sorted(items, key=_y_center):
        if rows and abs(_y_center(item) - mean(_y_center(r) for r in rows[-1])) <= tolerance:
            rows[-1].append(item)
        else:
            rows.append([item])

    return [
        " | ".join(
            _normalize_amount(cell["text"])
            for cell in _merge_thousands(sorted(row, key=lambda c: c["box"][0]), gap_limit)
        )
        for row in rows
    ]


# A quantity line sits next to its item line and reads "2,000 db | * | 185,00 Ft /db".
QUANTITY_SEPARATORS = {"*", "x", "×", "X"}
QUANTITY_CELL = re.compile(r"(\d[\d.,]*)\s*[^\d\s]*")
UNIT_PRICE_CELL = re.compile(r"(\d[\d.,]*)(?:\s*Ft)?(?:\s*/\s*\w+)?")
LEADING_NUMBER = re.compile(r"\d[\d.,]*")
# Allowed rounding error when qty x unit price is compared with the printed amount.
ATTACH_TOLERANCE_RATIO = 0.005


def _readings(number_text):
    """Possible values of a number with . or , as separators: "2,000" is 2.0 or 2000."""
    parts = re.split(r"[.,]", number_text)
    if len(parts) == 1:
        return {float(number_text)}
    if len(parts) == 2:
        integer, fraction = parts
        readings = {float(f"{integer}.{fraction}")}
        if len(fraction) == 3:
            readings.add(float(integer + fraction))
        return readings
    if all(len(part) == 3 for part in parts[1:]):
        return {float("".join(parts))}
    return set()


def _quantity_line(line):
    """Return (qty readings, unit price readings) if the line is a quantity line, else None."""
    cells = [cell.strip() for cell in line.split(" | ")]
    if len(cells) != 3 or cells[1] not in QUANTITY_SEPARATORS:
        return None
    qty = QUANTITY_CELL.fullmatch(cells[0])
    price = UNIT_PRICE_CELL.fullmatch(cells[2])
    if not qty or not price:
        return None
    return _readings(qty.group(1)), _readings(price.group(1))


def _line_amounts(line):
    """Numbers printed after the item name, e.g. 370 in "CSOKIPUD. HABBAL | 370 | B00"."""
    amounts = set()
    for cell in line.split(" | ")[1:]:
        number = LEADING_NUMBER.match(cell.strip())
        if number:
            amounts |= _readings(number.group())
    return amounts


def _find_match(qty_readings, price_readings, amounts):
    for qty in sorted(qty_readings):
        for price in sorted(price_readings):
            for amount in sorted(amounts):
                if abs(qty * price - amount) <= max(1.0, ATTACH_TOLERANCE_RATIO * amount):
                    return qty, price
    return None


def attach_quantity_lines(lines):
    """Move each quantity line onto its item line as "qty=N unit_price=P".

    The quantity line may sit above or below its item. It is attached only when exactly
    one neighbouring item line has an amount equal to qty x unit price. Otherwise it is kept.
    """
    parsed = [_quantity_line(line) for line in lines]
    output = list(lines)
    dropped, attached = set(), set()

    for i, quantity in enumerate(parsed):
        if quantity is None:
            continue
        candidates = []
        for j in (i - 1, i + 1):
            if not 0 <= j < len(lines) or parsed[j] is not None or j in attached:
                continue
            match = _find_match(*quantity, _line_amounts(lines[j]))
            if match:
                candidates.append((j, match))
        if len(candidates) == 1:
            j, (qty, price) = candidates[0]
            output[j] = f"{lines[j]} | qty={qty:g} unit_price={price:g}"
            attached.add(j)
            dropped.add(i)

    return [line for k, line in enumerate(output) if k not in dropped]
