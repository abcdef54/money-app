"""v2: goal transactions, monthly budgets, richer context, category uniqueness

- goals: current_amount moved into goal_transactions (initial deposit), column dropped
- budgets: start_date/end_date replaced by year/month (historical monthly records)
- expense_contexts: + satisfaction, + planning_horizon, wider shopping_channel
- categories: duplicates merged, unique (parent, lower(name)) index added

Revision ID: b7d3e9f2c4a1
Revises: 46b7ca21dd2e
Create Date: 2026-07-11

"""
from collections import defaultdict
from datetime import date, datetime

import sqlalchemy as sa
from alembic import op

revision = "b7d3e9f2c4a1"
down_revision = "46b7ca21dd2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now()

    # ------------------------------------------------------------------
    # 1. Merge duplicate categories (created by the double-submit bug),
    #    then enforce uniqueness at the database level.
    # ------------------------------------------------------------------
    rows = conn.execute(
        sa.text("SELECT id, parent_id, lower(name) FROM categories ORDER BY id")
    ).fetchall()
    groups: dict[tuple, list[int]] = defaultdict(list)
    for cat_id, parent_id, lname in rows:
        groups[(parent_id or 0, lname)].append(cat_id)
    for ids in groups.values():
        if len(ids) < 2:
            continue
        keep, *dupes = ids  # lowest id wins
        for dup in dupes:
            for stmt in (
                "UPDATE expenses SET category_id = :keep WHERE category_id = :dup",
                "UPDATE merchants SET category_hint_id = :keep WHERE category_hint_id = :dup",
                "UPDATE budgets SET category_id = :keep WHERE category_id = :dup",
                "UPDATE categories SET parent_id = :keep WHERE parent_id = :dup",
            ):
                conn.execute(sa.text(stmt), {"keep": keep, "dup": dup})
            conn.execute(sa.text("DELETE FROM categories WHERE id = :dup"), {"dup": dup})

    op.create_index(
        "uq_categories_parent_name",
        "categories",
        [sa.text("coalesce(parent_id, 0)"), sa.text("lower(name)")],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 2. Goal transactions: preserve saved amounts as initial deposits.
    # ------------------------------------------------------------------
    op.create_table(
        "goal_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "goal_id",
            sa.Integer(),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_goal_transactions_goal_id", "goal_transactions", ["goal_id"])

    for goal_id, amount in conn.execute(
        sa.text("SELECT id, current_amount FROM goals WHERE current_amount > 0")
    ).fetchall():
        conn.execute(
            sa.text(
                "INSERT INTO goal_transactions "
                "(goal_id, amount, transaction_type, date, note, created_at, updated_at) "
                "VALUES (:g, :a, 'deposit', :d, 'Initial balance', :n, :n)"
            ),
            {"g": goal_id, "a": amount, "d": date.today().isoformat(), "n": now},
        )

    with op.batch_alter_table("goals") as batch:
        batch.drop_column("current_amount")

    # ------------------------------------------------------------------
    # 3. Budgets become monthly historical records.
    # ------------------------------------------------------------------
    op.add_column("budgets", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("budgets", sa.Column("month", sa.Integer(), nullable=True))

    for budget_id, start in conn.execute(sa.text("SELECT id, start_date FROM budgets")).fetchall():
        start_str = str(start)  # SQLite returns 'YYYY-MM-DD'
        conn.execute(
            sa.text("UPDATE budgets SET year = :y, month = :m WHERE id = :id"),
            {"y": int(start_str[0:4]), "m": int(start_str[5:7]), "id": budget_id},
        )

    # Drop duplicate budgets for the same (category, year, month), keep lowest id.
    budget_rows = conn.execute(
        sa.text("SELECT id, coalesce(category_id, 0), year, month FROM budgets ORDER BY id")
    ).fetchall()
    seen: set[tuple] = set()
    for budget_id, cat, year, month in budget_rows:
        key = (cat, year, month)
        if key in seen:
            conn.execute(sa.text("DELETE FROM budgets WHERE id = :id"), {"id": budget_id})
        else:
            seen.add(key)

    with op.batch_alter_table("budgets") as batch:
        batch.alter_column("year", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("month", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("start_date")
        batch.drop_column("end_date")

    op.create_index(
        "uq_budgets_category_period",
        "budgets",
        [sa.text("coalesce(category_id, 0)"), "year", "month"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 4. Richer behavioral context fields.
    # ------------------------------------------------------------------
    with op.batch_alter_table("expense_contexts") as batch:
        batch.add_column(sa.Column("satisfaction", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("planning_horizon", sa.String(30), nullable=True))
        batch.alter_column(
            "shopping_channel", existing_type=sa.String(10), type_=sa.String(30)
        )


def downgrade() -> None:
    with op.batch_alter_table("expense_contexts") as batch:
        batch.drop_column("planning_horizon")
        batch.drop_column("satisfaction")
        batch.alter_column("shopping_channel", existing_type=sa.String(30), type_=sa.String(10))

    op.drop_index("uq_budgets_category_period", table_name="budgets")
    op.add_column("budgets", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("budgets", sa.Column("end_date", sa.Date(), nullable=True))
    conn = op.get_bind()
    for budget_id, year, month in conn.execute(sa.text("SELECT id, year, month FROM budgets")):
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        conn.execute(
            sa.text("UPDATE budgets SET start_date = :s, end_date = :e WHERE id = :id"),
            {"s": start.isoformat(), "e": end.isoformat(), "id": budget_id},
        )
    with op.batch_alter_table("budgets") as batch:
        batch.alter_column("start_date", existing_type=sa.Date(), nullable=False)
        batch.alter_column("end_date", existing_type=sa.Date(), nullable=False)
        batch.drop_column("month")
        batch.drop_column("year")

    op.add_column("goals", sa.Column("current_amount", sa.Numeric(14, 2), nullable=True))
    conn.execute(
        sa.text(
            "UPDATE goals SET current_amount = coalesce((SELECT sum(CASE WHEN transaction_type = 'deposit' "
            "THEN amount ELSE -amount END) FROM goal_transactions WHERE goal_id = goals.id), 0)"
        )
    )
    with op.batch_alter_table("goals") as batch:
        batch.alter_column("current_amount", existing_type=sa.Numeric(14, 2), nullable=False)
    op.drop_index("ix_goal_transactions_goal_id", table_name="goal_transactions")
    op.drop_table("goal_transactions")

    op.drop_index("uq_categories_parent_name", table_name="categories")
