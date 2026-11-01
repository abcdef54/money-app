import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Empty, ErrorBanner, MoneyTooltip, Segmented } from "../components/ui";
import { api } from "../lib/api";
import { formatDateTime, formatMoney, formatMoneyShort, percent } from "../lib/format";
import { useAsync } from "../lib/hooks";

const FALLBACK_COLORS = ["#6366f1", "#38bdf8", "#34d399", "#facc15", "#f472b6", "#fb7185", "#a78bfa", "#94a3b8"];

function heatColor(value: number, max: number): string {
  if (max === 0 || value === 0) return "var(--bg-hover)";
  const intensity = Math.min(value / max, 1);
  return `rgba(99, 102, 241, ${0.15 + intensity * 0.85})`;
}

export default function AnalyticsPage() {
  const [granularity, setGranularity] = useState("day");
  const [comparePeriod, setComparePeriod] = useState("month");

  const series = useAsync(() => api.spendingOverTime(granularity), [granularity]);
  const categories = useAsync(() => api.byCategory(), []);
  const merchants = useAsync(() => api.byMerchant(undefined, undefined, 10), []);
  const trends = useAsync(() => api.categoryTrends(6), []);
  const weekday = useAsync(() => api.heatmapWeekday(), []);
  const hours = useAsync(() => api.heatmapHour(), []);
  const comparison = useAsync(() => api.comparePeriods(comparePeriod), [comparePeriod]);
  const catComparison = useAsync(() => api.compareCategories(comparePeriod), [comparePeriod]);
  const largest = useAsync(() => api.largestPurchases(8), []);

  const trendData =
    trends.data?.months.map((month, i) => {
      const row: Record<string, number | string> = { month };
      for (const s of trends.data!.series.slice(0, 6)) row[s.name] = s.data[i];
      return row;
    }) ?? [];

  const maxWeekday = Math.max(...(weekday.data?.map((c) => c.amount) ?? [0]));
  const maxHour = Math.max(...(hours.data?.map((c) => c.amount) ?? [0]));

  return (
    <>
      <div className="page-header">
        <h1>Analytics</h1>
      </div>
      <ErrorBanner error={series.error} />

      {/* Income vs expenses over time */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>Income vs expenses</h3>
          <Segmented
            options={[
              { value: "day", label: "Daily" },
              { value: "week", label: "Weekly" },
              { value: "month", label: "Monthly" },
            ]}
            value={granularity}
            onChange={setGranularity}
          />
        </div>
        {series.data && series.data.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={series.data}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="period" stroke="var(--text-faint)" fontSize={11} tickLine={false} />
              <YAxis stroke="var(--text-faint)" fontSize={11} tickLine={false} width={50} tickFormatter={(v: number) => formatMoneyShort(v)} />
              <Tooltip content={<MoneyTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="income" name="Income" fill="#34d399" radius={[3, 3, 0, 0]} />
              <Bar dataKey="expenses" name="Expenses" fill="#818cf8" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <Empty message="No data yet" />
        )}
      </div>

      {/* Comparison */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h3 style={{ margin: 0 }}>Period comparison</h3>
          <Segmented
            options={[
              { value: "week", label: "Week" },
              { value: "month", label: "Month" },
              { value: "year", label: "Year" },
            ]}
            value={comparePeriod}
            onChange={setComparePeriod}
          />
        </div>
        {comparison.data && (
          <div className="grid cols-3">
            {[comparison.data.previous, comparison.data.current].map((side, i) => (
              <div key={i} style={{ padding: "6px 0" }}>
                <div style={{ fontSize: 12, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
                  {side.label}
                </div>
                <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>{formatMoney(side.total)}</div>
                <div style={{ fontSize: 12, color: "var(--text-dim)" }}>
                  {side.count} transactions · {formatMoney(side.daily_average)}/day
                </div>
              </div>
            ))}
            <div style={{ padding: "6px 0" }}>
              <div style={{ fontSize: 12, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
                Change
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  marginTop: 4,
                  color: comparison.data.change_amount > 0 ? "var(--red)" : "var(--green)",
                }}
              >
                {percent(comparison.data.change_percent)}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-dim)" }}>
                {comparison.data.change_amount > 0 ? "+" : ""}
                {formatMoney(comparison.data.change_amount)}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        {/* Top merchants */}
        <div className="card">
          <h3>Top merchants (30 days)</h3>
          {merchants.data && merchants.data.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(merchants.data.length * 32, 120)}>
              <BarChart data={merchants.data} layout="vertical" margin={{ left: 30 }}>
                <XAxis type="number" stroke="var(--text-faint)" fontSize={11} tickFormatter={(v: number) => formatMoneyShort(v)} />
                <YAxis type="category" dataKey="name" stroke="var(--text-faint)" fontSize={11} width={110} tickLine={false} />
                <Tooltip content={<MoneyTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="amount" name="Spent" fill="#38bdf8" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty message="No merchant data" />
          )}
        </div>

        {/* Spending by category */}
        <div className="card">
          <h3>Spending by category (30 days)</h3>
          {categories.data && categories.data.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(Math.min(categories.data.length, 10) * 32, 120)}>
              <BarChart data={categories.data.slice(0, 10)} layout="vertical" margin={{ left: 30 }}>
                <XAxis type="number" stroke="var(--text-faint)" fontSize={11} tickFormatter={(v: number) => formatMoneyShort(v)} />
                <YAxis type="category" dataKey="name" stroke="var(--text-faint)" fontSize={11} width={110} tickLine={false} />
                <Tooltip content={<MoneyTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="amount" name="Spent" radius={[0, 3, 3, 0]}>
                  {categories.data.slice(0, 10).map((entry, i) => (
                    <Cell key={i} fill={entry.color ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty message="No category data" />
          )}
        </div>
      </div>

      {/* Category trends */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Category trends (6 months)</h3>
        {trendData.length > 0 && trends.data ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendData}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="month" stroke="var(--text-faint)" fontSize={11} tickLine={false} />
              <YAxis stroke="var(--text-faint)" fontSize={11} tickLine={false} width={50} tickFormatter={(v: number) => formatMoneyShort(v)} />
              <Tooltip content={<MoneyTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {trends.data.series.slice(0, 6).map((s, i) => (
                <Line
                  key={s.name}
                  type="monotone"
                  dataKey={s.name}
                  stroke={s.color ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <Empty message="Not enough history yet" />
        )}
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        {/* Weekday heatmap */}
        <div className="card">
          <h3>Spending by weekday (90 days)</h3>
          <div style={{ display: "flex", gap: 6 }}>
            {weekday.data?.map((cell) => (
              <div key={cell.x} style={{ flex: 1, textAlign: "center" }}>
                <div
                  title={`${cell.label}: ${formatMoney(cell.amount)} (${cell.count} purchases)`}
                  style={{
                    height: 64,
                    borderRadius: 8,
                    background: heatColor(cell.amount, maxWeekday),
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 11,
                    fontWeight: 600,
                    transition: "transform 0.15s",
                    cursor: "default",
                  }}
                >
                  {formatMoneyShort(cell.amount)}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 4 }}>{cell.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Hour heatmap */}
        <div className="card">
          <h3>Spending by hour (90 days)</h3>
          <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 80 }}>
            {hours.data?.map((cell) => (
              <div
                key={cell.x}
                title={`${cell.label}: ${formatMoney(cell.amount)} (${cell.count} purchases)`}
                style={{
                  flex: 1,
                  height: `${maxHour ? Math.max((cell.amount / maxHour) * 100, 3) : 3}%`,
                  background: heatColor(cell.amount, maxHour),
                  borderRadius: 3,
                }}
              />
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-faint)", marginTop: 6 }}>
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
            <span>23:00</span>
          </div>
        </div>
      </div>

      <div className="grid cols-2">
        {/* Category comparison table */}
        <div className="card" style={{ padding: 0 }}>
          <h3 style={{ padding: "20px 20px 0" }}>Category comparison ({comparePeriod})</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Category</th>
                <th className="num">Previous</th>
                <th className="num">Current</th>
                <th className="num">Change</th>
              </tr>
            </thead>
            <tbody>
              {catComparison.data?.slice(0, 10).map((row, i) => (
                <tr key={i}>
                  <td>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span className="dot" style={{ background: row.color ?? "var(--text-faint)" }} />
                      {row.name}
                    </span>
                  </td>
                  <td className="num" style={{ color: "var(--text-dim)" }}>{formatMoneyShort(row.previous)}</td>
                  <td className="num">{formatMoneyShort(row.current)}</td>
                  <td
                    className="num"
                    style={{
                      fontWeight: 600,
                      color:
                        row.change_percent == null
                          ? "var(--text-faint)"
                          : row.change_percent > 0
                            ? "var(--red)"
                            : "var(--green)",
                    }}
                  >
                    {percent(row.change_percent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Largest purchases */}
        <div className="card" style={{ padding: 0 }}>
          <h3 style={{ padding: "20px 20px 0" }}>Largest purchases (90 days)</h3>
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>Merchant</th>
                <th>Category</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {largest.data?.map((purchase) => (
                <tr key={purchase.id}>
                  <td style={{ color: "var(--text-dim)", whiteSpace: "nowrap" }}>
                    {formatDateTime(purchase.transaction_datetime)}
                  </td>
                  <td>{purchase.merchant ?? "–"}</td>
                  <td style={{ color: "var(--text-dim)" }}>{purchase.category ?? "–"}</td>
                  <td className="num" style={{ fontWeight: 600 }}>{formatMoney(purchase.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
