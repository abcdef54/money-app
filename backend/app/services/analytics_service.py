"""Chart-oriented analytics.

Aggregation strategy: raw (datetime, amount) rows are fetched with SQL
filters and bucketed in Python. For a single-user dataset this is fast,
and it stays 100% portable between SQLite and PostgreSQL (no dialect
specific date functions).
"""
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Expense, Income, Merchant
from app.schemas.analytics import (
    CategoryComparisonRow,
    Comparison,
    ComparisonSide,
    HeatmapCell,
    LargestPurchase,
    NamedAmount,
    TimePoint,
)
from app.services.periods import bucket_key, iter_buckets, period_bounds, previous_period_bounds

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _expense_rows(db: Session, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
    return [
        (dt, float(amount))
        for dt, amount in db.execute(
            select(Expense.transaction_datetime, Expense.amount).where(
                Expense.is_deleted.is_(False),
                Expense.transaction_datetime >= start,
                Expense.transaction_datetime < end,
            )
        )
    ]


def _income_rows(db: Session, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
    return [
        (dt, float(amount))
        for dt, amount in db.execute(
            select(Income.transaction_datetime, Income.amount).where(
                Income.is_deleted.is_(False),
                Income.transaction_datetime >= start,
                Income.transaction_datetime < end,
            )
        )
    ]


def spending_over_time(
    db: Session, start: datetime, end: datetime, granularity: str
) -> list[TimePoint]:
    """Expenses + income per bucket, with empty buckets filled in."""
    expenses: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    incomes: dict[str, float] = defaultdict(float)
    for dt, amount in _expense_rows(db, start, end):
        key = bucket_key(dt, granularity)
        expenses[key] += amount
        counts[key] += 1
    for dt, amount in _income_rows(db, start, end):
        incomes[bucket_key(dt, granularity)] += amount
    return [
        TimePoint(
            period=key,
            expenses=round(expenses.get(key, 0), 2),
            income=round(incomes.get(key, 0), 2),
            count=counts.get(key, 0),
        )
        for key in iter_buckets(start, end, granularity)
    ]


def by_category(db: Session, start: datetime, end: datetime) -> list[NamedAmount]:
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            Category.color,
            func.sum(Expense.amount),
            func.count(Expense.id),
        )
        .join(Category, Expense.category_id == Category.id, isouter=True)
        .where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
        .group_by(Category.id)
        .order_by(func.sum(Expense.amount).desc())
    ).all()
    return [
        NamedAmount(
            id=row[0],
            name=row[1] or "Uncategorized",
            color=row[2],
            amount=float(row[3]),
            count=row[4],
        )
        for row in rows
    ]


def by_merchant(db: Session, start: datetime, end: datetime, limit: int = 15) -> list[NamedAmount]:
    rows = db.execute(
        select(Merchant.id, Merchant.name, func.sum(Expense.amount), func.count(Expense.id))
        .join(Merchant, Expense.merchant_id == Merchant.id)
        .where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
        .group_by(Merchant.id)
        .order_by(func.sum(Expense.amount).desc())
        .limit(limit)
    ).all()
    return [
        NamedAmount(id=row[0], name=row[1], amount=float(row[2]), count=row[3]) for row in rows
    ]


def heatmap_weekday(db: Session, start: datetime, end: datetime) -> list[HeatmapCell]:
    totals = [0.0] * 7
    counts = [0] * 7
    for dt, amount in _expense_rows(db, start, end):
        totals[dt.weekday()] += amount
        counts[dt.weekday()] += 1
    return [
        HeatmapCell(x=i, label=WEEKDAY_LABELS[i], amount=round(totals[i], 2), count=counts[i])
        for i in range(7)
    ]


def heatmap_hour(db: Session, start: datetime, end: datetime) -> list[HeatmapCell]:
    totals = [0.0] * 24
    counts = [0] * 24
    for dt, amount in _expense_rows(db, start, end):
        totals[dt.hour] += amount
        counts[dt.hour] += 1
    return [
        HeatmapCell(x=h, label=f"{h:02d}:00", amount=round(totals[h], 2), count=counts[h])
        for h in range(24)
    ]


