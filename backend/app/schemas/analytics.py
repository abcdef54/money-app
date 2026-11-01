"""Schemas for dashboard, analytics and insights responses."""
from datetime import date, datetime

from pydantic import BaseModel


class NamedAmount(BaseModel):
    id: int | None = None
    name: str
    amount: float
    count: int = 0
    color: str | None = None


class DashboardSummary(BaseModel):
    period: str
    start_date: date
    end_date: date
    total_income: float
    total_expenses: float
    balance: float          # income - expenses in the period
    savings_rate: float     # (income - expenses) / income, 0 if no income
    daily_average: float
    expense_count: int
    largest_expense: dict | None = None
    largest_category: NamedAmount | None = None
    largest_merchant: NamedAmount | None = None


class TimePoint(BaseModel):
    period: str   # e.g. "2026-07-11", "2026-W28", "2026-07"
    expenses: float
    income: float = 0
    count: int = 0


class HeatmapCell(BaseModel):
    x: int        # weekday 0-6 (Mon-Sun) or hour 0-23
    label: str
    amount: float
    count: int


class ComparisonSide(BaseModel):
    label: str
    start_date: date
    end_date: date
    total: float
    count: int
    daily_average: float


class Comparison(BaseModel):
    current: ComparisonSide
    previous: ComparisonSide
    change_amount: float
    change_percent: float | None  # None when previous total is 0


class CategoryComparisonRow(BaseModel):
    category_id: int | None
    name: str
    color: str | None
    current: float
    previous: float
    change_percent: float | None


class Insight(BaseModel):
    kind: str          # weekend_spending | top_weekday | category_trend | ...
    severity: str      # info | warning | positive
    message: str
    value: float | None = None


class LargestPurchase(BaseModel):
    id: int
    amount: float
    merchant: str | None
    category: str | None
    note: str | None
    transaction_datetime: datetime
