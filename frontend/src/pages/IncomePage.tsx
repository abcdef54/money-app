import { FormEvent, useState } from "react";
import { Empty, ErrorBanner, Modal } from "../components/ui";
import { api } from "../lib/api";
import { formatDateTime, formatMoney, toLocalInputValue } from "../lib/format";
import { useAsync } from "../lib/hooks";
import type { Income } from "../lib/types";

const SOURCES = ["salary", "scholarship", "gift", "refund", "investment", "interest", "other"];

function IncomeForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: Income;
  onSaved: () => void;
  onCancel?: () => void;
}) {
  const accounts = useAsync(() => api.listAccounts(), []);
  const [amount, setAmount] = useState(initial ? String(initial.amount) : "");
  const [source, setSource] = useState(initial?.source ?? "salary");
  const [accountId, setAccountId] = useState(initial?.account_id?.toString() ?? "");
  const [datetime, setDatetime] = useState(
    initial ? toLocalInputValue(new Date(initial.transaction_datetime)) : toLocalInputValue(new Date()),
  );
  const [note, setNote] = useState(initial?.note ?? "");
  const [recurring, setRecurring] = useState(initial?.is_recurring ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (saving) return; // guard against rapid double-submits
    setSaving(true);
    try {
      const payload = {
        amount: Number(amount),
        source,
        account_id: accountId ? Number(accountId) : null,
        transaction_datetime: datetime,
        note: note || null,
        is_recurring: recurring,
      };
      if (initial) await api.updateIncome(initial.id, payload);
      else await api.createIncome(payload);
      if (!initial) {
        setAmount("");
        setNote("");
      }
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
      <div className="form-row">
        <label className="field">
          Amount (₫) *
          <input type="number" min="1" required value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <label className="field">
          Source
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Account
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">–</option>
            {accounts.data?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Date & time
          <input type="datetime-local" required value={datetime} onChange={(e) => setDatetime(e.target.value)} />
        </label>
      </div>
      <div className="form-row">
        <label className="field" style={{ flex: 3 }}>
          Note
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingTop: 20 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={recurring} onChange={(e) => setRecurring(e.target.checked)} />
          Recurring
        </label>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : initial ? "Save changes" : "Add income"}
        </button>
      </div>
    </form>
  );
}

export default function IncomePage() {
  const [editing, setEditing] = useState<Income | null>(null);
  const incomes = useAsync(() => api.listIncomes({ page_size: 100 }), []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Income</h1>
          {incomes.data && <div className="sub">{incomes.data.total} entries</div>}
        </div>
      </div>

      <ErrorBanner error={incomes.error} />

      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Add income</h3>
        <IncomeForm onSaved={() => incomes.refetch()} />
      </div>

      <div className="card" style={{ padding: 0, overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>When</th>
              <th>Source</th>
              <th>Account</th>
              <th>Note</th>
              <th className="num">Amount</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {incomes.data?.items.map((income) => (
              <tr key={income.id}>
                <td style={{ color: "var(--text-dim)", whiteSpace: "nowrap" }}>
                  {formatDateTime(income.transaction_datetime)}
                </td>
                <td>
                  <span className="pill">{income.source}</span>
                  {income.is_recurring && <span className="pill" style={{ marginLeft: 4 }}>recurring</span>}
                </td>
                <td>{income.account?.name ?? "–"}</td>
                <td style={{ color: "var(--text-dim)" }}>{income.note}</td>
                <td className="num" style={{ fontWeight: 600, color: "var(--green)" }}>
                  +{formatMoney(income.amount)}
                </td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button className="btn ghost small" onClick={() => setEditing(income)}>
                    Edit
                  </button>
                  <button
                    className="btn ghost small danger"
                    onClick={async () => {
                      await api.deleteIncome(income.id);
                      incomes.refetch();
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {incomes.data?.items.length === 0 && <Empty message="No income recorded yet" />}
      </div>

      {editing && (
        <Modal title={`Edit income #${editing.id}`} onClose={() => setEditing(null)}>
          <IncomeForm
            initial={editing}
            onSaved={() => {
              setEditing(null);
              incomes.refetch();
            }}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}
    </>
  );
}
