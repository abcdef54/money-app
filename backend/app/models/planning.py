"""Planning entities: Budget (monthly record), Goal, GoalTransaction."""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.reference import Category


class Budget(TimestampMixin, Base):
    """A spending limit for a category in a specific month.

    One row per (category, year, month) — past months are permanent
    historical records, never overwritten. category_id may be NULL for an
    overall (all-categories) budget. Actual spend is always computed
    dynamically from expenses.
    """

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int] = mapped_column(nullable=False)  # 1-12
    rollover: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_threshold: Mapped[float] = mapped_column(default=0.8, nullable=False)  # fraction 0-1

    category: Mapped[Category | None] = relationship()


# One budget per category per month (coalesce makes NULL category unique too).
Index(
    "uq_budgets_category_period",
    func.coalesce(Budget.category_id, 0),
    Budget.year,
    Budget.month,
    unique=True,
)


class Goal(TimestampMixin, Base):
    """A savings goal. The saved amount is never stored — it is always the
    sum of this goal's deposit/withdraw transactions."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[int] = mapped_column(default=3, nullable=False)  # 1 (highest) - 5
    completed: Mapped[bool] = mapped_column(default=False, nullable=False)

    transactions: Mapped[list["GoalTransaction"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )


class GoalTransaction(TimestampMixin, Base):
    """A deposit into or withdrawal from a savings goal.

    Complete history is preserved — the goal's balance is derived data.
    """

    __tablename__ = "goal_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)  # deposit|withdraw
    date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    goal: Mapped[Goal] = relationship(back_populates="transactions")
