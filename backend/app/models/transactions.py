"""Money movement: Expense, Income, Attachment."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.reference import Account, Category, Location, Merchant, Tag, expense_tags


class Expense(TimestampMixin, SoftDeleteMixin, Base):
    """A single outgoing transaction.

    This is intentionally an *event with context*, not just an amount:
    every cheap-to-collect signal (need vs want, payment method, time,
    merchant, location, tags, behavioral context) is kept as raw data so
    future ML models can learn from it. Derived values (monthly totals,
    budget remainders...) are never stored here.
    """

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)
    transaction_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    merchant_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))

    payment_method: Mapped[str | None] = mapped_column(String(30))  # cash|card|e_wallet|bank_transfer|other
    note: Mapped[str | None] = mapped_column(Text)
    is_need: Mapped[bool | None] = mapped_column()  # True=need, False=want, None=unmarked
    is_recurring: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Split expense support: children point at the original transaction.
    parent_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL")
    )
    split_group_id: Mapped[str | None] = mapped_column(String(36), index=True)

    account: Mapped[Account | None] = relationship()
    merchant: Mapped[Merchant | None] = relationship()
    category: Mapped[Category | None] = relationship()
    location: Mapped[Location | None] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=expense_tags)
    context: Mapped["ExpenseContext | None"] = relationship(
        back_populates="expense", uselist=False, cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan"
    )


class Income(TimestampMixin, SoftDeleteMixin, Base):
    """A single incoming transaction."""

    __tablename__ = "incomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # salary|scholarship|gift|refund|investment|interest|other
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    transaction_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    is_recurring: Mapped[bool] = mapped_column(default=False, nullable=False)

    account: Mapped[Account | None] = relationship()


class Attachment(TimestampMixin, Base):
    """Receipt image attached to an expense. OCR text is filled in later."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    ocr_text: Mapped[str | None] = mapped_column(Text)

    expense: Mapped[Expense] = relationship(back_populates="attachments")


# Imported at the bottom to avoid a circular import at module load time.
from app.models.context import ExpenseContext  # noqa: E402
