import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Empty, ErrorBanner, MoneyTooltip, ProgressBar, Segmented, StatCard } from "../components/ui";
import { api } from "../lib/api";
import { formatMoney, formatMoneyShort } from "../lib/format";
import { useAsync } from "../lib/hooks";

const FALLBACK_COLORS = ["#6366f1", "#38bdf8", "#34d399", "#facc15", "#f472b6", "#fb7185", "#a78bfa", "#94a3b8"];

export default function DashboardPage() {
  const [period, setPeriod] = useState("month");

  const summary = useAsync(() => api.dashboardSummary(period), [period]);
  const series = useAsync(
    () => api.spendingOverTime(period === "year" ? "month" : "day"),
    [period],
  );
  const categories = useAsync(() => api.byCategory(), []);
  const insights = useAsync(() => api.insights(), []);
  const budgets = useAsync(() => api.budgetsProgress(), []);

  const s = summary.data;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          {s && (
            <div className="sub">
              {s.start_date} → {s.end_date} · {s.expense_count} expenses
            </div>
          )}
        </div>
        <Segmented
          options={[
            { value: "day", label: "Today" },
            { value: "week", label: "Week" },
            { value: "month", label: "Month" },
            { value: "year", label: "Year" },
          ]}
          value={period}
          onChange={setPeriod}
        />
      </div>

      <ErrorBanner error={summary.error} />

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <StatCard label="Income" value={s ? formatMoney(s.total_income) : "…"} tone="positive" />
        <StatCard label="Expenses" value={s ? formatMoney(s.total_expenses) : "…"} tone="negative" />
        <StatCard
          label="Balance"
          value={s ? formatMoney(s.balance) : "…"}
          tone={s && s.balance >= 0 ? "positive" : "negative"}
          sub={s && s.total_income > 0 ? `Savings rate ${(s.savings_rate * 100).toFixed(0)}%` : undefined}
        />
        <StatCard label="Daily average" value={s ? formatMoney(s.daily_average) : "…"} />
      </div>

      <div className="grid cols-3" style={{ marginBottom: 16 }}>
        <StatCard
          label="Largest expense"
          value={s?.largest_expense ? formatMoney(s.largest_expense.amount) : "–"}
          sub={s?.largest_expense?.merchant ?? s?.largest_expense?.note ?? undefined}
        />
        <StatCard
          label="Top category"
          value={s?.largest_category ? s.largest_category.name : "–"}
          sub={s?.largest_category ? formatMoney(s.largest_category.amount) : undefined}
        />
        <StatCard
          label="Top merchant"
          value={s?.largest_merchant ? s.largest_merchant.name : "–"}
          sub={
            s?.largest_merchant
              ? `${formatMoney(s.largest_merchant.amount)} · ${s.largest_merchant.count}×`
              : undefined
          }
        />
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3>Spending over time</h3>
          {series.data && series.data.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={series.data}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="period"
                  stroke="var(--text-faint)"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  stroke="var(--text-faint)"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v: number) => formatMoneyShort(v)}
                  width={50}
                />
                <Tooltip content={<MoneyTooltip />} />
                <Area
                  type="monotone"
                  dataKey="expenses"
                  name="Expenses"
                  stroke="#818cf8"
                  strokeWidth={2}
                  fill="url(#spendGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <Empty message="No spending yet" />
          )}
        </div>

        <div className="card">
          <h3>Spending by category (30 days)</h3>
          {categories.data && categories.data.length > 0 ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ResponsiveContainer width="55%" height={240}>
                <PieChart>
                  <Pie
                    data={categories.data.slice(0, 8)}
                    dataKey="amount"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {categories.data.slice(0, 8).map((entry, i) => (
                      <Cell key={i} fill={entry.color ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<MoneyTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                {categories.data.slice(0, 8).map((c, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                    <span className="dot" style={{ background: c.color ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length] }} />
                    <span style={{ flex: 1, color: "var(--text-dim)" }}>{c.name}</span>
                    <span style={{ fontVariantNumeric: "tabular-nums" }}>{formatMoneyShort(c.amount)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Empty message="No categorized spending yet" />
          )}
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Insights</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {insights.data && insights.data.length > 0 ? (
              insights.data.slice(0, 6).map((insight, i) => (
                <div key={i} className={`insight ${insight.severity}`}>
                  <span className="badge">
                    {insight.severity === "warning" ? "⚠️" : insight.severity === "positive" ? "✅" : "💡"}
                  </span>
                  <span>{insight.message}</span>
                </div>
              ))
            ) : (
              <Empty message="Insights appear once you have enough data" />
            )}
          </div>
        </div>

        <div className="card">
          <h3>Budgets this month</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {budgets.data && budgets.data.length > 0 ? (
              budgets.data.map((b) => (
                <div key={b.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, fontSize: 13 }}>
                    <span>{b.category?.name ?? "Overall"}</span>
                    <span style={{ color: "var(--text-dim)" }}>
                      {formatMoney(b.spent)} / {formatMoney(b.budget_amount)}
                    </span>
                  </div>
                  <ProgressBar fraction={b.fraction_used} status={b.status} />
                </div>
              ))
            ) : (
              <Empty message="No budgets set — create one in Budgets" />
            )}
          </div>
        </div>
      </div>
    </>
  );
}
