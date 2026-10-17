from lines import group_lines


def cell(text, x1, y1, x2, y2):
    return {"text": text, "score": 0.99, "box": [x1, y1, x2, y2]}


def test_empty():
    assert group_lines([]) == []


def test_cells_on_same_row_are_joined_left_to_right():
    items = [
        cell("14.00", 300, 102, 340, 120),
        cell("1x Salad", 10, 100, 120, 118),
    ]
    assert group_lines(items) == ["1x Salad | 14.00"]


def test_rows_are_ordered_top_to_bottom():
    items = [
        cell("Tax 3.50", 10, 200, 120, 218),
        cell("Steak", 10, 100, 80, 118),
        cell("32.00", 300, 101, 340, 119),
        cell("Total", 10, 300, 70, 318),
    ]
    assert group_lines(items) == ["Steak | 32.00", "Tax 3.50", "Total"]


def test_small_vertical_jitter_stays_on_one_row():
    items = [
        cell("Salad", 10, 100, 80, 120),
        cell("14.00", 300, 106, 340, 126),
    ]
    assert group_lines(items) == ["Salad | 14.00"]


def test_thousands_split_across_cells_is_one_number():
    items = [
        cell("MASCULAN 4", 10, 100, 120, 118),
        cell("1", 130, 100, 135, 118),
        cell("799", 140, 100, 170, 118),
        cell("C0O", 180, 100, 210, 118),
    ]
    assert group_lines(items) == ["MASCULAN 4 | 1799 | C0O"]


def test_distant_cells_are_not_merged():
    items = [
        cell("MASCULAN 4", 10, 100, 120, 118),
        cell("2", 130, 100, 135, 118),
        cell("799", 200, 100, 230, 118),
    ]
    assert group_lines(items) == ["MASCULAN 4 | 2 | 799"]


def test_thousands_with_decimals():
    items = [
        cell("Wine", 10, 100, 60, 118),
        cell("1", 70, 100, 75, 118),
        cell("799,50", 80, 100, 120, 118),
    ]
    assert group_lines(items) == ["Wine | 1799,50"]


def test_quantity_with_leading_zero_unit_price_is_not_merged():
    items = [
        cell("BRADOLIFE", 10, 100, 110, 118),
        cell("13", 120, 100, 135, 118),
        cell("009", 137, 100, 155, 118),
    ]
    assert group_lines(items) == ["BRADOLIFE | 13 | 009"]


def test_chained_thousands_split():
    items = [
        cell("1", 10, 100, 15, 118),
        cell("234", 20, 100, 35, 118),
        cell("567", 40, 100, 55, 118),
    ]
    assert group_lines(items) == ["1234567"]


def test_single_cell_thousands_space_is_removed():
    items = [cell("Total 8 606 Ft", 10, 100, 200, 118)]
    assert group_lines(items) == ["Total 8606 Ft"]


def test_numbers_that_are_not_thousands_are_unchanged():
    items = [
        cell("2030 ÉRD FIASTYUK UTCA 3", 10, 100, 200, 118),
        cell("433783******9550", 10, 200, 200, 218),
        cell("+36 20 123 4567", 10, 300, 200, 318),
    ]
    assert group_lines(items) == [
        "2030 ÉRD FIASTYUK UTCA 3",
        "433783******9550",
        "+36 20 123 4567",
    ]
