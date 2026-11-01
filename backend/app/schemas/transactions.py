"""Schemas for Expense (with behavioral context), Income, Attachment."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.reference import AccountOut, CategoryOut, LocationOut, MerchantOut, TagOut

PLANNING_HORIZONS = (
    "not_planned",
    "planned_today",
    "planned_this_week",
    "planned_this_month",
    "planned_over_month",
)


# --- Expense context (behavioral data) ---------------------------------
class ExpenseContextIn(BaseModel):
    need_level: int | None = Field(default=None, ge=1, le=5)
    planned_purchase: bool | None = None  # kept for legacy data; derived from planning_horizon
    planning_horizon: str | None = Field(
        default=None, pattern="^(not_planned|planned_today|planned_this_week|planned_this_month|planned_over_month)$"
    )
    impulse_score: int | None = Field(default=None, ge=1, le=5)
    urgency: int | None = Field(default=None, ge=1, le=5)
    expected_regret: int | None = Field(default=None, ge=1, le=5)
    actual_regret: int | None = Field(default=None, ge=1, le=5)
    satisfaction: int | None = Field(default=None, ge=1, le=5)
    emotion: str | None = None
    motivation: str | None = None
    shopping_channel: str | None = None
    who_with: str | None = None


class ExpenseContextOut(ORMModel, ExpenseContextIn):
    expense_id: int


# --- Expense -----------------------------------------------------------
class ExpenseBase(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "VND"
    transaction_datetime: datetime
    account_id: int | None = None
    merchant_id: int | None = None
    category_id: int | None = None
    location_id: int | None = None
    payment_method: str | None = None
    note: str | None = None
    is_need: bool | None = None
    is_recurring: bool = False


class ExpenseCreate(ExpenseBase):
    tag_ids: list[int] = []
    context: ExpenseContextIn | None = None


class ExpenseUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = None
    transaction_datetime: datetime | None = None
    account_id: int | None = None
    merchant_id: int | None = None
    category_id: int | None = None
    location_id: int | None = None
    payment_method: str | None = None
    note: str | None = None
    is_need: bool | None = None
    is_recurring: bool | None = None
    tag_ids: list[int] | None = None
    context: ExpenseContextIn | None = None


class ExpenseSplitPart(BaseModel):
    amount: float = Field(gt=0)
    category_id: int | None = None
    note: str | None = None


class ExpenseSplit(BaseModel):
    parts: list[ExpenseSplitPart] = Field(min_length=2)


class AttachmentOut(ORMModel):
    id: int
    expense_id: int
    image_path: str
    ocr_text: str | None = None


class ExpenseOut(ORMModel):
    id: int
    amount: float
    currency: str
    transaction_datetime: datetime
    created_at: datetime
    updated_at: datetime
    account_id: int | None
    merchant_id: int | None
    category_id: int | None
    location_id: int | None
    payment_method: str | None
    note: str | None
    is_need: bool | None
    is_recurring: bool
    parent_transaction_id: int | None
    split_group_id: str | None
    is_deleted: bool

    account: AccountOut | None = None
    merchant: MerchantOut | None = None
    category: CategoryOut | None = None
    location: LocationOut | None = None
    tags: list[TagOut] = []
    context: ExpenseContextOut | None = None
    attachments: list[AttachmentOut] = []


class ExpensePage(BaseModel):
    items: list[ExpenseOut]
    total: int
    page: int
    page_size: int


# --- Income ------------------------------------------------------------
class IncomeBase(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "VND"
    source: str = "other"
    account_id: int | None = None
    transaction_datetime: datetime
    note: str | None = None
    is_recurring: bool = False


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = None
    source: str | None = None
    account_id: int | None = None
    transaction_datetime: datetime | None = None
    note: str | None = None
    is_recurring: bool | None = None


class IncomeOut(ORMModel):
    id: int
    amount: float
    currency: str
    source: str
    account_id: int | None
    transaction_datetime: datetime
    note: str | None
    is_recurring: bool
    is_deleted: bool
    account: AccountOut | None = None
