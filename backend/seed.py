"""Seed the database.

Usage:
    python seed.py            # defaults + ~3 months of realistic sample data
    python seed.py --defaults-only
    python seed.py --wipe     # delete the database file and reseed

Sample data uses a fixed RNG seed so reseeding is reproducible.
"""
import argparse
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models import (
    Account,
    Base,
    Budget,
    Category,
    DailyContext,
    Expense,
    ExpenseContext,
    Goal,
    GoalTransaction,
    Income,
    Merchant,
    Tag,
)

rng = random.Random(29)

CATEGORIES: dict[str, dict] = {
    "Food": {"icon": "🍜", "color": "#f97316", "children": ["Coffee", "Restaurant", "Grocery", "Snacks"]},
    "Transportation": {"icon": "🛵", "color": "#38bdf8", "children": ["Fuel", "Grab", "Bus", "Parking"]},
    "Entertainment": {"icon": "🎮", "color": "#a78bfa", "children": ["Games", "Movies", "Music"]},
    "Shopping": {"icon": "🛍️", "color": "#f472b6", "children": ["Clothes", "Electronics", "Household"]},
    "Education": {"icon": "📚", "color": "#34d399", "children": ["Books", "Courses", "Supplies"]},
    "Health": {"icon": "💊", "color": "#fb7185", "children": ["Pharmacy", "Gym", "Doctor"]},
    "Bills": {"icon": "🧾", "color": "#facc15", "children": ["Electricity", "Internet", "Phone", "Rent"]},
    "Other": {"icon": "📦", "color": "#94a3b8", "children": []},
}

ACCOUNTS = [
    ("Cash", "cash", None),
    ("Vietcombank", "bank", "Vietcombank"),
    ("MoMo", "e_wallet", None),
    ("ZaloPay", "e_wallet", None),
    ("Credit Card", "credit_card", "VPBank"),
]

# (merchant, subcategory, min_k, max_k, weight) — amounts in thousands of VND
MERCHANTS = [
    ("Highlands Coffee", "Coffee", 35, 75, 10),
    ("Phúc Long", "Coffee", 40, 70, 8),
    ("Local coffee shop", "Coffee", 20, 45, 12),
    ("Cơm tấm quán", "Restaurant", 30, 60, 14),
    ("Phở Hà Nội", "Restaurant", 40, 80, 8),
    ("Bún chả 34", "Restaurant", 35, 65, 6),
    ("KFC", "Restaurant", 80, 180, 4),
    ("WinMart", "Grocery", 100, 500, 8),
    ("Bách Hóa Xanh", "Grocery", 80, 350, 8),
    ("Circle K", "Snacks", 15, 60, 10),
    ("GS25", "Snacks", 15, 55, 6),
    ("Grab", "Grab", 25, 120, 12),
    ("Be", "Grab", 20, 100, 5),
    ("Petrolimex", "Fuel", 50, 150, 6),
    ("Xe buýt", "Bus", 7, 15, 4),
    ("Steam", "Games", 100, 800, 2),
    ("CGV Cinema", "Movies", 90, 250, 2),
    ("Spotify", "Music", 59, 59, 1),
    ("Shopee", "Clothes", 100, 800, 5),
    ("Lazada", "Electronics", 150, 2000, 2),
    ("Nhà thuốc Long Châu", "Pharmacy", 30, 200, 2),
    ("Gym membership", "Gym", 400, 400, 1),
    ("EVN", "Electricity", 300, 700, 1),
    ("VNPT", "Internet", 220, 220, 1),
    ("Viettel", "Phone", 100, 200, 1),
    ("Fahasa", "Books", 80, 300, 2),
]

TAGS = ["Impulse", "Discount", "Family", "Friends", "Project", "Exam week", "Vacation", "Birthday"]

EMOTIONS = ["calm", "happy", "stressed", "bored", "excited", "tired", "relaxed", "rewarding_myself"]
MOTIVATIONS = ["need", "convenience", "entertainment", "work", "study", "family", "health", "hobby", "discount", "fomo"]
PLANNED_HORIZONS = ["planned_today", "planned_this_week", "planned_this_month", "planned_over_month"]
PAYMENT_BY_ACCOUNT = {"Cash": "cash", "Vietcombank": "bank_transfer", "MoMo": "e_wallet", "ZaloPay": "e_wallet", "Credit Card": "card"}


