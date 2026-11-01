import { FormEvent, useState } from "react";
import { Empty, ErrorBanner, Modal } from "../components/ui";
import { api } from "../lib/api";
import { useAsync } from "../lib/hooks";
import type { Account, DailyContext } from "../lib/types";

const ACCOUNT_TYPES = ["cash", "bank", "credit_card", "e_wallet", "other"];

function AccountForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: Account;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [type, setType] = useState(initial?.account_type ?? "cash");
  const [bank, setBank] = useState(initial?.bank ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (saving) return; // guard against rapid double-submits
    setSaving(true);
    try {
      const payload = { name, account_type: type, bank: bank || null, currency: "VND" };
      if (initial) await api.updateAccount(initial.id, payload);
      else await api.createAccount(payload);
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
        <label className="field">
          Name *
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          Type
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {ACCOUNT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Bank
          <input value={bank} onChange={(e) => setBank(e.target.value)} />
        </label>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : initial ? "Save" : "Create"}
        </button>
      </div>
    </form>
  );
}

function DailyContextCard() {
  const contexts = useAsync(() => api.listDailyContexts(), []);
  const today = new Date().toISOString().slice(0, 10);
  const existing = contexts.data?.find((c: DailyContext) => c.date === today);

  const [sleep, setSleep] = useState("");
  const [stress, setStress] = useState("");
  const [happiness, setHappiness] = useState("");
  const [energy, setEnergy] = useState("");
  const [exercise, setExercise] = useState("");
  const [study, setStudy] = useState("");
  const [saved, setSaved] = useState(false);
  const [loaded, setLoaded] = useState(false);

  if (existing && !loaded) {
    setSleep(existing.sleep_hours?.toString() ?? "");
    setStress(existing.stress_level?.toString() ?? "");
    setHappiness(existing.happiness?.toString() ?? "");
    setEnergy(existing.energy?.toString() ?? "");
    setExercise(existing.exercise_minutes?.toString() ?? "");
    setStudy(existing.study_hours?.toString() ?? "");
    setLoaded(true);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    await api.upsertDailyContext({
      date: today,
      sleep_hours: sleep ? Number(sleep) : null,
      stress_level: stress ? Number(stress) : null,
      happiness: happiness ? Number(happiness) : null,
      energy: energy ? Number(energy) : null,
      exercise_minutes: exercise ? Number(exercise) : null,
      study_hours: study ? Number(study) : null,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    contexts.refetch();
  }

  const scale = (value: string, set: (v: string) => void, label: string) => (
    <label className="field">
      {label}
      <select value={value} onChange={(e) => set(e.target.value)}>
        <option value="">–</option>
        {[1, 2, 3, 4, 5].map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <h3>Today's context ({today})</h3>
      <p style={{ color: "var(--text-faint)", fontSize: 12, marginTop: -6 }}>
        Daily life signals that future ML models can correlate with spending. All optional.
      </p>
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="form-row" style={{ flexWrap: "wrap" }}>
          <label className="field">
            Sleep (hours)
            <input type="number" step="0.5" min="0" max="24" value={sleep} onChange={(e) => setSleep(e.target.value)} />
          </label>
          {scale(stress, setStress, "Stress")}
          {scale(happiness, setHappiness, "Happiness")}
          {scale(energy, setEnergy, "Energy")}
          <label className="field">
            Exercise (min)
            <input type="number" min="0" value={exercise} onChange={(e) => setExercise(e.target.value)} />
          </label>
          <label className="field">
            Study (hours)
            <input type="number" step="0.5" min="0" value={study} onChange={(e) => setStudy(e.target.value)} />
          </label>
        </div>
        <div>
          <button className="btn primary" type="submit">
            {saved ? "Saved ✓" : "Save today's context"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function SettingsPage() {
  const accounts = useAsync(() => api.listAccounts(), []);
  const tags = useAsync(() => api.listTags(), []);
  const [modal, setModal] = useState<"create" | Account | null>(null);
  const [newTag, setNewTag] = useState("");

  return (
    <>
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      <DailyContextCard />

      <div className="grid cols-2">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Accounts</h3>
            <button className="btn small" onClick={() => setModal("create")}>
              + Add
            </button>
          </div>
          <ErrorBanner error={accounts.error} />
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {accounts.data?.map((account) => (
              <div key={account.id} className="tree-node">
                <span style={{ flex: 1, fontWeight: 500 }}>{account.name}</span>
                <span className="pill">{account.account_type}</span>
                {account.bank && <span style={{ color: "var(--text-faint)", fontSize: 12 }}>{account.bank}</span>}
                <button className="btn ghost small" onClick={() => setModal(account)}>
                  Edit
                </button>
                <button
                  className="btn ghost small danger"
                  onClick={async () => {
                    await api.deleteAccount(account.id);
                    accounts.refetch();
                  }}
                >
                  Delete
                </button>
              </div>
            ))}
            {accounts.data?.length === 0 && <Empty message="No accounts" />}
          </div>
        </div>

        <div className="card">
          <h3>Tags</h3>
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            <input
              placeholder="New tag name…"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              style={{ maxWidth: 220 }}
            />
            <button
              className="btn"
              onClick={async () => {
                if (!newTag.trim()) return;
                await api.createTag({ name: newTag.trim() });
                setNewTag("");
                tags.refetch();
              }}
            >
              Add
            </button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {tags.data?.map((tag) => (
              <span key={tag.id} className="pill" style={{ fontSize: 12, padding: "5px 12px" }}>
                {tag.name}
                <button
                  style={{ background: "none", border: "none", color: "var(--text-faint)", cursor: "pointer", padding: "0 0 0 4px", fontSize: 13 }}
                  title="Delete tag"
                  onClick={async () => {
                    await api.deleteTag(tag.id);
                    tags.refetch();
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>About</h3>
        <p style={{ color: "var(--text-dim)", margin: 0, fontSize: 13, lineHeight: 1.7 }}>
          Personal Finance Analytics — local-first expense tracking designed for future ML.
          Data lives in <code>backend/finance.db</code> (SQLite). Derived values are always computed
          from raw events, soft-deleted rows are preserved, and behavioral context is stored per
          expense and per day, so a future <code>/ml</code> module can train on clean, labeled history.
        </p>
      </div>

      {modal && (
        <Modal title={modal === "create" ? "New account" : `Edit ${modal.name}`} onClose={() => setModal(null)}>
          <AccountForm
            initial={modal === "create" ? undefined : modal}
            onSaved={() => {
              setModal(null);
              accounts.refetch();
            }}
            onCancel={() => setModal(null)}
          />
        </Modal>
      )}
    </>
  );
}
