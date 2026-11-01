"""Budgets (monthly historical records), goals with transaction history,
and daily context. All balances/progress are computed, never stored."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Budget, Category, DailyContext, Expense, Goal, GoalTransaction
from app.schemas.planning import (
    BudgetCreate,
    BudgetHistoryMonth,
    BudgetProgress,
    BudgetUpdate,
    DailyContextIn,
    GoalCreate,
    GoalOut,
    GoalTransactionCreate,
    GoalUpdate,
)


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


def _budgetable_category_ids(db: Session) -> set[int]:
    """Categories whose expenses count toward budgets."""
    return set(db.scalars(select(Category.id).where(Category.budgetable.is_(True))))


def _descendant_category_ids(db: Session, category_id: int) -> list[int]:
    """A category budget covers the category and all its descendants."""
    ids = [category_id]
    frontier = [category_id]
    while frontier:
        children = list(
            db.scalars(select(Category.id).where(Category.parent_id.in_(frontier)))
        )
        children = [c for c in children if c not in ids]
        ids.extend(children)
        frontier = children
    return ids


# --- Budgets -----------------------------------------------------------
def list_budgets(db: Session, year: int | None = None, month: int | None = None) -> list[Budget]:
    query = (
        select(Budget)
        .options(selectinload(Budget.category))
        .order_by(Budget.year.desc(), Budget.month.desc(), Budget.id)
    )
    if year is not None:
        query = query.where(Budget.year == year)
    if month is not None:
        query = query.where(Budget.month == month)
    return list(db.scalars(query))


def _check_duplicate(db: Session, category_id: int | None, year: int, month: int, exclude_id: int | None = None) -> None:
    query = select(Budget.id).where(
        Budget.year == year,
        Budget.month == month,
        Budget.category_id.is_(None) if category_id is None else Budget.category_id == category_id,
    )
    if exclude_id is not None:
        query = query.where(Budget.id != exclude_id)
    if db.scalar(query.limit(1)):
        raise HTTPException(
            status_code=400,
            detail="A budget for this category and month already exists",
        )


def create_budget(db: Session, data: BudgetCreate) -> Budget:
    _check_duplicate(db, data.category_id, data.year, data.month)
    budget = Budget(**data.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(db: Session, budget_id: int, data: BudgetUpdate) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    fields = data.model_dump(exclude_unset=True)
    merged = {
        "category_id": fields.get("category_id", budget.category_id),
        "year": fields.get("year", budget.year),
        "month": fields.get("month", budget.month),
    }
    _check_duplicate(db, merged["category_id"], merged["year"], merged["month"], exclude_id=budget_id)
    for key, value in fields.items():
        setattr(budget, key, value)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget_id: int) -> None:
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()


def budget_progress(db: Session, budget: Budget, today: date | None = None) -> BudgetProgress:
    """Compute spend against a budget dynamically.

    Expenses in categories marked budgetable=False are excluded — they are
    legitimate expenses (still visible in analytics) but do not consume
    budgets or trigger alerts.
    """
    today = today or date.today()
    start, end = month_bounds(budget.year, budget.month)
    budgetable_ids = _budgetable_category_ids(db)

    query = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.is_deleted.is_(False),
        Expense.transaction_datetime >= start,
        Expense.transaction_datetime < end,
    )
    if budget.category_id is not None:
        covered = [
            cid for cid in _descendant_category_ids(db, budget.category_id) if cid in budgetable_ids
        ]
        if not covered:
            covered = [-1]  # nothing budgetable → zero spend
        query = query.where(Expense.category_id.in_(covered))
    else:
        # Overall budget: uncategorized expenses count; non-budgetable don't.
        query = query.where(
            (Expense.category_id.is_(None)) | (Expense.category_id.in_(budgetable_ids))
        )

    spent = float(db.scalar(query) or 0)
    amount = float(budget.budget_amount)
    fraction = spent / amount if amount else 0.0

    is_past = (budget.year, budget.month) < (today.year, today.month)
    if is_past:
        if spent == 0:
            status = "unused"
        elif fraction > 1:
            status = "exceeded"
        else:
            status = "completed"
    else:
        if fraction >= 1:
            status = "exceeded"
        elif fraction >= budget.alert_threshold:
            status = "warning"
        else:
            status = "ok"

    return BudgetProgress(
        id=budget.id,
        category_id=budget.category_id,
        category=budget.category,
        budget_amount=amount,
        year=budget.year,
        month=budget.month,
        rollover=budget.rollover,
        alert_threshold=budget.alert_threshold,
        spent=spent,
        remaining=amount - spent,
        fraction_used=round(fraction, 4),
        status=status,
    )


def budget_history(db: Session, months: int, anchor: date | None = None) -> list[BudgetHistoryMonth]:
    """Per-month budget snapshots for the last N months (newest first)."""
    anchor = anchor or date.today()
    result: list[BudgetHistoryMonth] = []
    year, month = anchor.year, anchor.month
    for _ in range(months):
        budgets = list_budgets(db, year, month)
        items = [budget_progress(db, b, today=anchor) for b in budgets]
        result.append(
            BudgetHistoryMonth(
                year=year,
                month=month,
                label=f"{year}-{month:02d}",
                total_budget=round(sum(i.budget_amount for i in items), 2),
                total_spent=round(sum(i.spent for i in items), 2),
                completed=sum(1 for i in items if i.status == "completed"),
                exceeded=sum(1 for i in items if i.status == "exceeded"),
                unused=sum(1 for i in items if i.status == "unused"),
                items=items,
            )
        )
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return result


# --- Goals -------------------------------------------------------------
_SIGNED_AMOUNT = case(
    (GoalTransaction.transaction_type == "deposit", GoalTransaction.amount),
    else_=-GoalTransaction.amount,
)


def _goal_balances(db: Session, goal_ids: list[int] | None = None) -> dict[int, float]:
    query = select(GoalTransaction.goal_id, func.coalesce(func.sum(_SIGNED_AMOUNT), 0)).group_by(
        GoalTransaction.goal_id
    )
    if goal_ids is not None:
        query = query.where(GoalTransaction.goal_id.in_(goal_ids))
    return {goal_id: float(total) for goal_id, total in db.execute(query)}


def _goal_out(goal: Goal, balance: float) -> GoalOut:
    return GoalOut(
        id=goal.id,
        title=goal.title,
        target_amount=float(goal.target_amount),
        deadline=goal.deadline,
        priority=goal.priority,
        completed=goal.completed,
        current_amount=balance,
    )


def _get_goal(db: Session, goal_id: int) -> Goal:
    goal = db.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


def list_goals(db: Session) -> list[GoalOut]:
    goals = list(db.scalars(select(Goal).order_by(Goal.completed, Goal.priority, Goal.deadline)))
    balances = _goal_balances(db)
    return [_goal_out(g, balances.get(g.id, 0.0)) for g in goals]


def get_goal(db: Session, goal_id: int) -> GoalOut:
    goal = _get_goal(db, goal_id)
    balance = _goal_balances(db, [goal_id]).get(goal_id, 0.0)
    return _goal_out(goal, balance)


def create_goal(db: Session, data: GoalCreate) -> GoalOut:
    goal = Goal(**data.model_dump(exclude={"initial_amount"}))
    db.add(goal)
    db.flush()
    if data.initial_amount > 0:
        db.add(
            GoalTransaction(
                goal_id=goal.id,
                amount=Decimal(str(data.initial_amount)),
                transaction_type="deposit",
                date=date.today(),
                note="Initial balance",
            )
        )
    db.commit()
    return get_goal(db, goal.id)


def update_goal(db: Session, goal_id: int, data: GoalUpdate) -> GoalOut:
    goal = _get_goal(db, goal_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    db.commit()
    return get_goal(db, goal_id)


def delete_goal(db: Session, goal_id: int) -> None:
    db.delete(_get_goal(db, goal_id))
    db.commit()


def list_goal_transactions(db: Session, goal_id: int) -> list[GoalTransaction]:
    _get_goal(db, goal_id)
    return list(
        db.scalars(
            select(GoalTransaction)
            .where(GoalTransaction.goal_id == goal_id)
            .order_by(GoalTransaction.date.desc(), GoalTransaction.id.desc())
        )
    )


def create_goal_transaction(db: Session, goal_id: int, data: GoalTransactionCreate) -> GoalOut:
    _get_goal(db, goal_id)
    if data.transaction_type == "withdraw":
        balance = _goal_balances(db, [goal_id]).get(goal_id, 0.0)
        if data.amount > balance:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot withdraw more than the current saved amount ({balance:,.0f})",
            )
    db.add(
        GoalTransaction(
            goal_id=goal_id,
            amount=Decimal(str(data.amount)),
            transaction_type=data.transaction_type,
            date=data.date,
            note=data.note,
        )
    )
    db.commit()
    return get_goal(db, goal_id)


def delete_goal_transaction(db: Session, goal_id: int, transaction_id: int) -> GoalOut:
    tx = db.get(GoalTransaction, transaction_id)
    if tx is None or tx.goal_id != goal_id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return get_goal(db, goal_id)


# --- Daily context -----------------------------------------------------
def upsert_daily_context(db: Session, data: DailyContextIn) -> DailyContext:
    existing = db.scalar(select(DailyContext).where(DailyContext.date == data.date))
    if existing:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        return existing
    context = DailyContext(**data.model_dump())
    db.add(context)
    db.commit()
    return context


def list_daily_contexts(db: Session, start: date | None = None, end: date | None = None) -> list[DailyContext]:
    query = select(DailyContext).order_by(DailyContext.date.desc())
    if start:
        query = query.where(DailyContext.date >= start)
    if end:
        query = query.where(DailyContext.date <= end)
    return list(db.scalars(query.limit(90)))


def days_left_in_month(year: int, month: int, today: date | None = None) -> int:
    today = today or date.today()
    _, end = month_bounds(year, month)
    return max(((end - timedelta(days=1)).date() - today).days, 0)
