from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# What the ocr-mvp /parse endpoint returns under "receipt". Mirrors ocr-mvp/structure.py.
class ParsedItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    qty: float = 1
    unit_price: float | None = None
    total_price: float
    assigned_to: list[str] = []
    missing: list[str] = []


class ParsedReceipt(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[ParsedItem]
    subtotal: float | None = None
    tax: float | None = None
    tip: float | None = None
    total: float | None = None
    currency: str | None = None
    warnings: list[str] = []


Confirmation = Literal["none", "confirmed", "needs_reconfirm"]


# Responses. Amounts are integers in minor units (1450 = 14.50). Quantities are decimals.
class ClaimOut(BaseModel):
    member_id: int
    name: str
    quantity: int


class ItemOut(BaseModel):
    id: int
    position: int
    name: str
    quantity: float
    unit_price_minor: int | None
    total_minor: int
    missing: list[str]
    preassigned_names: list[str]
    # Quantity minus everyone's claims. Below zero means the item is over-claimed.
    remaining: float
    claims: list[ClaimOut]


class MemberOut(BaseModel):
    id: int
    name: str
    joined: bool
    # "none": not confirmed. "confirmed": confirmed on the current bill.
    # "needs_reconfirm": the bill changed after the guest confirmed.
    confirmation: Confirmation


class ShareOut(BaseModel):
    member_id: int
    name: str
    subtotal_minor: int
    tax_minor: int
    tip_minor: int
    total_minor: int


class SessionView(BaseModel):
    session_id: str
    status: str
    expires_at: datetime
    currency: str | None
    subtotal_minor: int | None
    tax_minor: int | None
    tip_minor: int | None
    total_minor: int | None
    warnings: list[str]
    host_payment_handle: str | None
    items: list[ItemOut]
    members: list[MemberOut]
    # Why the host cannot mark the split ready yet. Empty when it can be shared.
    problems: list[str]
    # True when every item is claimed and every joined guest has confirmed the current bill.
    locked: bool
    # What still stops the split from locking. Empty when it is locked.
    blockers: list[str]
    # Each joined guest's exact share. None until the split is locked.
    shares: list[ShareOut] | None


class SessionCreated(SessionView):
    # Returned once. The host's browser keeps it. The server stores only its hash.
    host_token: str


class JoinOut(BaseModel):
    member_id: int
    name: str
    # Returned once. The guest's browser keeps it. The server stores only its hash.
    member_token: str


class MeOut(BaseModel):
    member_id: int
    name: str
    confirmation: Confirmation


# Requests
class SessionPatch(BaseModel):
    currency: str | None = Field(default=None, max_length=8)
    subtotal_minor: int | None = None
    tax_minor: int | None = None
    tip_minor: int | None = None
    total_minor: int | None = None
    host_payment_handle: str | None = Field(default=None, max_length=64)


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(default=1, gt=0, le=10000)
    unit_price_minor: int | None = None
    total_minor: int


class ItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: float | None = Field(default=None, gt=0, le=10000)
    unit_price_minor: int | None = None
    total_minor: int | None = None


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class ClaimIn(BaseModel):
    # The guest's total for this item. Setting it again is safe.
    quantity: int = Field(ge=0, le=1000)
