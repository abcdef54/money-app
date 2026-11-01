# Personal Finance Analytics

A local-first personal finance platform: a beautiful expense tracker today, designed from the schema up to become an AI-powered financial assistant tomorrow. All data stays on your computer in a single SQLite file.

## Stack

**Backend** — FastAPI · SQLAlchemy 2.0 · Alembic · SQLite (PostgreSQL-ready via `DATABASE_URL`) · Pydantic v2
**Frontend** — React 18 · TypeScript · Vite · Recharts · dark mode by default

## Quick start

### 1. Backend (http://localhost:8000)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

alembic upgrade head           # create the database schema
python seed.py                 # default categories/accounts/merchants + 3 months of sample data
# python seed.py --defaults-only   → reference data only, no sample transactions
# python seed.py --wipe            → delete finance.db and reseed

uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

### 2. Frontend (http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to the backend, so just open http://localhost:5173.

## Project layout

```
backend/
  app/
    core/        config (env-overridable), database session management
    models/      SQLAlchemy models — the ML-ready schema
    schemas/     Pydantic request/response models
    services/    ALL business logic (analytics, insights, budgets, CRUD)
    api/routes/  thin REST routers
  alembic/       migrations
  seed.py        seeding / reset script
frontend/
  src/
    lib/         typed API client, hooks, formatting
    components/  shared UI + the expense entry form
    pages/       Dashboard, Expenses, Income, Categories, Merchants,
                 Budgets, Goals, Analytics, Settings
```

## Design decisions that matter for future ML

- **Raw events only.** Totals, budget remainders, goal balances, averages and insights are always computed on the fly from raw rows — never stored.
- **Soft delete everywhere.** Deleted expenses stay in the database (`is_deleted`, `deleted_at`) and can be restored; history is never destroyed.
- **Every expense is an event with context.** `expense_contexts` captures need level, impulse score, planning horizon, expected vs *actual* regret and post-purchase satisfaction (fill them in later → labeled training data), emotion, motivation, channel, and company. The UI shows descriptive labels ("4 — Mostly Impulsive"); compact numeric/enum values are stored underneath. `daily_contexts` captures sleep, stress, mood, exercise and study hours per day.
- **Goals are ledgers, not counters.** Saved amounts are the sum of `goal_transactions` (deposits/withdrawals with dates and notes) — complete savings history is preserved.
- **Budgets are monthly records.** One row per (category, year, month); past months are permanent snapshots with completed/exceeded/unused statuses, enabling budget-vs-actual history. Categories marked *not budgetable* are excluded from all budget math but still appear in analytics.
- **Splits keep the parent.** Splitting an expense soft-deletes the original and links children via `parent_transaction_id` + `split_group_id`, so the raw event survives.
- **Merchant merge** rewrites expense references, keeping merchant statistics clean.
- **Heuristic insights now, models later.** The insights feed (`/api/insights`) is plain SQL + statistics; a future `/ml` router can plug into `app/api/routes/__init__.py` and reuse the same services.
- **Database portability.** Set `DATABASE_URL=postgresql+psycopg://...` to move to PostgreSQL; no code changes needed (Alembic reads the same setting).

## Useful endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/dashboard/summary?period=day\|week\|month\|year` | KPI summary |
| `GET /api/analytics/spending-over-time?granularity=day\|week\|month` | time series |
| `GET /api/analytics/by-category` / `by-merchant` | breakdowns |
| `GET /api/analytics/heatmap/weekday` / `hour` | when you spend |
| `GET /api/analytics/compare?period=week\|month\|year` | this vs last period |
| `GET /api/analytics/category-trends?months=6` | per-category monthly trends |
| `GET /api/insights` | heuristic behavioral insights |
| `GET /api/budgets/progress?year&month` | budget usage for a month (defaults to current) |
| `GET /api/budgets/history?months=12` | monthly budget snapshots with statuses |
| `GET /api/goals/{id}/transactions` | savings deposit/withdrawal history |
| `POST /api/goals/{id}/transactions` | record a deposit or withdrawal |
