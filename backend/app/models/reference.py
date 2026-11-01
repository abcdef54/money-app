"""Reference entities: Account, Category, Merchant, Location, Tag."""
from sqlalchemy import Column, ForeignKey, Index, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Many-to-many: expenses <-> tags
expense_tags = Table(
    "expense_tags",
    Base.metadata,
    Column("expense_id", ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Account(TimestampMixin, Base):
    """A place money lives: cash, bank account, e-wallet, credit card..."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)  # cash|bank|credit_card|e_wallet|other
    currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)
    bank: Mapped[str | None] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Category(TimestampMixin, Base):
    """Hierarchical spending category (one level of nesting is typical,
    but arbitrary depth is supported via parent_id)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    icon: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    budgetable: Mapped[bool] = mapped_column(default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)

    parent: Mapped["Category | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")


# No duplicate names among siblings (case-insensitive). coalesce() makes the
# constraint apply to top-level categories too (NULL parents would otherwise
# never compare equal).
Index(
    "uq_categories_parent_name",
    func.coalesce(Category.parent_id, 0),
    func.lower(Category.name),
    unique=True,
)


class Merchant(TimestampMixin, Base):
    """Who money was paid to. Merchants can be merged when duplicates appear."""

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    category_hint_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    category_hint: Mapped["Category | None"] = relationship()


class Location(TimestampMixin, Base):
    """Optional place where a purchase happened."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()


class Tag(TimestampMixin, Base):
    """Free-form label applied to expenses (Vacation, Impulse, Exam...)."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    color: Mapped[str | None] = mapped_column(String(20))
