from app.models import Bill, BillItem, Confidence, SplitRequest, ItemAssignment, Portion
from app.splitter import calculate_split


def bill():
    return Bill(
        items=[
            BillItem(name="Biryani", quantity=2, unit_price=500, total_price=1000,
                     confidence=Confidence(value=1)),
            BillItem(name="Coke", quantity=1, unit_price=100, total_price=100,
                     confidence=Confidence(value=1)),
        ],
        subtotal=1100,
        discount=0,
        service_charge=110,
        cgst=99,
        sgst=99,
        other_tax=0,
        printed_total=1408,
        overall_confidence=Confidence(value=1),
    )


def test_proportional_charges():
    req = SplitRequest(
        bill=bill(),
        members=["A", "B"],
        assignments=[
            ItemAssignment(item_index=0, portions=[Portion(member="A", portions=1), Portion(member="B", portions=1)]),
            ItemAssignment(item_index=1, portions=[Portion(member="B", portions=1)]),
        ],
    )
    out = calculate_split(req)
    a, b = out.people
    assert a.food_subtotal == 500
    assert b.food_subtotal == 600
    assert a.service_charge_share == 50
    assert b.service_charge_share == 60
    assert a.cgst_share == 45
    assert b.cgst_share == 54
    assert a.total == 640
    assert b.total == 768
    assert out.calculated_total == 1408
    assert out.total_matches


def test_detects_wrong_printed_total():
    b = bill()
    b.printed_total = 1400
    req = SplitRequest(
        bill=b,
        members=["A"],
        assignments=[
            ItemAssignment(item_index=0, portions=[Portion(member="A", portions=1)]),
            ItemAssignment(item_index=1, portions=[Portion(member="A", portions=1)]),
        ],
    )
    out = calculate_split(req)
    assert not out.total_matches
    assert out.warning
