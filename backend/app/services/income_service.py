"""Income business logic."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Income
from app.schemas.transactions import IncomeCreate, IncomeUpdate


def get_income(db: Session, income_id: int) -> Income:
    income = db.scalar(
        select(Income).options(selectinload(Income.account)).where(Income.id == income_id)
    )
    if income is None:
        raise HTTPException(status_code=404, detail="Income not found")
    return income


def list_incomes(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    start: datetime | None = None,
    end: datetime | None = None,
    source: str | None = None,
    account_id: int | None = None,
) -> tuple[list[Income], int]:
    query = select(Income).where(Income.is_deleted.is_(False))
    if start is not None:
        query = query.where(Income.transaction_datetime >= start)
    if end is not None:
        query = query.where(Income.transaction_datetime < end)
    if source is not None:
        query = query.where(Income.source == source)
    if account_id is not None:
        query = query.where(Income.account_id == account_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.options(selectinload(Income.account))
            .order_by(Income.transaction_datetime.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def create_income(db: Session, data: IncomeCreate) -> Income:
    income = Income(**data.model_dump())
    db.add(income)
    db.commit()
    return get_income(db, income.id)


def update_income(db: Session, income_id: int, data: IncomeUpdate) -> Income:
    income = get_income(db, income_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(income, key, value)
    db.commit()
    return get_income(db, income_id)


def soft_delete_income(db: Session, income_id: int) -> None:
    income = get_income(db, income_id)
    income.is_deleted = True
    income.deleted_at = datetime.now()
    db.commit()
