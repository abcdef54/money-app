import { FormEvent, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Empty, ErrorBanner, Modal, MoneyTooltip, ProgressBar } from "../components/ui";
import { api } from "../lib/api";
import { formatMoney, formatMoneyShort } from "../lib/format";
import { useAsync } from "../lib/hooks";
import { monthLabel } from "../lib/labels";
import type { Budget } from "../lib/types";

const STATUS_COLORS: Record<string, string> = {
  ok: "var(--green)",
  completed: "var(--green)",
  warning: "var(--yellow)",
  exceeded: "var(--red)",
  unused: "var(--text-faint)",
};

function BudgetForm({
  initial,
  year,
  month,
  onSaved,
  onCancel,
}: {
  initial?: Budget;
  year: number;
  month: number;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const categories = useAsync(() => api.listCategories(), []);
  const [categoryId, setCategoryId] = useState(initial?.category_id?.toString() ?? "");
  const [amount, setAmount] = useState(initial ? String(initial.budget_amount) : "");
  const [formYear, setFormYear] = useState(String(initial?.year ?? year));
  const [formMonth, setFormMonth] = useState(String(initial?.month ?? month));
  const [threshold, setThreshold] = useState(String((initial?.alert_threshold ?? 0.8) * 100));
  const [rollover, setRollover] = useState(initial?.rollover ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      const payload = {
        category_id: categoryId ? Number(categoryId) : null,
        budget_amount: Number(amount),
        year: Number(formYear),
        month: Number(formMonth),
        alert_threshold: Number(threshold) / 100,
        rollover,
      };
      if (initial) await api.updateBudget(initial.id, payload);
      else await api.createBudget(payload);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {error && <div className="error-banner">{error}</div>}
      <div className="form-row">
        <label className="field" style={{ flex: 2 }}>
          Category
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">Overall (all spending)</option>
            {categories.data
              ?.filter((c) => c.budgetable)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.parent_id ? "· " : ""}{c.name}
                </option>
              ))}
          </select>
        </label>
        <label className="field">
          Amount (₫) *
          <input type="number" min="1" required value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
      </div>
      <div className="form-row">
        <label className="field">
          Month
          <select value={formMonth} onChange={(e) => setFormMonth(e.target.value)}>
            {Array.from({ length: 12 }, (_, i) => (
              <option key={i + 1} value={i + 1}>
                {monthLabel(2000, i + 1).split(" ")[0]}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Year
          <input type="number" min="2000" max="2100" required value={formYear} onChange={(e) => setFormYear(e.target.value)} />
        </label>
        <label className="field">
          Alert at (%)
          <input type="number" min="0" max="100" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        </label>
      </div>
      <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <input type="checkbox" style={{ width: "auto" }} checked={rollover} onChange={(e) => setRollover(e.target.checked)} />
        Roll unused budget over to the next period
      </label>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : initial ? "Save" : "Create budget"}
        </button>
      </div>
    </form>
  );
}

