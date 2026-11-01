"""Dashboard, analytics and insights endpoints."""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import (
    CategoryComparisonRow,
    Comparison,
    DashboardSummary,
    HeatmapCell,
    Insight,
    LargestPurchase,
    NamedAmount,
    TimePoint,
)
from app.services import analytics_service, dashboard_service, insights_service

router = APIRouter(tags=["analytics"])


def _range(
    start: date | None, end: date | None, default_days: int = 90
) -> tuple[datetime, datetime]:
    """Resolve an optional date range; defaults to the last N days."""
    end_dt = datetime.combine((end or date.today()) + timedelta(days=1), time.min)
    start_dt = (
        datetime.combine(start, time.min)
        if start
        else end_dt - timedelta(days=default_days)
    )
    return start_dt, end_dt


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    anchor: date | None = None,
    db: Session = Depends(get_db),
):
    return dashboard_service.summary(db, period, anchor or date.today())


@router.get("/analytics/spending-over-time", response_model=list[TimePoint])
def spending_over_time(
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    start_dt, end_dt = _range(start, end, default_days={"day": 30, "week": 84, "month": 365}[granularity])
    return analytics_service.spending_over_time(db, start_dt, end_dt, granularity)


@router.get("/analytics/by-category", response_model=list[NamedAmount])
def spending_by_category(
    start: date | None = None, end: date | None = None, db: Session = Depends(get_db)
):
    return analytics_service.by_category(db, *_range(start, end, 30))


@router.get("/analytics/by-merchant", response_model=list[NamedAmount])
def spending_by_merchant(
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    start_dt, end_dt = _range(start, end, 30)
    return analytics_service.by_merchant(db, start_dt, end_dt, limit)


@router.get("/analytics/heatmap/weekday", response_model=list[HeatmapCell])
def heatmap_weekday(
    start: date | None = None, end: date | None = None, db: Session = Depends(get_db)
):
    return analytics_service.heatmap_weekday(db, *_range(start, end, 90))


@router.get("/analytics/heatmap/hour", response_model=list[HeatmapCell])
def heatmap_hour(
    start: date | None = None, end: date | None = None, db: Session = Depends(get_db)
):
    return analytics_service.heatmap_hour(db, *_range(start, end, 90))


@router.get("/analytics/largest-purchases", response_model=list[LargestPurchase])
def largest_purchases(
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    start_dt, end_dt = _range(start, end, 90)
    return analytics_service.largest_purchases(db, start_dt, end_dt, limit)


@router.get("/analytics/category-trends")
def category_trends(
    months: int = Query(6, ge=2, le=24),
    anchor: date | None = None,
    db: Session = Depends(get_db),
):
    return analytics_service.category_trends(db, months, anchor or date.today())


@router.get("/analytics/compare", response_model=Comparison)
def compare_periods(
    period: str = Query("month", pattern="^(week|month|year)$"),
    anchor: date | None = None,
    db: Session = Depends(get_db),
):
    return analytics_service.compare_periods(db, period, anchor or date.today())


@router.get("/analytics/compare/categories", response_model=list[CategoryComparisonRow])
def compare_categories(
    period: str = Query("month", pattern="^(week|month|year)$"),
    anchor: date | None = None,
    db: Session = Depends(get_db),
):
    return analytics_service.compare_categories(db, period, anchor or date.today())


@router.get("/insights", response_model=list[Insight])
def insights(anchor: date | None = None, db: Session = Depends(get_db)):
    return insights_service.generate_insights(db, anchor)
