"""Heuristic behavioral insights — SQL + simple statistics, no ML.

Each heuristic returns None when there is not enough data, so the
insights feed degrades gracefully on a fresh database.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Expense, Merchant
from app.schemas.analytics import Insight
from app.services import planning_service
from app.services.analytics_service import _expense_rows, by_category
from app.services.periods import month_bounds, previous_period_bounds

MIN_ROWS = 10  # don't emit statistics from almost no data


def _fmt(amount: float, currency: str = "VND") -> str:
    if currency == "VND":
        return f"{amount:,.0f} ₫"
    return f"{amount:,.2f} {currency}"


def _weekend_vs_weekday(rows: list[tuple[datetime, float]]) -> Insight | None:
    weekday_days: dict[date, float] = defaultdict(float)
    weekend_days: dict[date, float] = defaultdict(float)
    for dt, amount in rows:
        (weekend_days if dt.weekday() >= 5 else weekday_days)[dt.date()] += amount
    if len(weekday_days) < 5 or len(weekend_days) < 2:
        return None
    weekday_avg = sum(weekday_days.values()) / len(weekday_days)
    weekend_avg = sum(weekend_days.values()) / len(weekend_days)
    if weekday_avg == 0:
        return None
    diff = (weekend_avg - weekday_avg) / weekday_avg * 100
    if abs(diff) < 15:
        return None
    direction = "more" if diff > 0 else "less"
    return Insight(
        kind="weekend_spending",
        severity="info",
        message=f"You spend {abs(diff):.0f}% {direction} on weekends than on weekdays (last 90 days).",
        value=round(diff, 1),
    )


def _top_weekday(rows: list[tuple[datetime, float]]) -> Insight | None:
    labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    totals = [0.0] * 7
    for dt, amount in rows:
        totals[dt.weekday()] += amount
    if sum(totals) == 0:
        return None
    top = max(range(7), key=lambda i: totals[i])
    return Insight(
        kind="top_weekday",
        severity="info",
        message=f"You usually spend the most on {labels[top]}s ({_fmt(totals[top])} over the last 90 days).",
        value=totals[top],
    )


def _peak_hours(rows: list[tuple[datetime, float]]) -> Insight | None:
    counts = [0] * 24
    for dt, _ in rows:
        counts[dt.hour] += 1
    total = sum(counts)
    if total < MIN_ROWS:
        return None
    # Best 3-hour window by purchase count.
    best_start = max(range(22), key=lambda h: counts[h] + counts[h + 1] + counts[h + 2])
    window = counts[best_start] + counts[best_start + 1] + counts[best_start + 2]
    share = window / total * 100
    if share < 25:
        return None
    return Insight(
        kind="peak_hours",
        severity="info",
        message=(
            f"{share:.0f}% of your purchases happen between "
            f"{datetime(2000, 1, 1, best_start).strftime('%H:%M')} and "
            f"{datetime(2000, 1, 1, min(best_start + 3, 23)).strftime('%H:%M')}."
        ),
        value=round(share, 1),
    )


def _category_changes(db: Session, anchor: date) -> list[Insight]:
    cur_start, cur_end = month_bounds(anchor)
    prev_start, prev_end = previous_period_bounds("month", anchor)
    current = {c.name: c.amount for c in by_category(db, cur_start, cur_end)}
    previous = {c.name: c.amount for c in by_category(db, prev_start, prev_end)}
    insights: list[Insight] = []
    for name, cur_amount in current.items():
        prev_amount = previous.get(name, 0)
        if prev_amount < 1 or cur_amount < 1:
            continue
        change = (cur_amount - prev_amount) / prev_amount * 100
        if change >= 30:
            insights.append(
                Insight(
                    kind="category_increase",
                    severity="warning",
                    message=f"{name} spending increased {change:.0f}% this month ({_fmt(cur_amount)} vs {_fmt(prev_amount)}).",
                    value=round(change, 1),
                )
            )
        elif change <= -30:
            insights.append(
                Insight(
                    kind="category_decrease",
                    severity="positive",
                    message=f"{name} spending decreased {abs(change):.0f}% this month ({_fmt(cur_amount)} vs {_fmt(prev_amount)}).",
                    value=round(change, 1),
                )
            )
    insights.sort(key=lambda i: -abs(i.value or 0))
    return insights[:3]


def _highest_week(db: Session, anchor: date) -> Insight | None:
    year_start = datetime(anchor.year, 1, 1)
    rows = _expense_rows(db, year_start, datetime.now())
    if len(rows) < MIN_ROWS:
        return None
    weeks: dict[str, float] = defaultdict(float)
    for dt, amount in rows:
        iso = dt.isocalendar()
        weeks[f"{iso.year}-W{iso.week:02d}"] += amount
    if len(weeks) < 3:
        return None
    this_iso = anchor.isocalendar()
    this_key = f"{this_iso.year}-W{this_iso.week:02d}"
    top_key = max(weeks, key=lambda k: weeks[k])
    if top_key == this_key:
        return Insight(
            kind="highest_week",
            severity="warning",
            message=f"This is your highest-spending week this year ({_fmt(weeks[top_key])}).",
            value=weeks[top_key],
        )
    return None


def _merchant_frequency(db: Session, anchor: date) -> Insight | None:
    year_start = datetime(anchor.year, 1, 1)
    row = db.execute(
        select(Merchant.name, func.count(Expense.id))
        .join(Merchant, Expense.merchant_id == Merchant.id)
        .where(Expense.is_deleted.is_(False), Expense.transaction_datetime >= year_start)
        .group_by(Merchant.id)
        .order_by(func.count(Expense.id).desc())
        .limit(1)
    ).first()
    if row is None or row[1] < 5:
        return None
    return Insight(
        kind="merchant_frequency",
        severity="info",
        message=f"You have spent at {row[0]} {row[1]} times this year.",
        value=float(row[1]),
    )


def _daily_average_trend(db: Session, anchor: date) -> Insight | None:
    """Compare average daily spend of the last month vs the two before it."""
    end = datetime.combine(anchor + timedelta(days=1), datetime.min.time())
    recent_start = end - timedelta(days=30)
    older_start = end - timedelta(days=90)
    recent = _expense_rows(db, recent_start, end)
    older = _expense_rows(db, older_start, recent_start)
    if len(recent) < MIN_ROWS or len(older) < MIN_ROWS:
        return None
    recent_avg = sum(a for _, a in recent) / 30
    older_avg = sum(a for _, a in older) / 60
    if older_avg == 0:
        return None
    change = (recent_avg - older_avg) / older_avg * 100
    if abs(change) < 15:
        return None
    direction = "increased" if change > 0 else "decreased"
    return Insight(
        kind="daily_average_trend",
        severity="warning" if change > 0 else "positive",
        message=(
            f"Your average daily spending has {direction} {abs(change):.0f}% in the last month "
            f"({_fmt(recent_avg)}/day vs {_fmt(older_avg)}/day before)."
        ),
        value=round(change, 1),
    )


def _budget_alerts(db: Session, anchor: date) -> list[Insight]:
    insights: list[Insight] = []
    for budget in planning_service.list_budgets(db, anchor.year, anchor.month):
        progress = planning_service.budget_progress(db, budget, today=anchor)
        name = progress.category.name if progress.category else "Overall"
        days_left = planning_service.days_left_in_month(budget.year, budget.month, anchor)
        if progress.status == "exceeded":
            insights.append(
                Insight(
                    kind="budget_exceeded",
                    severity="warning",
                    message=f"You exceeded your {name} budget ({_fmt(progress.spent)} of {_fmt(progress.budget_amount)}).",
                    value=progress.fraction_used,
                )
            )
        elif progress.status == "warning":
            insights.append(
                Insight(
                    kind="budget_warning",
                    severity="warning",
                    message=f"{name} budget is {progress.fraction_used * 100:.0f}% used with {days_left} days left.",
                    value=progress.fraction_used,
                )
            )
    return insights


def generate_insights(db: Session, anchor: date | None = None) -> list[Insight]:
    anchor = anchor or date.today()
    ninety_days_ago = datetime.combine(anchor - timedelta(days=90), datetime.min.time())
    now = datetime.combine(anchor + timedelta(days=1), datetime.min.time())
    rows = _expense_rows(db, ninety_days_ago, now)

    insights: list[Insight] = []
    insights.extend(_budget_alerts(db, anchor))
    if len(rows) >= MIN_ROWS:
        for candidate in (
            _weekend_vs_weekday(rows),
            _top_weekday(rows),
            _peak_hours(rows),
            _highest_week(db, anchor),
            _merchant_frequency(db, anchor),
            _daily_average_trend(db, anchor),
        ):
            if candidate is not None:
                insights.append(candidate)
        insights.extend(_category_changes(db, anchor))
    return insights
