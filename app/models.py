from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class Confidence(BaseModel):
    value: float = Field(ge=0, le=1)
    note: Optional[str] = None


class BillItem(BaseModel):
    name: str
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)
    total_price: float = Field(default=0, ge=0)
    confidence: Confidence = Field(default_factory=lambda: Confidence(value=0.5))

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return v.strip()


class Bill(BaseModel):
    restaurant_name: Optional[str] = None
    currency: str = "INR"
    items: list[BillItem] = Field(default_factory=list)
    subtotal: float = Field(default=0, ge=0)
    discount: float = Field(default=0, ge=0)
    service_charge: float = Field(default=0, ge=0)
    cgst: float = Field(default=0, ge=0)
    sgst: float = Field(default=0, ge=0)
    other_tax: float = Field(default=0, ge=0)
    printed_total: Optional[float] = Field(default=None, ge=0)
    overall_confidence: Confidence = Field(
        default_factory=lambda: Confidence(value=0.5)
    )


class Portion(BaseModel):
    member: str
    portions: float = Field(default=0, ge=0)


class ItemAssignment(BaseModel):
    item_index: int = Field(ge=0)
    portions: list[Portion] = Field(default_factory=list)


class SplitRequest(BaseModel):
    bill: Bill
    members: list[str] = Field(min_length=1)
    assignments: list[ItemAssignment] = Field(default_factory=list)


class PersonBreakdown(BaseModel):
    member: str
    food_subtotal: float
    discount_share: float
    service_charge_share: float
    cgst_share: float
    sgst_share: float
    other_tax_share: float
    total: float


class SplitResponse(BaseModel):
    people: list[PersonBreakdown]
    bill_total: float
    calculated_total: float
    difference: float
    total_matches: bool
    warning: Optional[str] = None
