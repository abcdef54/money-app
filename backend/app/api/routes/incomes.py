"""Income endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.transactions import IncomeCreate, IncomeOut, IncomeUpdate
from app.services import income_service

router = APIRouter(prefix="/incomes", tags=["incomes"])


@router.get("", response_model=dict)
def list_incomes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start: datetime | None = None,
    end: datetime | None = None,
    source: str | None = None,
    account_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    items, total = income_service.list_incomes(
        db, page=page, page_size=page_size, start=start, end=end, source=source, account_id=account_id
    )
    return {
        "items": [IncomeOut.model_validate(i).model_dump() for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=IncomeOut, status_code=201)
def create_income(data: IncomeCreate, db: Session = Depends(get_db)):
    return income_service.create_income(db, data)


@router.patch("/{income_id}", response_model=IncomeOut)
def update_income(income_id: int, data: IncomeUpdate, db: Session = Depends(get_db)):
    return income_service.update_income(db, income_id, data)


@router.delete("/{income_id}", status_code=204)
def delete_income(income_id: int, db: Session = Depends(get_db)) -> None:
    income_service.soft_delete_income(db, income_id)
