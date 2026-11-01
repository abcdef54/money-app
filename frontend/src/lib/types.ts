// API types mirroring the backend Pydantic schemas.

export interface Account {
  id: number;
  name: string;
  account_type: string;
  currency: string;
  bank: string | null;
  active: boolean;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  icon: string | null;
  color: string | null;
  active: boolean;
  budgetable: boolean;
  sort_order: number;
}

export interface CategoryTree extends Category {
  children: CategoryTree[];
}

export interface Merchant {
  id: number;
  name: string;
  category_hint_id: number | null;
  notes: string | null;
  active: boolean;
}

export interface Tag {
  id: number;
  name: string;
  color: string | null;
}

export interface ExpenseContext {
  need_level: number | null;
  planned_purchase: boolean | null;
  planning_horizon: string | null;
  impulse_score: number | null;
  urgency: number | null;
  expected_regret: number | null;
  actual_regret: number | null;
  satisfaction: number | null;
  emotion: string | null;
  motivation: string | null;
  shopping_channel: string | null;
  who_with: string | null;
}

export interface Expense {
  id: number;
  amount: number;
  currency: string;
  transaction_datetime: string;
  account_id: number | null;
  merchant_id: number | null;
  category_id: number | null;
  location_id: number | null;
  payment_method: string | null;
  note: string | null;
  is_need: boolean | null;
  is_recurring: boolean;
  parent_transaction_id: number | null;
  split_group_id: string | null;
  is_deleted: boolean;
  account: Account | null;
  merchant: Merchant | null;
  category: Category | null;
  tags: Tag[];
  context: (ExpenseContext & { expense_id: number }) | null;
}

export interface ExpensePage {
  items: Expense[];
  total: number;
  page: number;
  page_size: number;
}

export interface Income {
  id: number;
  amount: number;
  currency: string;
  source: string;
  account_id: number | null;
  transaction_datetime: string;
  note: string | null;
  is_recurring: boolean;
  account: Account | null;
}

export interface Budget {
  id: number;
  category_id: number | null;
  budget_amount: number;
  year: number;
  month: number;
  rollover: boolean;
  alert_threshold: number;
  category: Category | null;
}

export interface BudgetProgress extends Budget {
  spent: number;
  remaining: number;
  fraction_used: number;
  // current month: ok | warning | exceeded — past months: completed | exceeded | unused
  status: "ok" | "warning" | "exceeded" | "completed" | "unused";
}

export interface BudgetHistoryMonth {
  year: number;
  month: number;
  label: string;
  total_budget: number;
  total_spent: number;
  completed: number;
  exceeded: number;
  unused: number;
  items: BudgetProgress[];
}

export interface Goal {
  id: number;
  title: string;
  target_amount: number;
  current_amount: number; // computed from transactions, never stored
  deadline: string | null;
  priority: number;
  completed: boolean;
}

export interface GoalTransaction {
  id: number;
  goal_id: number;
  amount: number;
  transaction_type: "deposit" | "withdraw";
  date: string;
  note: string | null;
}

export interface DailyContext {
  id: number;
  date: string;
  sleep_hours: number | null;
  stress_level: number | null;
  happiness: number | null;
  energy: number | null;
  exercise_minutes: number | null;
  study_hours: number | null;
  notes: string | null;
}

export interface NamedAmount {
  id: number | null;
  name: string;
  amount: number;
  count: number;
  color: string | null;
}

export interface DashboardSummary {
  period: string;
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  balance: number;
  savings_rate: number;
  daily_average: number;
  expense_count: number;
  largest_expense: {
    id: number;
    amount: number;
    note: string | null;
    transaction_datetime: string;
    merchant: string | null;
  } | null;
  largest_category: NamedAmount | null;
  largest_merchant: NamedAmount | null;
}

export interface TimePoint {
  period: string;
  expenses: number;
  income: number;
  count: number;
}

export interface HeatmapCell {
  x: number;
  label: string;
  amount: number;
  count: number;
}

export interface ComparisonSide {
  label: string;
  start_date: string;
  end_date: string;
  total: number;
  count: number;
  daily_average: number;
}

export interface Comparison {
  current: ComparisonSide;
  previous: ComparisonSide;
  change_amount: number;
  change_percent: number | null;
}

export interface CategoryComparisonRow {
  category_id: number | null;
  name: string;
  color: string | null;
  current: number;
  previous: number;
  change_percent: number | null;
}

export interface Insight {
  kind: string;
  severity: "info" | "warning" | "positive";
  message: string;
  value: number | null;
}

export interface LargestPurchase {
  id: number;
  amount: number;
  merchant: string | null;
  category: string | null;
  note: string | null;
  transaction_datetime: string;
}

export interface CategoryTrends {
  months: string[];
  series: { name: string; color: string | null; data: number[] }[];
}
