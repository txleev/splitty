from datetime import datetime

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


# Responses. Amounts are integers in minor units (1450 = 14.50). Quantities are decimals.
class ItemOut(BaseModel):
    id: int
    position: int
    name: str
    quantity: float
    unit_price_minor: int | None
    total_minor: int
    missing: list[str]
    preassigned_names: list[str]


class MemberOut(BaseModel):
    id: int
    name: str
    joined: bool


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


class SessionCreated(SessionView):
    # Returned once. The host's browser keeps it. The server stores only its hash.
    host_token: str


class JoinOut(BaseModel):
    member_id: int
    name: str
    # Returned once. The guest's browser keeps it. The server stores only its hash.
    member_token: str


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
