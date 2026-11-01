"""Expense business logic: CRUD, soft delete/restore, splitting, filtering."""
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Expense, ExpenseContext, Tag
from app.schemas.transactions import ExpenseCreate, ExpenseSplit, ExpenseUpdate

_EXPENSE_LOAD_OPTIONS = (
    selectinload(Expense.account),
    selectinload(Expense.merchant),
    selectinload(Expense.category),
    selectinload(Expense.location),
    selectinload(Expense.tags),
    selectinload(Expense.context),
    selectinload(Expense.attachments),
)


def get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.scalar(
        select(Expense).options(*_EXPENSE_LOAD_OPTIONS).where(Expense.id == expense_id)
    )
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


def list_expenses(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    start: datetime | None = None,
    end: datetime | None = None,
    category_id: int | None = None,
    merchant_id: int | None = None,
    account_id: int | None = None,
    tag_id: int | None = None,
    is_need: bool | None = None,
    search: str | None = None,
    include_deleted: bool = False,
    only_deleted: bool = False,
) -> tuple[list[Expense], int]:
    query = select(Expense)
    if only_deleted:
        query = query.where(Expense.is_deleted.is_(True))
    elif not include_deleted:
        query = query.where(Expense.is_deleted.is_(False))
    if start is not None:
        query = query.where(Expense.transaction_datetime >= start)
    if end is not None:
        query = query.where(Expense.transaction_datetime < end)
    if category_id is not None:
        query = query.where(Expense.category_id == category_id)
    if merchant_id is not None:
        query = query.where(Expense.merchant_id == merchant_id)
    if account_id is not None:
        query = query.where(Expense.account_id == account_id)
    if is_need is not None:
        query = query.where(Expense.is_need.is_(is_need))
    if tag_id is not None:
        query = query.where(Expense.tags.any(Tag.id == tag_id))
    if search:
        query = query.where(Expense.note.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.options(*_EXPENSE_LOAD_OPTIONS)
            .order_by(Expense.transaction_datetime.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def _resolve_tags(db: Session, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))))
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=400, detail="One or more tag ids do not exist")
    return tags


def _context_payload(data, exclude_unset: bool = False) -> dict:
    """Context fields with planned_purchase derived from planning_horizon.

    The legacy boolean is kept in sync so historical and new rows remain
    comparable as ML features.
    """
    payload = data.model_dump(exclude_unset=exclude_unset)
    horizon = payload.get("planning_horizon")
    if horizon is not None and payload.get("planned_purchase") is None:
        payload["planned_purchase"] = horizon != "not_planned"
    return payload


def create_expense(db: Session, data: ExpenseCreate) -> Expense:
    payload = data.model_dump(exclude={"tag_ids", "context"})
    expense = Expense(**payload)
    expense.tags = _resolve_tags(db, data.tag_ids)
    if data.context is not None and any(
        v is not None for v in data.context.model_dump().values()
    ):
        expense.context = ExpenseContext(**_context_payload(data.context))
    db.add(expense)
    db.commit()
    return get_expense(db, expense.id)


def update_expense(db: Session, expense_id: int, data: ExpenseUpdate) -> Expense:
    expense = get_expense(db, expense_id)
    fields = data.model_dump(exclude_unset=True, exclude={"tag_ids", "context"})
    for key, value in fields.items():
        setattr(expense, key, value)
    if data.tag_ids is not None:
        expense.tags = _resolve_tags(db, data.tag_ids)
    if data.context is not None:
        if expense.context is None:
            expense.context = ExpenseContext(**_context_payload(data.context))
        else:
            for key, value in _context_payload(data.context, exclude_unset=True).items():
                setattr(expense.context, key, value)
    db.commit()
    return get_expense(db, expense_id)


def soft_delete_expense(db: Session, expense_id: int) -> None:
    expense = get_expense(db, expense_id)
    expense.is_deleted = True
    expense.deleted_at = datetime.now()
    db.commit()


def restore_expense(db: Session, expense_id: int) -> Expense:
    expense = get_expense(db, expense_id)
    expense.is_deleted = False
    expense.deleted_at = None
    db.commit()
    return get_expense(db, expense_id)


def split_expense(db: Session, expense_id: int, data: ExpenseSplit) -> list[Expense]:
    """Split an expense into parts. The original is soft-deleted and kept
    as the parent so the raw event is never lost."""
    original = get_expense(db, expense_id)
    parts_total = sum(Decimal(str(p.amount)) for p in data.parts)
    if parts_total != original.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Split parts ({parts_total}) must sum to the original amount ({original.amount})",
        )
    group_id = str(uuid.uuid4())
    children: list[Expense] = []
    for part in data.parts:
        children.append(
            Expense(
                amount=Decimal(str(part.amount)),
                currency=original.currency,
                transaction_datetime=original.transaction_datetime,
                account_id=original.account_id,
                merchant_id=original.merchant_id,
                category_id=part.category_id or original.category_id,
                location_id=original.location_id,
                payment_method=original.payment_method,
                note=part.note,
                is_need=original.is_need,
                parent_transaction_id=original.id,
                split_group_id=group_id,
            )
        )
    original.is_deleted = True
    original.deleted_at = datetime.now()
    original.split_group_id = group_id
    db.add_all(children)
    db.commit()
    return [get_expense(db, child.id) for child in children]
