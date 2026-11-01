import { FormEvent, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Empty, ErrorBanner, Modal, MoneyTooltip, ProgressBar } from "../components/ui";
import { api } from "../lib/api";
import { formatDate, formatMoney, formatMoneyShort } from "../lib/format";
import { useAsync } from "../lib/hooks";
import type { Goal, GoalTransaction } from "../lib/types";

// --- Create / edit goal --------------------------------------------------
function GoalForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: Goal;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [target, setTarget] = useState(initial ? String(initial.target_amount) : "");
  const [initialAmount, setInitialAmount] = useState("0");
  const [deadline, setDeadline] = useState(initial?.deadline ?? "");
  const [priority, setPriority] = useState(String(initial?.priority ?? 3));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      const payload = {
        title,
        target_amount: Number(target),
        deadline: deadline || null,
        priority: Number(priority),
      };
      if (initial) await api.updateGoal(initial.id, payload);
      else await api.createGoal({ ...payload, initial_amount: Number(initialAmount) || 0 });
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {error && <div className="error-banner">{error}</div>}
      <label className="field">
        Title *
        <input required value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <div className="form-row">
        <label className="field">
          Target (₫) *
          <input type="number" min="1" required value={target} onChange={(e) => setTarget(e.target.value)} />
        </label>
        {!initial && (
          <label className="field">
            Starting balance (₫)
            <input type="number" min="0" value={initialAmount} onChange={(e) => setInitialAmount(e.target.value)} />
          </label>
        )}
        <label className="field">
          Deadline
          <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </label>
        <label className="field">
          Priority
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n} {n === 1 ? "(highest)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>
      {initial && (
        <p style={{ color: "var(--text-faint)", fontSize: 12, margin: 0 }}>
          The saved amount is managed through deposits and withdrawals — use the buttons on the goal card.
        </p>
      )}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : initial ? "Save" : "Create goal"}
        </button>
      </div>
    </form>
  );
}

// --- Deposit / withdraw dialog -------------------------------------------
function TransactionForm({
  goal,
  type,
  onSaved,
  onCancel,
}: {
  goal: Goal;
  type: "deposit" | "withdraw";
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      await api.createGoalTransaction(goal.id, {
        amount: Number(amount),
        transaction_type: type,
        date,
        note: note || null,
      });
      onSaved();
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {error && <div className="error-banner">{error}</div>}
      <div style={{ fontSize: 13, color: "var(--text-dim)" }}>
        Current saved: <strong style={{ color: "var(--text)" }}>{formatMoney(goal.current_amount)}</strong>
        {" · "}Target: {formatMoney(goal.target_amount)}
      </div>
      <div className="form-row">
        <label className="field">
          Amount (₫) *
          <input type="number" min="1" required autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <label className="field">
          Date
          <input type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
      </div>
      <label className="field">
        Note
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={type === "deposit" ? "e.g. Monthly salary, Freelance payment…" : "e.g. Used part of savings for emergency"}
        />
      </label>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : type === "deposit" ? "Save deposit" : "Save withdrawal"}
        </button>
      </div>
    </form>
  );
}

