"""Expense endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.transactions import (
    ExpenseCreate,
    ExpenseOut,
    ExpensePage,
    ExpenseSplit,
    ExpenseUpdate,
)
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=ExpensePage)
def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start: datetime | None = None,
    end: datetime | None = None,
    category_id: int | None = None,
    merchant_id: int | None = None,
    account_id: int | None = None,
    tag_id: int | None = None,
    is_need: bool | None = None,
    search: str | None = None,
    only_deleted: bool = False,
    db: Session = Depends(get_db),
) -> ExpensePage:
    items, total = expense_service.list_expenses(
        db,
        page=page,
        page_size=page_size,
        start=start,
        end=end,
        category_id=category_id,
        merchant_id=merchant_id,
        account_id=account_id,
        tag_id=tag_id,
        is_need=is_need,
        search=search,
        only_deleted=only_deleted,
    )
    return ExpensePage(
        items=[ExpenseOut.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    return expense_service.get_expense(db, expense_id)


@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db)):
    return expense_service.create_expense(db, data)


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, data: ExpenseUpdate, db: Session = Depends(get_db)):
    return expense_service.update_expense(db, expense_id, data)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)) -> None:
    expense_service.soft_delete_expense(db, expense_id)


@router.post("/{expense_id}/restore", response_model=ExpenseOut)
def restore_expense(expense_id: int, db: Session = Depends(get_db)):
    return expense_service.restore_expense(db, expense_id)


@router.post("/{expense_id}/split", response_model=list[ExpenseOut])
def split_expense(expense_id: int, data: ExpenseSplit, db: Session = Depends(get_db)):
    return expense_service.split_expense(db, expense_id, data)
