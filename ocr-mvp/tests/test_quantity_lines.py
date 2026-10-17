from lines import attach_quantity_lines


def test_quantity_line_above_item_is_attached():
    lines = [
        "T. CHIPS BBQ(11) | 499 | B00",
        "2,000 db | * | 185,00 Ft /db",
        "CSOKIPUD. HABBAL | 370 | B00",
    ]
    assert attach_quantity_lines(lines) == [
        "T. CHIPS BBQ(11) | 499 | B00",
        "CSOKIPUD. HABBAL | 370 | B00 | qty=2 unit_price=185",
    ]


def test_weighed_quantity_below_item_is_attached():
    lines = [
        "CSOKIPUD. HABBAL | 370 | B00",
        "1,038 kg | * | 699,00 Ft /kg",
        "BANÁN KG | 726 | C00",
    ]
    assert attach_quantity_lines(lines) == [
        "CSOKIPUD. HABBAL | 370 | B00",
        "BANÁN KG | 726 | C00 | qty=1.038 unit_price=699",
    ]


def test_amount_with_tax_code_attached_to_the_same_item():
    lines = [
        "1,080 kg | * | 484,00 Ft /kg",
        "ALMA, GALA KG | 523 C00",
    ]
    assert attach_quantity_lines(lines) == ["ALMA, GALA KG | 523 C00 | qty=1.08 unit_price=484"]


def test_quantity_line_without_matching_neighbour_is_kept():
    lines = [
        "2 | * | 5",
        "B | 99",
    ]
    assert attach_quantity_lines(lines) == lines


def test_quantity_line_matching_both_neighbours_is_kept():
    lines = [
        "A | 10",
        "2 | * | 5",
        "B | 10",
    ]
    assert attach_quantity_lines(lines) == lines


def test_numbers_inside_the_item_name_are_not_amounts():
    lines = [
        "2030 ÉRD FIASTYUK UTCA 3",
        "2 | * | 5",
    ]
    # 2030 is part of the name, so it cannot match 2 x 5 and the quantity line stays.
    assert attach_quantity_lines(lines) == lines


def test_lines_without_quantity_are_untouched():
    lines = ["DM KFT.", "OSSZESEN: | 8606 Ft", "AUTH CODE: | MYICDM"]
    assert attach_quantity_lines(lines) == lines
