// Fast expense entry / edit form with merchant autocomplete, need/want
// toggle, tags, and an optional behavioral-context section that uses
// descriptive labels (numeric values are stored underneath for ML).
import { FormEvent, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import { toLocalInputValue } from "../lib/format";
import {
  ACTUAL_REGRET_OPTIONS,
  CHANNEL_OPTIONS,
  EMOTION_OPTIONS,
  EXPECTED_REGRET_OPTIONS,
  IMPULSE_OPTIONS,
  MOTIVATION_OPTIONS,
  NEED_LEVEL_OPTIONS,
  Option,
  PLANNING_OPTIONS,
  SATISFACTION_OPTIONS,
  URGENCY_OPTIONS,
  WHO_WITH_OPTIONS,
} from "../lib/labels";
import type { Account, Category, Expense, Merchant, Tag } from "../lib/types";

interface Props {
  accounts: Account[];
  categories: Category[];
  merchants: Merchant[];
  tags: Tag[];
  initial?: Expense;
  onSaved: () => void;
  onCancel?: () => void;
  onMerchantCreated: () => void;
}

function LabeledSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Option[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field" style={{ minWidth: 150 }}>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">–</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ExpenseForm({
  accounts,
  categories,
  merchants,
  tags,
  initial,
  onSaved,
  onCancel,
  onMerchantCreated,
}: Props) {
  const [amount, setAmount] = useState(initial ? String(initial.amount) : "");
  const [datetime, setDatetime] = useState(
    initial ? toLocalInputValue(new Date(initial.transaction_datetime)) : toLocalInputValue(new Date()),
  );
  const [categoryId, setCategoryId] = useState<string>(initial?.category_id?.toString() ?? "");
  const [accountId, setAccountId] = useState<string>(initial?.account_id?.toString() ?? "");
  const [paymentMethod, setPaymentMethod] = useState(initial?.payment_method ?? "");
  const [note, setNote] = useState(initial?.note ?? "");
  const [isNeed, setIsNeed] = useState<boolean | null>(initial?.is_need ?? null);
  const [isRecurring, setIsRecurring] = useState(initial?.is_recurring ?? false);
  const [tagIds, setTagIds] = useState<number[]>(initial?.tags.map((t) => t.id) ?? []);

  // Merchant autocomplete state
  const [merchantQuery, setMerchantQuery] = useState(initial?.merchant?.name ?? "");
  const [merchantId, setMerchantId] = useState<number | null>(initial?.merchant_id ?? null);
  const [merchantOpen, setMerchantOpen] = useState(false);
  const blurTimeout = useRef<number>();

  // Optional behavioral context
  const [showContext, setShowContext] = useState(Boolean(initial?.context));
  const [needLevel, setNeedLevel] = useState(initial?.context?.need_level?.toString() ?? "");
  const [impulse, setImpulse] = useState(initial?.context?.impulse_score?.toString() ?? "");
  const [planning, setPlanning] = useState(initial?.context?.planning_horizon ?? "");
  const [urgency, setUrgency] = useState(initial?.context?.urgency?.toString() ?? "");
  const [emotion, setEmotion] = useState(initial?.context?.emotion ?? "");
  const [motivation, setMotivation] = useState(initial?.context?.motivation ?? "");
  const [channel, setChannel] = useState(initial?.context?.shopping_channel ?? "");
  const [whoWith, setWhoWith] = useState(initial?.context?.who_with ?? "");
  const [expectedRegret, setExpectedRegret] = useState(
    initial?.context?.expected_regret?.toString() ?? "",
  );
  const [actualRegret, setActualRegret] = useState(initial?.context?.actual_regret?.toString() ?? "");
  const [satisfaction, setSatisfaction] = useState(initial?.context?.satisfaction?.toString() ?? "");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const merchantMatches = useMemo(() => {
    const q = merchantQuery.trim().toLowerCase();
    if (!q) return merchants.slice(0, 8);
    return merchants.filter((m) => m.name.toLowerCase().includes(q)).slice(0, 8);
  }, [merchants, merchantQuery]);

  const exactMerchant = merchants.find(
    (m) => m.name.toLowerCase() === merchantQuery.trim().toLowerCase(),
  );

  function pickMerchant(m: Merchant) {
    setMerchantId(m.id);
    setMerchantQuery(m.name);
    setMerchantOpen(false);
    // Auto-fill category from the merchant hint when empty.
    if (!categoryId && m.category_hint_id) setCategoryId(String(m.category_hint_id));
  }

  async function createMerchantInline() {
    const name = merchantQuery.trim();
    if (!name) return;
    const created = await api.createMerchant({ name });
    onMerchantCreated();
    pickMerchant(created);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (saving) return; // guard against double-submit
    setError(null);
    setSaving(true);
    try {
      let finalMerchantId = merchantId;
      // Typed a new merchant name without picking → create it on the fly.
      if (!finalMerchantId && merchantQuery.trim()) {
        if (exactMerchant) {
          finalMerchantId = exactMerchant.id;
        } else {
          const created = await api.createMerchant({ name: merchantQuery.trim() });
          onMerchantCreated();
          finalMerchantId = created.id;
        }
      }
      const hasContext =
        needLevel || impulse || planning || urgency || emotion || motivation || channel ||
        whoWith || expectedRegret || actualRegret || satisfaction;
      const context =
        showContext && hasContext
          ? {
              need_level: needLevel ? Number(needLevel) : null,
              impulse_score: impulse ? Number(impulse) : null,
              planning_horizon: planning || null,
              urgency: urgency ? Number(urgency) : null,
              emotion: emotion || null,
              motivation: motivation || null,
              shopping_channel: channel || null,
              who_with: whoWith || null,
              expected_regret: expectedRegret ? Number(expectedRegret) : null,
              actual_regret: actualRegret ? Number(actualRegret) : null,
              satisfaction: satisfaction ? Number(satisfaction) : null,
            }
          : undefined;
      const payload = {
        amount: Number(amount),
        transaction_datetime: datetime,
        category_id: categoryId ? Number(categoryId) : null,
        account_id: accountId ? Number(accountId) : null,
        merchant_id: finalMerchantId,
        payment_method: paymentMethod || null,
        note: note || null,
        is_need: isNeed,
        is_recurring: isRecurring,
        tag_ids: tagIds,
        ...(context !== undefined ? { context } : {}),
      };
      if (initial) {
        await api.updateExpense(initial.id, payload);
      } else {
        await api.createExpense(payload);
        setAmount("");
        setNote("");
        setMerchantQuery("");
        setMerchantId(null);
        setTagIds([]);
        setIsNeed(null);
      }
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {error && <div className="error-banner">{error}</div>}
      <div className="form-row">
        <label className="field" style={{ flex: 1.2 }}>
          Amount (₫) *
          <input
            type="number"
            min="1"
            step="any"
            required
            autoFocus={!initial}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="45000"
          />
        </label>
        <label className="field" style={{ flex: 1.2 }}>
          Date & time
          <input type="datetime-local" value={datetime} onChange={(e) => setDatetime(e.target.value)} required />
        </label>
        <div className="field" style={{ flex: 1 }}>
          Need / Want
          <div className="segmented" style={{ width: "100%" }}>
            <button type="button" className={isNeed === true ? "active" : ""} onClick={() => setIsNeed(isNeed === true ? null : true)} style={{ flex: 1 }}>
              Need
            </button>
            <button type="button" className={isNeed === false ? "active" : ""} onClick={() => setIsNeed(isNeed === false ? null : false)} style={{ flex: 1 }}>
              Want
            </button>
          </div>
        </div>
      </div>

      <div className="form-row">
        <div className="field autocomplete" style={{ position: "relative" }}>
          Merchant
          <input
            value={merchantQuery}
            placeholder="Start typing…"
            onChange={(e) => {
              setMerchantQuery(e.target.value);
              setMerchantId(null);
              setMerchantOpen(true);
            }}
            onFocus={() => setMerchantOpen(true)}
            onBlur={() => {
              blurTimeout.current = window.setTimeout(() => setMerchantOpen(false), 150);
            }}
          />
          {merchantOpen && (merchantMatches.length > 0 || merchantQuery.trim()) && (
            <div className="autocomplete-list" onMouseDown={() => window.clearTimeout(blurTimeout.current)}>
              {merchantMatches.map((m) => (
                <button type="button" key={m.id} onClick={() => pickMerchant(m)}>
                  {m.name}
                </button>
              ))}
              {merchantQuery.trim() && !exactMerchant && (
                <button type="button" className="create" onClick={createMerchantInline}>
                  + Create “{merchantQuery.trim()}”
                </button>
              )}
            </div>
          )}
        </div>
        <label className="field">
          Category
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">–</option>
            {categories
              .filter((c) => !c.parent_id)
              .map((root) => (
                <optgroup key={root.id} label={`${root.icon ?? ""} ${root.name}`}>
                  <option value={root.id}>{root.name}</option>
                  {categories
                    .filter((c) => c.parent_id === root.id)
                    .map((child) => (
                      <option key={child.id} value={child.id}>
                        {"  "}{child.name}
                      </option>
                    ))}
                </optgroup>
              ))}
          </select>
        </label>
        <label className="field">
          Account
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">–</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Payment
          <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
            <option value="">–</option>
            <option value="cash">Cash</option>
            <option value="card">Card</option>
            <option value="e_wallet">E-wallet</option>
            <option value="bank_transfer">Bank transfer</option>
            <option value="other">Other</option>
          </select>
        </label>
      </div>

      <div className="form-row">
        <label className="field" style={{ flex: 2 }}>
          Note
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional note" />
        </label>
        <div className="field" style={{ flex: 2 }}>
          Tags
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, paddingTop: 4 }}>
            {tags.map((tag) => {
              const active = tagIds.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  className="pill"
                  style={
                    active
                      ? { background: "var(--accent-soft)", color: "var(--accent-hover)", borderColor: "var(--accent)", cursor: "pointer" }
                      : { cursor: "pointer" }
                  }
                  onClick={() =>
                    setTagIds(active ? tagIds.filter((id) => id !== tag.id) : [...tagIds, tag.id])
                  }
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        </div>
        <label className="field" style={{ flex: 0.8, flexDirection: "row", alignItems: "center", gap: 8, paddingTop: 20 }}>
          <input
            type="checkbox"
            style={{ width: "auto" }}
            checked={isRecurring}
            onChange={(e) => setIsRecurring(e.target.checked)}
          />
          Recurring
        </label>
      </div>

      <div>
        <button type="button" className="btn ghost small" onClick={() => setShowContext(!showContext)}>
          {showContext ? "▾" : "▸"} Behavioral context (for future ML)
        </button>
        {showContext && (
          <>
            <div className="form-row" style={{ marginTop: 10, flexWrap: "wrap" }}>
              <LabeledSelect label="Need level" options={NEED_LEVEL_OPTIONS} value={needLevel} onChange={setNeedLevel} />
              <LabeledSelect label="Impulse level" options={IMPULSE_OPTIONS} value={impulse} onChange={setImpulse} />
              <LabeledSelect label="Purchase planning" options={PLANNING_OPTIONS} value={planning} onChange={setPlanning} />
              <LabeledSelect label="Urgency" options={URGENCY_OPTIONS} value={urgency} onChange={setUrgency} />
              <LabeledSelect label="Expected regret" options={EXPECTED_REGRET_OPTIONS} value={expectedRegret} onChange={setExpectedRegret} />
            </div>
            <div className="form-row" style={{ marginTop: 10, flexWrap: "wrap" }}>
              <LabeledSelect label="Emotion" options={EMOTION_OPTIONS} value={emotion} onChange={setEmotion} />
              <LabeledSelect label="Motivation" options={MOTIVATION_OPTIONS} value={motivation} onChange={setMotivation} />
              <LabeledSelect label="Shopping channel" options={CHANNEL_OPTIONS} value={channel} onChange={setChannel} />
              <LabeledSelect label="Who were you with?" options={WHO_WITH_OPTIONS} value={whoWith} onChange={setWhoWith} />
            </div>
            {initial && (
              <div className="form-row" style={{ marginTop: 10, flexWrap: "wrap" }}>
                <LabeledSelect label="Actual regret (later)" options={ACTUAL_REGRET_OPTIONS} value={actualRegret} onChange={setActualRegret} />
                <LabeledSelect label="Satisfaction (later)" options={SATISFACTION_OPTIONS} value={satisfaction} onChange={setSatisfaction} />
              </div>
            )}
          </>
        )}
      </div>

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button type="submit" className="btn primary" disabled={saving}>
          {saving ? "Saving…" : initial ? "Save changes" : "Add expense"}
        </button>
      </div>
    </form>
  );
}
