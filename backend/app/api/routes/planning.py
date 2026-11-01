"""Endpoints for budgets (monthly records), goals + transactions, daily context."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.planning import (
    BudgetCreate,
    BudgetHistoryMonth,
    BudgetOut,
    BudgetProgress,
    BudgetUpdate,
    DailyContextIn,
    DailyContextOut,
    GoalCreate,
    GoalOut,
    GoalTransactionCreate,
    GoalTransactionOut,
    GoalUpdate,
)
from app.services import planning_service as svc

router = APIRouter(tags=["planning"])


# --- Budgets -----------------------------------------------------------
@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(
    year: int | None = None, month: int | None = Query(None, ge=1, le=12), db: Session = Depends(get_db)
):
    return svc.list_budgets(db, year, month)


@router.get("/budgets/progress", response_model=list[BudgetProgress])
def budgets_progress(
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Budget progress for a month (defaults to the current month)."""
    today = date.today()
    budgets = svc.list_budgets(db, year or today.year, month or today.month)
    return [svc.budget_progress(db, b) for b in budgets]


@router.get("/budgets/history", response_model=list[BudgetHistoryMonth])
def budgets_history(months: int = Query(12, ge=1, le=36), db: Session = Depends(get_db)):
    return svc.budget_history(db, months)


@router.post("/budgets", response_model=BudgetOut, status_code=201)
def create_budget(data: BudgetCreate, db: Session = Depends(get_db)):
    return svc.create_budget(db, data)


@router.patch("/budgets/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: int, data: BudgetUpdate, db: Session = Depends(get_db)):
    return svc.update_budget(db, budget_id, data)


@router.delete("/budgets/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_budget(db, budget_id)


# --- Goals -------------------------------------------------------------
@router.get("/goals", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db)):
    return svc.list_goals(db)


@router.post("/goals", response_model=GoalOut, status_code=201)
def create_goal(data: GoalCreate, db: Session = Depends(get_db)):
    return svc.create_goal(db, data)


@router.patch("/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, data: GoalUpdate, db: Session = Depends(get_db)):
    return svc.update_goal(db, goal_id, data)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_goal(db, goal_id)


@router.get("/goals/{goal_id}/transactions", response_model=list[GoalTransactionOut])
def list_goal_transactions(goal_id: int, db: Session = Depends(get_db)):
    return svc.list_goal_transactions(db, goal_id)


@router.post("/goals/{goal_id}/transactions", response_model=GoalOut, status_code=201)
def create_goal_transaction(goal_id: int, data: GoalTransactionCreate, db: Session = Depends(get_db)):
    """Record a deposit or withdrawal; returns the goal with its new balance."""
    return svc.create_goal_transaction(db, goal_id, data)


@router.delete("/goals/{goal_id}/transactions/{transaction_id}", response_model=GoalOut)
def delete_goal_transaction(goal_id: int, transaction_id: int, db: Session = Depends(get_db)):
    return svc.delete_goal_transaction(db, goal_id, transaction_id)


# --- Daily context -----------------------------------------------------
@router.get("/daily-context", response_model=list[DailyContextOut])
def list_daily_contexts(
    start: date | None = None, end: date | None = None, db: Session = Depends(get_db)
):
    return svc.list_daily_contexts(db, start, end)


@router.put("/daily-context", response_model=DailyContextOut)
def upsert_daily_context(data: DailyContextIn, db: Session = Depends(get_db)):
    return svc.upsert_daily_context(db, data)
