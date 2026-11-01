"""Behavioral context tables — the core of future ML training data."""
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExpenseContext(TimestampMixin, Base):
    """Behavioral context captured for an individual expense.

    Everything here is optional: capture what is cheap to record at entry
    time. `actual_regret` and `satisfaction` are expected to be filled in
    days later, giving labeled data for regret/satisfaction prediction.
    """

    __tablename__ = "expense_contexts"

    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True
    )
    need_level: Mapped[int | None] = mapped_column()          # 1-5 (optional → essential)
    planned_purchase: Mapped[bool | None] = mapped_column()   # derived from planning_horizon on write
    planning_horizon: Mapped[str | None] = mapped_column(String(30))
    # not_planned|planned_today|planned_this_week|planned_this_month|planned_over_month
    impulse_score: Mapped[int | None] = mapped_column()       # 1-5 (planned → completely impulsive)
    urgency: Mapped[int | None] = mapped_column()             # 1-5
    expected_regret: Mapped[int | None] = mapped_column()     # 1-5, at purchase time
    actual_regret: Mapped[int | None] = mapped_column()       # 1-5, filled in later
    satisfaction: Mapped[int | None] = mapped_column()        # 1-5, filled in later
    emotion: Mapped[str | None] = mapped_column(String(30))
    motivation: Mapped[str | None] = mapped_column(String(100))
    shopping_channel: Mapped[str | None] = mapped_column(String(30))
    # physical_store|online|marketplace|social_media|recommendation|other
    who_with: Mapped[str | None] = mapped_column(String(50))  # alone|family|friends|partner|coworkers|classmates|other

    expense = relationship("Expense", back_populates="context")


class DailyContext(TimestampMixin, Base):
    """One row per day of life context that may influence spending."""

    __tablename__ = "daily_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    sleep_hours: Mapped[float | None] = mapped_column()
    stress_level: Mapped[int | None] = mapped_column()    # 1-5
    happiness: Mapped[int | None] = mapped_column()       # 1-5
    energy: Mapped[int | None] = mapped_column()          # 1-5
    exercise_minutes: Mapped[int | None] = mapped_column()
    study_hours: Mapped[float | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text)
