from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from .models import Bill, SplitRequest, SplitResponse, PersonBreakdown


CENT = Decimal("0.01")


def money(value: float | Decimal) -> float:
    return float(Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP))


def split_amount(amount: float, weights: dict[str, float]) -> dict[str, float]:
    total_weight = sum(max(0.0, v) for v in weights.values())
    if total_weight <= 0 or amount == 0:
        return {k: 0.0 for k in weights}
    raw = {k: amount * max(0.0, v) / total_weight for k, v in weights.items()}
    rounded = {k: money(v) for k, v in raw.items()}
    # Put rounding residue on the largest share so totals remain exact to cents.
    residue = money(amount - sum(rounded.values()))
    if rounded:
        target = max(rounded, key=rounded.get)
        rounded[target] = money(rounded[target] + residue)
    return rounded


def calculate_split(req: SplitRequest) -> SplitResponse:
    members = [m.strip() for m in req.members if m.strip()]
    if not members:
        raise ValueError("At least one member is required")

    assignments = {a.item_index: a for a in req.assignments}
    food = {m: 0.0 for m in members}

    for idx, item in enumerate(req.bill.items):
        assignment = assignments.get(idx)
        if not assignment:
            continue

        weights = {p.member: p.portions for p in assignment.portions if p.member in members}
        if not weights:
            continue

        parts = split_amount(item.total_price, weights)
        for member, amount in parts.items():
            food[member] = money(food[member] + amount)

    # Charges follow what each person actually ate.
    discount = split_amount(req.bill.discount, food)
    service = split_amount(req.bill.service_charge, food)
    cgst = split_amount(req.bill.cgst, food)
    sgst = split_amount(req.bill.sgst, food)
    other_tax = split_amount(req.bill.other_tax, food)

    people = []
    for member in members:
        total = money(
            food[member]
            - discount[member]
            + service[member]
            + cgst[member]
            + sgst[member]
            + other_tax[member]
        )
        people.append(
            PersonBreakdown(
                member=member,
                food_subtotal=money(food[member]),
                discount_share=money(discount[member]),
                service_charge_share=money(service[member]),
                cgst_share=money(cgst[member]),
                sgst_share=money(sgst[member]),
                other_tax_share=money(other_tax[member]),
                total=total,
            )
        )

    calculated = money(sum(p.total for p in people))
    bill_total = (
        req.bill.printed_total
        if req.bill.printed_total is not None
        else money(req.bill.subtotal - req.bill.discount + req.bill.service_charge
                   + req.bill.cgst + req.bill.sgst + req.bill.other_tax)
    )
    difference = money(calculated - bill_total)

    warning = None
    if req.bill.printed_total is not None:
        expected = money(
            req.bill.subtotal - req.bill.discount + req.bill.service_charge
            + req.bill.cgst + req.bill.sgst + req.bill.other_tax
        )
        if abs(expected - req.bill.printed_total) > 0.01:
            warning = (
                f"Printed total mismatch: printed ₹{req.bill.printed_total:.2f}, "
                f"calculated from bill components ₹{expected:.2f}."
            )

    return SplitResponse(
        people=people,
        bill_total=money(bill_total),
        calculated_total=calculated,
        difference=difference,
        total_matches=abs(difference) <= 0.01,
        warning=warning,
    )