def seed_defaults(db) -> dict:
    """Categories, accounts, merchants, tags. Returns lookup dicts."""
    cats: dict[str, Category] = {}
    for root_name, meta in CATEGORIES.items():
        root = Category(name=root_name, icon=meta["icon"], color=meta["color"])
        db.add(root)
        db.flush()
        cats[root_name] = root
        for child_name in meta["children"]:
            child = Category(name=child_name, parent_id=root.id, color=meta["color"])
            db.add(child)
            db.flush()
            cats[child_name] = child

    accounts: dict[str, Account] = {}
    for name, acc_type, bank in ACCOUNTS:
        account = Account(name=name, account_type=acc_type, currency="VND", bank=bank)
        db.add(account)
        db.flush()
        accounts[name] = account

    merchants: dict[str, Merchant] = {}
    for name, subcat, *_ in MERCHANTS:
        merchant = Merchant(name=name, category_hint_id=cats[subcat].id)
        db.add(merchant)
        db.flush()
        merchants[name] = merchant

    tags: dict[str, Tag] = {}
    for name in TAGS:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
        tags[name] = tag

    db.commit()
    return {"cats": cats, "accounts": accounts, "merchants": merchants, "tags": tags}


def seed_sample_data(db, lookups: dict, days: int = 100) -> None:
    cats, accounts, merchants, tags = (
        lookups["cats"],
        lookups["accounts"],
        lookups["merchants"],
        lookups["tags"],
    )
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_day = today - timedelta(days=days)

    weights = [m[4] for m in MERCHANTS]
    account_names = list(accounts)

    # --- Expenses ---
    for day_offset in range(days + 1):
        day = start_day + timedelta(days=day_offset)
        is_weekend = day.weekday() >= 5
        n = rng.choices([0, 1, 2, 3, 4, 5], weights=[4, 18, 30, 26, 14, 8])[0]
        if is_weekend:
            n = min(n + rng.choice([0, 1, 2]), 7)
        for _ in range(n):
            name, subcat, lo, hi, _w = rng.choices(MERCHANTS, weights=weights)[0]
            # Evening bias for purchase times
            hour = rng.choices(
                range(24),
                weights=[1, 1, 0, 0, 0, 0, 2, 5, 6, 4, 4, 8, 10, 5, 4, 4, 5, 7, 9, 12, 12, 8, 4, 2],
            )[0]
            dt = day + timedelta(hours=hour, minutes=rng.randint(0, 59))
            if dt > datetime.now():
                continue
            amount = Decimal(rng.randint(lo, hi)) * 1000
            account_name = rng.choices(account_names, weights=[30, 15, 25, 10, 20])[0]
            is_need = subcat in {"Grocery", "Fuel", "Bus", "Electricity", "Internet", "Phone", "Rent", "Pharmacy", "Supplies"} or (
                subcat in {"Restaurant", "Coffee"} and rng.random() < 0.4
            )
            impulse = rng.random() < (0.35 if not is_need else 0.08)
            expense = Expense(
                amount=amount,
                currency="VND",
                transaction_datetime=dt,
                account_id=accounts[account_name].id,
                merchant_id=merchants[name].id,
                category_id=cats[subcat].id,
                payment_method=PAYMENT_BY_ACCOUNT[account_name],
                is_need=is_need,
                note=None,
            )
            if impulse:
                expense.tags = [tags["Impulse"]]
            elif rng.random() < 0.1:
                expense.tags = [tags[rng.choice(["Friends", "Family", "Discount"])]]
            # ~60% of expenses get behavioral context (realistic partial logging)
            if rng.random() < 0.6:
                horizon = "not_planned" if impulse else rng.choice(PLANNED_HORIZONS)
                expense.context = ExpenseContext(
                    need_level=rng.randint(4, 5) if is_need else rng.randint(1, 3),
                    planned_purchase=horizon != "not_planned",
                    planning_horizon=horizon,
                    impulse_score=rng.randint(4, 5) if impulse else rng.randint(1, 2),
                    urgency=rng.randint(1, 5),
                    expected_regret=rng.randint(2, 4) if impulse else rng.randint(1, 2),
                    actual_regret=rng.randint(1, 5) if rng.random() < 0.4 else None,
                    satisfaction=rng.randint(2, 5) if rng.random() < 0.4 else None,
                    emotion=rng.choice(EMOTIONS),
                    motivation="need" if is_need else rng.choice(MOTIVATIONS),
                    shopping_channel="marketplace"
                    if name in {"Shopee", "Lazada"}
                    else "online"
                    if name in {"Steam", "Spotify"}
                    else "physical_store",
                    who_with=rng.choice(
                        ["alone", "alone", "alone", "friends", "family", "partner", "coworkers", "classmates"]
                    ),
                )
            db.add(expense)

    # --- Monthly recurring bills & income ---
    first_month = start_day.replace(day=1)
    cursor = first_month
    while cursor <= today:
        if cursor >= start_day:
            for merchant_name, subcat, amount_k in [("EVN", "Electricity", rng.randint(350, 650)), ("VNPT", "Internet", 220), ("Spotify", "Music", 59)]:
                dt = cursor.replace(day=min(rng.randint(3, 8), 28), hour=9)
                if dt <= datetime.now():
                    db.add(
                        Expense(
                            amount=Decimal(amount_k) * 1000,
                            transaction_datetime=dt,
                            account_id=accounts["Vietcombank"].id,
                            merchant_id=merchants[merchant_name].id,
                            category_id=cats[subcat].id,
                            payment_method="bank_transfer",
                            is_need=True,
                            is_recurring=True,
                        )
                    )
            salary_dt = cursor.replace(day=min(5, 28), hour=8)
            if salary_dt <= datetime.now():
                db.add(
                    Income(
                        amount=Decimal(rng.randint(14_000, 16_000)) * 1000,
                        source="salary",
                        account_id=accounts["Vietcombank"].id,
                        transaction_datetime=salary_dt,
                        is_recurring=True,
                        note="Monthly salary",
                    )
                )
        month = cursor.month + 1
        cursor = cursor.replace(year=cursor.year + (month > 12), month=(month - 1) % 12 + 1)

    # Occasional extra income
    for _ in range(4):
        dt = start_day + timedelta(days=rng.randint(0, days), hours=rng.randint(8, 20))
        if dt <= datetime.now():
            db.add(
                Income(
                    amount=Decimal(rng.randint(300, 2_000)) * 1000,
                    source=rng.choice(["gift", "refund", "scholarship", "other"]),
                    account_id=accounts[rng.choice(["MoMo", "Cash"])].id,
                    transaction_datetime=dt,
                )
            )

    # --- Daily context (~70% of days logged) ---
    for day_offset in range(days + 1):
        day = (start_day + timedelta(days=day_offset)).date()
        if rng.random() < 0.7:
            db.add(
                DailyContext(
                    date=day,
                    sleep_hours=round(rng.uniform(5.5, 8.5), 1),
                    stress_level=rng.randint(1, 5),
                    happiness=rng.randint(2, 5),
                    energy=rng.randint(2, 5),
                    exercise_minutes=rng.choice([0, 0, 0, 20, 30, 45, 60]),
                    study_hours=round(rng.uniform(0, 6), 1),
                )
            )

    # --- Budgets: one record per month for the last 4 months (history) ---
    budget_specs = [("Food", 3_000), ("Transportation", 800), ("Entertainment", 600), ("Shopping", 1_000)]
    year, month = today.year, today.month
    for offset in range(4):
        for cat_name, amount_k in budget_specs:
            wobble = rng.choice([-200, -100, 0, 0, 100])  # budgets evolve over time
            db.add(
                Budget(
                    category_id=cats[cat_name].id,
                    budget_amount=Decimal(max(amount_k + wobble, 200)) * 1000,
                    year=year,
                    month=month,
                    alert_threshold=0.8,
                )
            )
        month -= 1
        if month == 0:
            month, year = 12, year - 1

    # --- Goals with deposit/withdraw history ---
    def add_goal(title: str, target_k: int, priority: int, deadline_days: int | None, deposits: list[tuple[int, int, str | None]]) -> None:
        goal = Goal(
            title=title,
            target_amount=Decimal(target_k) * 1000,
            priority=priority,
            deadline=today.date() + timedelta(days=deadline_days) if deadline_days else None,
        )
        db.add(goal)
        db.flush()
        for days_ago, amount_k, note in deposits:
            db.add(
                GoalTransaction(
                    goal_id=goal.id,
                    amount=Decimal(abs(amount_k)) * 1000,
                    transaction_type="deposit" if amount_k > 0 else "withdraw",
                    date=today.date() - timedelta(days=days_ago),
                    note=note,
                )
            )

    add_goal("Emergency fund", 30_000, 1, None, [
        (95, 3_000, "Opening deposit"),
        (65, 3_500, "Monthly salary"),
        (35, 3_000, "Monthly salary"),
        (20, -1_500, "Used part of savings for emergency"),
        (5, 4_500, "Monthly salary + freelance payment"),
    ])
    add_goal("New laptop", 25_000, 2, 180, [
        (80, 2_000, "Initial saving"),
        (50, 2_000, None),
        (18, 2_000, "Freelance payment"),
    ])
    add_goal("Đà Lạt trip", 5_000, 3, 60, [
        (55, 1_500, None),
        (25, 1_200, "Birthday gift"),
        (8, 500, None),
    ])
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--defaults-only", action="store_true", help="seed reference data only")
    parser.add_argument("--wipe", action="store_true", help="delete the SQLite file first")
    args = parser.parse_args()

    if args.wipe and settings.database_url.startswith("sqlite"):
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        if db_path.exists():
            db_path.unlink()
            print(f"Deleted {db_path}")

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            print("Database already contains data — aborting. Use --wipe to reseed.")
            return
        lookups = seed_defaults(db)
        print("Seeded default categories, accounts, merchants, tags.")
        if not args.defaults_only:
            seed_sample_data(db, lookups)
            print(f"Seeded sample data: {db.query(Expense).count()} expenses, {db.query(Income).count()} incomes.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
