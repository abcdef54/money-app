// Thin typed API client. All endpoints are relative — Vite proxies /api
// to the FastAPI backend in dev.
import type {
  Account,
  Budget,
  BudgetHistoryMonth,
  BudgetProgress,
  Category,
  CategoryComparisonRow,
  CategoryTree,
  CategoryTrends,
  Comparison,
  DailyContext,
  DashboardSummary,
  Expense,
  ExpensePage,
  Goal,
  GoalTransaction,
  HeatmapCell,
  Income,
  Insight,
  LargestPurchase,
  Merchant,
  NamedAmount,
  Tag,
  TimePoint,
} from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export const api = {
  // Expenses
  listExpenses: (params: Record<string, string | number | boolean | undefined>) =>
    request<ExpensePage>(`/api/expenses${qs(params)}`),
  createExpense: (data: unknown) =>
    request<Expense>("/api/expenses", { method: "POST", body: JSON.stringify(data) }),
  updateExpense: (id: number, data: unknown) =>
    request<Expense>(`/api/expenses/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteExpense: (id: number) => request<void>(`/api/expenses/${id}`, { method: "DELETE" }),
  restoreExpense: (id: number) =>
    request<Expense>(`/api/expenses/${id}/restore`, { method: "POST" }),

  // Incomes
  listIncomes: (params: Record<string, string | number | undefined>) =>
    request<{ items: Income[]; total: number }>(`/api/incomes${qs(params)}`),
  createIncome: (data: unknown) =>
    request<Income>("/api/incomes", { method: "POST", body: JSON.stringify(data) }),
  updateIncome: (id: number, data: unknown) =>
    request<Income>(`/api/incomes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteIncome: (id: number) => request<void>(`/api/incomes/${id}`, { method: "DELETE" }),

  // Reference data
  listAccounts: () => request<Account[]>("/api/accounts"),
  createAccount: (data: unknown) =>
    request<Account>("/api/accounts", { method: "POST", body: JSON.stringify(data) }),
  updateAccount: (id: number, data: unknown) =>
    request<Account>(`/api/accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteAccount: (id: number) => request<void>(`/api/accounts/${id}`, { method: "DELETE" }),

  listCategories: (includeInactive = false) =>
    request<Category[]>(`/api/categories${qs({ include_inactive: includeInactive })}`),
  categoryTree: () => request<CategoryTree[]>("/api/categories/tree"),
  createCategory: (data: unknown) =>
    request<Category>("/api/categories", { method: "POST", body: JSON.stringify(data) }),
  updateCategory: (id: number, data: unknown) =>
    request<Category>(`/api/categories/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCategory: (id: number) => request<void>(`/api/categories/${id}`, { method: "DELETE" }),

  listMerchants: (search?: string) => request<Merchant[]>(`/api/merchants${qs({ search })}`),
  createMerchant: (data: unknown) =>
    request<Merchant>("/api/merchants", { method: "POST", body: JSON.stringify(data) }),
  updateMerchant: (id: number, data: unknown) =>
    request<Merchant>(`/api/merchants/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteMerchant: (id: number) => request<void>(`/api/merchants/${id}`, { method: "DELETE" }),
  mergeMerchants: (sourceIds: number[], targetId: number) =>
    request<Merchant>("/api/merchants/merge", {
      method: "POST",
      body: JSON.stringify({ source_ids: sourceIds, target_id: targetId }),
    }),

  listTags: () => request<Tag[]>("/api/tags"),
  createTag: (data: unknown) =>
    request<Tag>("/api/tags", { method: "POST", body: JSON.stringify(data) }),
  deleteTag: (id: number) => request<void>(`/api/tags/${id}`, { method: "DELETE" }),

  // Budgets (monthly records)
  listBudgets: (year?: number, month?: number) =>
    request<Budget[]>(`/api/budgets${qs({ year, month })}`),
  budgetsProgress: (year?: number, month?: number) =>
    request<BudgetProgress[]>(`/api/budgets/progress${qs({ year, month })}`),
  budgetsHistory: (months = 12) =>
    request<BudgetHistoryMonth[]>(`/api/budgets/history${qs({ months })}`),
  createBudget: (data: unknown) =>
    request<Budget>("/api/budgets", { method: "POST", body: JSON.stringify(data) }),
  updateBudget: (id: number, data: unknown) =>
    request<Budget>(`/api/budgets/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteBudget: (id: number) => request<void>(`/api/budgets/${id}`, { method: "DELETE" }),

  // Goals + savings transactions
  listGoals: () => request<Goal[]>("/api/goals"),
  createGoal: (data: unknown) =>
    request<Goal>("/api/goals", { method: "POST", body: JSON.stringify(data) }),
  updateGoal: (id: number, data: unknown) =>
    request<Goal>(`/api/goals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteGoal: (id: number) => request<void>(`/api/goals/${id}`, { method: "DELETE" }),
  listGoalTransactions: (goalId: number) =>
    request<GoalTransaction[]>(`/api/goals/${goalId}/transactions`),
  createGoalTransaction: (goalId: number, data: unknown) =>
    request<Goal>(`/api/goals/${goalId}/transactions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteGoalTransaction: (goalId: number, transactionId: number) =>
    request<Goal>(`/api/goals/${goalId}/transactions/${transactionId}`, { method: "DELETE" }),

  // Daily context
  listDailyContexts: () => request<DailyContext[]>("/api/daily-context"),
  upsertDailyContext: (data: unknown) =>
    request<DailyContext>("/api/daily-context", { method: "PUT", body: JSON.stringify(data) }),

  // Dashboard / analytics / insights
  dashboardSummary: (period: string, anchor?: string) =>
    request<DashboardSummary>(`/api/dashboard/summary${qs({ period, anchor })}`),
  spendingOverTime: (granularity: string, start?: string, end?: string) =>
    request<TimePoint[]>(`/api/analytics/spending-over-time${qs({ granularity, start, end })}`),
  byCategory: (start?: string, end?: string) =>
    request<NamedAmount[]>(`/api/analytics/by-category${qs({ start, end })}`),
  byMerchant: (start?: string, end?: string, limit = 15) =>
    request<NamedAmount[]>(`/api/analytics/by-merchant${qs({ start, end, limit })}`),
  heatmapWeekday: () => request<HeatmapCell[]>("/api/analytics/heatmap/weekday"),
  heatmapHour: () => request<HeatmapCell[]>("/api/analytics/heatmap/hour"),
  largestPurchases: (limit = 10) =>
    request<LargestPurchase[]>(`/api/analytics/largest-purchases${qs({ limit })}`),
  categoryTrends: (months = 6) =>
    request<CategoryTrends>(`/api/analytics/category-trends${qs({ months })}`),
  comparePeriods: (period: string) => request<Comparison>(`/api/analytics/compare${qs({ period })}`),
  compareCategories: (period: string) =>
    request<CategoryComparisonRow[]>(`/api/analytics/compare/categories${qs({ period })}`),
  insights: () => request<Insight[]>("/api/insights"),
};