// --- History modal ---------------------------------------------------------
function GoalHistory({ goal, onChanged }: { goal: Goal; onChanged: () => void }) {
  const transactions = useAsync(() => api.listGoalTransactions(goal.id), [goal.id]);

  const monthly = useMemo(() => {
    const buckets = new Map<string, number>();
    for (const tx of transactions.data ?? []) {
      const key = tx.date.slice(0, 7);
      const signed = tx.transaction_type === "deposit" ? tx.amount : -tx.amount;
      buckets.set(key, (buckets.get(key) ?? 0) + signed);
    }
    return [...buckets.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, net]) => ({ month, net }));
  }, [transactions.data]);

  async function removeTx(tx: GoalTransaction) {
    await api.deleteGoalTransaction(goal.id, tx.id);
    transactions.refetch();
    onChanged();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div className="grid cols-3">
        <div>
          <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>Saved</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: "var(--green)" }}>{formatMoney(goal.current_amount)}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>Remaining</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{formatMoney(Math.max(goal.target_amount - goal.current_amount, 0))}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>Completion</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>
            {goal.target_amount > 0 ? ((goal.current_amount / goal.target_amount) * 100).toFixed(0) : 0}%
          </div>
        </div>
      </div>

      {monthly.length > 1 && (
        <div>
          <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
            Monthly contributions
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={monthly}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="month" stroke="var(--text-faint)" fontSize={11} tickLine={false} />
              <YAxis stroke="var(--text-faint)" fontSize={11} tickLine={false} width={45} tickFormatter={(v: number) => formatMoneyShort(v)} />
              <Tooltip content={<MoneyTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="net" name="Net saved" fill="#34d399" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
          Transaction history
        </div>
        <table className="table">
          <tbody>
            {transactions.data?.map((tx) => (
              <tr key={tx.id}>
                <td style={{ color: "var(--text-dim)", whiteSpace: "nowrap" }}>{formatDate(tx.date)}</td>
                <td>
                  <span className={`pill ${tx.transaction_type === "deposit" ? "need" : "deleted"}`}>
                    {tx.transaction_type}
                  </span>
                </td>
                <td style={{ color: "var(--text-dim)", maxWidth: 220 }}>{tx.note}</td>
                <td className="num" style={{ fontWeight: 600, color: tx.transaction_type === "deposit" ? "var(--green)" : "var(--red)" }}>
                  {tx.transaction_type === "deposit" ? "+" : "−"}
                  {formatMoney(tx.amount)}
                </td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn ghost small danger" title="Delete transaction" onClick={() => removeTx(tx)}>
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {transactions.data?.length === 0 && <Empty message="No transactions yet" />}
      </div>
    </div>
  );
}

// --- Page --------------------------------------------------------------------
type ModalState =
  | { kind: "create" }
  | { kind: "edit"; goal: Goal }
  | { kind: "deposit" | "withdraw"; goal: Goal }
  | { kind: "history"; goal: Goal }
  | null;

export default function GoalsPage() {
  const goals = useAsync(() => api.listGoals(), []);
  const [modal, setModal] = useState<ModalState>(null);

  const close = () => setModal(null);
  const closeAndRefresh = () => {
    setModal(null);
    goals.refetch();
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Goals</h1>
          <div className="sub">Saved amounts are computed from full deposit/withdrawal history</div>
        </div>
        <button className="btn primary" onClick={() => setModal({ kind: "create" })}>
          + New goal
        </button>
      </div>

      <ErrorBanner error={goals.error} />

      <div className="grid cols-2">
        {goals.data?.map((goal) => {
          const fraction = goal.target_amount > 0 ? goal.current_amount / goal.target_amount : 0;
          return (
            <div className="card" key={goal.id} style={goal.completed ? { opacity: 0.6 } : undefined}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>
                    {goal.completed && "✅ "}
                    {goal.title}
                  </div>
                  <div style={{ color: "var(--text-faint)", fontSize: 12 }}>
                    Priority {goal.priority}
                    {goal.deadline && ` · due ${formatDate(goal.deadline)}`}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                  <button
                    className="btn ghost small"
                    onClick={async () => {
                      await api.updateGoal(goal.id, { completed: !goal.completed });
                      goals.refetch();
                    }}
                  >
                    {goal.completed ? "Reopen" : "Done"}
                  </button>
                  <button className="btn ghost small" onClick={() => setModal({ kind: "edit", goal })}>
                    Edit
                  </button>
                  <button
                    className="btn ghost small danger"
                    onClick={async () => {
                      await api.deleteGoal(goal.id);
                      goals.refetch();
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <ProgressBar fraction={fraction} status={fraction >= 1 ? "ok" : undefined} />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 13 }}>
                <span style={{ color: "var(--text-dim)" }}>
                  {formatMoney(goal.current_amount)} of {formatMoney(goal.target_amount)}
                </span>
                <span style={{ fontWeight: 600 }}>{(fraction * 100).toFixed(0)}%</span>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                <button className="btn small primary" onClick={() => setModal({ kind: "deposit", goal })}>
                  ↑ Deposit
                </button>
                <button className="btn small" onClick={() => setModal({ kind: "withdraw", goal })}>
                  ↓ Withdraw
                </button>
                <button className="btn small ghost" onClick={() => setModal({ kind: "history", goal })}>
                  History
                </button>
              </div>
            </div>
          );
        })}
      </div>
      {goals.data?.length === 0 && <Empty message="No goals yet" />}

      {modal?.kind === "create" && (
        <Modal title="New goal" onClose={close}>
          <GoalForm onSaved={closeAndRefresh} onCancel={close} />
        </Modal>
      )}
      {modal?.kind === "edit" && (
        <Modal title="Edit goal" onClose={close}>
          <GoalForm initial={modal.goal} onSaved={closeAndRefresh} onCancel={close} />
        </Modal>
      )}
      {(modal?.kind === "deposit" || modal?.kind === "withdraw") && (
        <Modal
          title={`${modal.kind === "deposit" ? "Deposit to" : "Withdraw from"} “${modal.goal.title}”`}
          onClose={close}
        >
          <TransactionForm goal={modal.goal} type={modal.kind} onSaved={closeAndRefresh} onCancel={close} />
        </Modal>
      )}
      {modal?.kind === "history" && (
        <Modal title={`${modal.goal.title} — savings history`} onClose={close}>
          <GoalHistory
            goal={goals.data?.find((g) => g.id === modal.goal.id) ?? modal.goal}
            onChanged={() => goals.refetch()}
          />
        </Modal>
      )}
    </>
  );
}
