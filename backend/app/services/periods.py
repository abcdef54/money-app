"""Date-period helpers shared by dashboard/analytics/insights services."""
from datetime import date, datetime, time, timedelta


def day_bounds(anchor: date) -> tuple[datetime, datetime]:
    start = datetime.combine(anchor, time.min)
    return start, start + timedelta(days=1)


def week_bounds(anchor: date) -> tuple[datetime, datetime]:
    """ISO week: Monday .. Sunday."""
    monday = anchor - timedelta(days=anchor.weekday())
    start = datetime.combine(monday, time.min)
    return start, start + timedelta(days=7)


def month_bounds(anchor: date) -> tuple[datetime, datetime]:
    start = datetime.combine(anchor.replace(day=1), time.min)
    if anchor.month == 12:
        end = datetime(anchor.year + 1, 1, 1)
    else:
        end = datetime(anchor.year, anchor.month + 1, 1)
    return start, end


def year_bounds(anchor: date) -> tuple[datetime, datetime]:
    return datetime(anchor.year, 1, 1), datetime(anchor.year + 1, 1, 1)


def period_bounds(period: str, anchor: date) -> tuple[datetime, datetime]:
    if period == "day":
        return day_bounds(anchor)
    if period == "week":
        return week_bounds(anchor)
    if period == "month":
        return month_bounds(anchor)
    if period == "year":
        return year_bounds(anchor)
    raise ValueError(f"Unknown period: {period}")


def previous_period_bounds(period: str, anchor: date) -> tuple[datetime, datetime]:
    start, _ = period_bounds(period, anchor)
    prev_anchor = (start - timedelta(days=1)).date()
    return period_bounds(period, prev_anchor)


def bucket_key(dt: datetime, granularity: str) -> str:
    """Stable string key for a time bucket."""
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if granularity == "month":
        return dt.strftime("%Y-%m")
    raise ValueError(f"Unknown granularity: {granularity}")


def iter_buckets(start: datetime, end: datetime, granularity: str) -> list[str]:
    """Every bucket key between start and end (inclusive of start's bucket)."""
    keys: list[str] = []
    cursor = start
    step = timedelta(days=1)
    while cursor < end:
        key = bucket_key(cursor, granularity)
        if not keys or keys[-1] != key:
            keys.append(key)
        cursor += step
    return keys
