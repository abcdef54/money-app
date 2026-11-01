"""Dashboard summaries. Everything is computed dynamically from raw rows."""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Expense, Income, Merchant
from app.schemas.analytics import DashboardSummary, NamedAmount
from app.services.periods import period_bounds


def _expense_sum(db: Session, start: datetime, end: datetime) -> float:
    return float(
        db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.is_deleted.is_(False),
                Expense.transaction_datetime >= start,
                Expense.transaction_datetime < end,
            )
        )
        or 0
    )


def _income_sum(db: Session, start: datetime, end: datetime) -> float:
    return float(
        db.scalar(
            select(func.coalesce(func.sum(Income.amount), 0)).where(
                Income.is_deleted.is_(False),
                Income.transaction_datetime >= start,
                Income.transaction_datetime < end,
            )
        )
        or 0
    )


def summary(db: Session, period: str, anchor: date) -> DashboardSummary:
    start, end = period_bounds(period, anchor)

    total_expenses = _expense_sum(db, start, end)
    total_income = _income_sum(db, start, end)
    expense_count = int(
        db.scalar(
            select(func.count(Expense.id)).where(
                Expense.is_deleted.is_(False),
                Expense.transaction_datetime >= start,
                Expense.transaction_datetime < end,
            )
        )
        or 0
    )

    days = max((min(end, datetime.now()) - start).days, 1)
    daily_average = total_expenses / days

    largest_row = db.execute(
        select(Expense.id, Expense.amount, Expense.note, Expense.transaction_datetime, Merchant.name)
        .outerjoin(Merchant, Expense.merchant_id == Merchant.id)
        .where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
        .order_by(Expense.amount.desc())
        .limit(1)
    ).first()
    largest_expense = (
        {
            "id": largest_row[0],
            "amount": float(largest_row[1]),
            "note": largest_row[2],
            "transaction_datetime": largest_row[3].isoformat(),
            "merchant": largest_row[4],
        }
        if largest_row
        else None
    )

    cat_row = db.execute(
        select(Category.id, Category.name, Category.color, func.sum(Expense.amount).label("total"), func.count(Expense.id))
        .join(Expense, Expense.category_id == Category.id)
        .where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
        .group_by(Category.id)
        .order_by(func.sum(Expense.amount).desc())
        .limit(1)
    ).first()
    largest_category = (
        NamedAmount(id=cat_row[0], name=cat_row[1], color=cat_row[2], amount=float(cat_row[3]), count=cat_row[4])
        if cat_row
        else None
    )

    merch_row = db.execute(
        select(Merchant.id, Merchant.name, func.sum(Expense.amount).label("total"), func.count(Expense.id))
        .join(Expense, Expense.merchant_id == Merchant.id)
        .where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
        .group_by(Merchant.id)
        .order_by(func.sum(Expense.amount).desc())
        .limit(1)
    ).first()
    largest_merchant = (
        NamedAmount(id=merch_row[0], name=merch_row[1], amount=float(merch_row[2]), count=merch_row[3])
        if merch_row
        else None
    )

    balance = total_income - total_expenses
    return DashboardSummary(
        period=period,
        start_date=start.date(),
        end_date=(end.date()),
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        savings_rate=round(balance / total_income, 4) if total_income > 0 else 0.0,
        daily_average=round(daily_average, 2),
        expense_count=expense_count,
        largest_expense=largest_expense,
        largest_category=largest_category,
        largest_merchant=largest_merchant,
    )