def largest_purchases(
    db: Session, start: datetime, end: datetime, limit: int = 10
) -> list[LargestPurchase]:
    rows = db.execute(
        select(
            Expense.id,
            Expense.amount,
            Merchant.name,
            Category.name,
            Expense.note,
            Expense.transaction_datetime,
        )
        .outerjoin(Merchant, Expense.merchant_id == Merchant.id)
        .outerjoin(Category, Expense.category_id == Category.id)
        .where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
        .order_by(Expense.amount.desc())
        .limit(limit)
    ).all()
    return [
        LargestPurchase(
            id=row[0],
            amount=float(row[1]),
            merchant=row[2],
            category=row[3],
            note=row[4],
            transaction_datetime=row[5],
        )
        for row in rows
    ]


def category_trends(db: Session, months: int, anchor: date) -> dict:
    """Monthly totals per root category for the last N months."""
    # Resolve every category to its root.
    categories = list(db.scalars(select(Category)))
    parent_of = {c.id: c.parent_id for c in categories}
    info = {c.id: c for c in categories}

    def root_of(cat_id: int) -> int:
        seen = set()
        while parent_of.get(cat_id) is not None and cat_id not in seen:
            seen.add(cat_id)
            cat_id = parent_of[cat_id]
        return cat_id

    end = period_bounds("month", anchor)[1]
    year, month = anchor.year, anchor.month
    for _ in range(months - 1):
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    start = datetime(year, month, 1)

    rows = db.execute(
        select(Expense.transaction_datetime, Expense.amount, Expense.category_id).where(
            Expense.is_deleted.is_(False),
            Expense.transaction_datetime >= start,
            Expense.transaction_datetime < end,
        )
    ).all()

    series: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for dt, amount, cat_id in rows:
        root = root_of(cat_id) if cat_id is not None else None
        name = info[root].name if root is not None else "Uncategorized"
        series[name][dt.strftime("%Y-%m")] += float(amount)

    months_keys = iter_buckets(start, end, "month")
    return {
        "months": months_keys,
        "series": [
            {
                "name": name,
                "color": next(
                    (c.color for c in categories if c.name == name and c.parent_id is None), None
                ),
                "data": [round(buckets.get(m, 0), 2) for m in months_keys],
            }
            for name, buckets in sorted(
                series.items(), key=lambda kv: -sum(kv[1].values())
            )
        ],
    }


def _side(db: Session, label: str, start: datetime, end: datetime) -> ComparisonSide:
    rows = _expense_rows(db, start, end)
    total = sum(a for _, a in rows)
    days = max((end - start).days, 1)
    return ComparisonSide(
        label=label,
        start_date=start.date(),
        end_date=end.date(),
        total=round(total, 2),
        count=len(rows),
        daily_average=round(total / days, 2),
    )


def compare_periods(db: Session, period: str, anchor: date) -> Comparison:
    cur_start, cur_end = period_bounds(period, anchor)
    prev_start, prev_end = previous_period_bounds(period, anchor)
    current = _side(db, f"This {period}", cur_start, cur_end)
    previous = _side(db, f"Last {period}", prev_start, prev_end)
    change = current.total - previous.total
    return Comparison(
        current=current,
        previous=previous,
        change_amount=round(change, 2),
        change_percent=round(change / previous.total * 100, 1) if previous.total else None,
    )


def compare_categories(db: Session, period: str, anchor: date) -> list[CategoryComparisonRow]:
    cur_start, cur_end = period_bounds(period, anchor)
    prev_start, prev_end = previous_period_bounds(period, anchor)
    current = {c.id: c for c in by_category(db, cur_start, cur_end)}
    previous = {c.id: c for c in by_category(db, prev_start, prev_end)}
    rows: list[CategoryComparisonRow] = []
    for cat_id in {*current.keys(), *previous.keys()}:
        cur = current.get(cat_id)
        prev = previous.get(cat_id)
        cur_amount = cur.amount if cur else 0.0
        prev_amount = prev.amount if prev else 0.0
        rows.append(
            CategoryComparisonRow(
                category_id=cat_id,
                name=(cur or prev).name,  # type: ignore[union-attr]
                color=(cur or prev).color,  # type: ignore[union-attr]
                current=cur_amount,
                previous=prev_amount,
                change_percent=round((cur_amount - prev_amount) / prev_amount * 100, 1)
                if prev_amount
                else None,
            )
        )
    rows.sort(key=lambda r: -r.current)
    return rows
