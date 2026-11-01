"""Schemas for Budget (monthly), Goal + GoalTransaction, DailyContext."""
from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.reference import CategoryOut


# --- Budget ------------------------------------------------------------
class BudgetBase(BaseModel):
    category_id: int | None = None
    budget_amount: float = Field(gt=0)
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    rollover: bool = False
    alert_threshold: float = Field(default=0.8, ge=0, le=1)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category_id: int | None = None
    budget_amount: float | None = Field(default=None, gt=0)
    year: int | None = Field(default=None, ge=2000, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    rollover: bool | None = None
    alert_threshold: float | None = Field(default=None, ge=0, le=1)


class BudgetOut(ORMModel, BudgetBase):
    id: int
    category: CategoryOut | None = None


class BudgetProgress(BudgetOut):
    """Budget with dynamically computed spend (never stored).

    status: current/future months → ok | warning | exceeded
            past months          → completed | exceeded | unused
    """

    spent: float
    remaining: float
    fraction_used: float
    status: str


class BudgetHistoryMonth(BaseModel):
    year: int
    month: int
    label: str  # "2026-07"
    total_budget: float
    total_spent: float
    completed: int
    exceeded: int
    unused: int
    items: list[BudgetProgress]


# --- Goal --------------------------------------------------------------
class GoalBase(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    target_amount: float = Field(gt=0)
    deadline: date | None = None
    priority: int = Field(default=3, ge=1, le=5)
    completed: bool = False


class GoalCreate(GoalBase):
    initial_amount: float = Field(default=0, ge=0)  # creates an initial deposit


class GoalUpdate(BaseModel):
    title: str | None = None
    target_amount: float | None = Field(default=None, gt=0)
    deadline: date | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    completed: bool | None = None


class GoalOut(ORMModel, GoalBase):
    id: int
    current_amount: float = 0  # always computed from transactions


class GoalTransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    transaction_type: str = Field(pattern="^(deposit|withdraw)$")
    date: date
    note: str | None = None


class GoalTransactionOut(ORMModel):
    id: int
    goal_id: int
    amount: float
    transaction_type: str
    date: date
    note: str | None


# --- Daily context -----------------------------------------------------
class DailyContextIn(BaseModel):
    date: date
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    happiness: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    exercise_minutes: int | None = Field(default=None, ge=0)
    study_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str | None = None


class DailyContextOut(ORMModel, DailyContextIn):
    id: int