export default function BudgetsPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [modal, setModal] = useState<"create" | Budget | null>(null);

  const progress = useAsync(() => api.budgetsProgress(year, month), [year, month]);
  const history = useAsync(() => api.budgetsHistory(12), []);

  const isCurrentMonth = year === today.getFullYear() && month === today.getMonth() + 1;

  function shiftMonth(delta: number) {
    let m = month + delta;
    let y = year;
    if (m === 0) (m = 12), (y -= 1);
    if (m === 13) (m = 1), (y += 1);
    setMonth(m);
    setYear(y);
  }

  const chartData = history.data
    ?.filter((h) => h.total_budget > 0 || h.total_spent > 0)
    .slice()
    .reverse()
    .map((h) => ({ label: h.label, Budget: h.total_budget, Actual: h.total_spent }));

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Budgets</h1>
          <div className="sub">Each month is a permanent record — history is never overwritten</div>
        </div>
        <button className="btn primary" onClick={() => setModal("create")}>
          + New budget
        </button>
      </div>

      <ErrorBanner error={progress.error} />

      {/* Month selector */}
      <div className="card" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12, padding: "12px 20px" }}>
        <button className="btn small" onClick={() => shiftMonth(-1)}>
          ←
        </button>
        <div style={{ fontWeight: 700, fontSize: 15, minWidth: 150, textAlign: "center" }}>
          {monthLabel(year, month)}
          {isCurrentMonth && <span className="pill" style={{ marginLeft: 8 }}>current</span>}
        </div>
        <button className="btn small" onClick={() => shiftMonth(1)}>
          →
        </button>
        {!isCurrentMonth && (
          <button
            className="btn ghost small"
            onClick={() => {
              setYear(today.getFullYear());
              setMonth(today.getMonth() + 1);
            }}
          >
            Back to this month
          </button>
        )}
      </div>

      {/* Budget cards for the selected month */}
      <div className="grid cols-2" style={{ marginBottom: 20 }}>
        {progress.data?.map((b) => (
          <div className="card" key={b.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>
                  {b.category?.icon} {b.category?.name ?? "Overall"}
                </div>
                <div style={{ color: "var(--text-faint)", fontSize: 12 }}>{monthLabel(b.year, b.month)}</div>
              </div>
              <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <span className="pill" style={{ color: STATUS_COLORS[b.status], borderColor: "transparent", background: "var(--bg-hover)" }}>
                  {b.status}
                </span>
                <button className="btn ghost small" onClick={() => setModal(b)}>
                  Edit
                </button>
                <button
                  className="btn ghost small danger"
                  onClick={async () => {
                    await api.deleteBudget(b.id);
                    progress.refetch();
                    history.refetch();
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
            <ProgressBar fraction={b.fraction_used} status={b.status === "completed" || b.status === "unused" ? "ok" : b.status} />
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 13 }}>
              <span style={{ color: "var(--text-dim)" }}>
                {formatMoney(b.spent)} of {formatMoney(b.budget_amount)} ({(b.fraction_used * 100).toFixed(0)}%)
              </span>
              <span style={{ fontWeight: 600, color: b.remaining < 0 ? "var(--red)" : "var(--green)" }}>
                {b.remaining < 0 ? `${formatMoney(-b.remaining)} over` : `${formatMoney(b.remaining)} left`}
              </span>
            </div>
          </div>
        ))}
      </div>
      {progress.data?.length === 0 && (
        <Empty message={`No budgets for ${monthLabel(year, month)} — create one with the button above`} />
      )}

      {/* History */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Budget vs actual (last 12 months)</h3>
        {chartData && chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" stroke="var(--text-faint)" fontSize={11} tickLine={false} />
              <YAxis stroke="var(--text-faint)" fontSize={11} tickLine={false} width={50} tickFormatter={(v: number) => formatMoneyShort(v)} />
              <Tooltip content={<MoneyTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Budget" fill="#6366f1" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Actual" fill="#38bdf8" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <Empty message="No budget history yet" />
        )}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <h3 style={{ padding: "20px 20px 0" }}>Monthly history</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Month</th>
              <th className="num">Budget</th>
              <th className="num">Spent</th>
              <th className="num">Difference</th>
              <th className="num">Used</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {history.data
              ?.filter((h) => h.items.length > 0)
              .map((h) => {
                const diff = h.total_budget - h.total_spent;
                const used = h.total_budget > 0 ? (h.total_spent / h.total_budget) * 100 : 0;
                return (
                  <tr
                    key={h.label}
                    style={{ cursor: "pointer" }}
                    title="Show this month"
                    onClick={() => {
                      setYear(h.year);
                      setMonth(h.month);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    <td style={{ fontWeight: 500 }}>{monthLabel(h.year, h.month)}</td>
                    <td className="num">{formatMoney(h.total_budget)}</td>
                    <td className="num">{formatMoney(h.total_spent)}</td>
                    <td className="num" style={{ color: diff < 0 ? "var(--red)" : "var(--green)", fontWeight: 600 }}>
                      {diff < 0 ? "−" : "+"}
                      {formatMoney(Math.abs(diff))}
                    </td>
                    <td className="num">{used.toFixed(0)}%</td>
                    <td>
                      {h.exceeded > 0 && <span className="pill deleted" style={{ marginRight: 4 }}>{h.exceeded} exceeded</span>}
                      {h.completed > 0 && <span className="pill need" style={{ marginRight: 4 }}>{h.completed} completed</span>}
                      {h.unused > 0 && <span className="pill">{h.unused} unused</span>}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
        {history.data?.filter((h) => h.items.length > 0).length === 0 && (
          <Empty message="No budget history yet" />
        )}
      </div>

      {modal && (
        <Modal
          title={modal === "create" ? `New budget — ${monthLabel(year, month)}` : "Edit budget"}
          onClose={() => setModal(null)}
        >
          <BudgetForm
            initial={modal === "create" ? undefined : modal}
            year={year}
            month={month}
            onSaved={() => {
              setModal(null);
              progress.refetch();
              history.refetch();
            }}
            onCancel={() => setModal(null)}
          />
        </Modal>
      )}
    </>
  );
}
