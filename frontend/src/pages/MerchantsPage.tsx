import { FormEvent, useState } from "react";
import { Empty, ErrorBanner, Modal } from "../components/ui";
import { api } from "../lib/api";
import { useAsync } from "../lib/hooks";
import type { Merchant } from "../lib/types";

export default function MerchantsPage() {
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Merchant | null>(null);
  const [creating, setCreating] = useState(false);
  const [mergeMode, setMergeMode] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [mergeTarget, setMergeTarget] = useState("");
  const [error, setError] = useState<string | null>(null);

  const merchants = useAsync(() => api.listMerchants(search || undefined), [search]);
  const categories = useAsync(() => api.listCategories(), []);

  async function doMerge() {
    if (!mergeTarget || selected.length === 0) return;
    try {
      await api.mergeMerchants(
        selected.filter((id) => id !== Number(mergeTarget)),
        Number(mergeTarget),
      );
      setMergeMode(false);
      setSelected([]);
      setMergeTarget("");
      merchants.refetch();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function MerchantForm({ initial }: { initial?: Merchant }) {
    const [name, setName] = useState(initial?.name ?? "");
    const [hint, setHint] = useState(initial?.category_hint_id?.toString() ?? "");
    const [notes, setNotes] = useState(initial?.notes ?? "");
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    async function submit(e: FormEvent) {
      e.preventDefault();
      if (saving) return; // guard against rapid double-submits
      setSaving(true);
      try {
        const payload = { name, category_hint_id: hint ? Number(hint) : null, notes: notes || null };
        if (initial) await api.updateMerchant(initial.id, payload);
        else await api.createMerchant(payload);
        setEditing(null);
        setCreating(false);
        merchants.refetch();
      } catch (err) {
        setFormError((err as Error).message);
        setSaving(false);
      }
    }

    return (
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {formError && <div className="error-banner">{formError}</div>}
        <label className="field">
          Name *
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          Default category
          <select value={hint} onChange={(e) => setHint(e.target.value)}>
            <option value="">–</option>
            {categories.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.parent_id ? "· " : ""}{c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Notes
          <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" className="btn" onClick={() => { setEditing(null); setCreating(false); }}>
            Cancel
          </button>
          <button className="btn primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : initial ? "Save" : "Create"}
          </button>
        </div>
      </form>
    );
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Merchants</h1>
          {merchants.data && <div className="sub">{merchants.data.length} merchants</div>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={`btn${mergeMode ? " primary" : ""}`} onClick={() => { setMergeMode(!mergeMode); setSelected([]); }}>
            {mergeMode ? "Cancel merge" : "Merge duplicates"}
          </button>
          <button className="btn primary" onClick={() => setCreating(true)}>
            + New merchant
          </button>
        </div>
      </div>

      <ErrorBanner error={merchants.error ?? error} />

      <div className="card" style={{ marginBottom: 16, padding: "14px 20px" }}>
        <input style={{ maxWidth: 300 }} placeholder="Search merchants…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {mergeMode && selected.length > 0 && (
        <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "center", padding: "14px 20px" }}>
          <span style={{ fontSize: 13, color: "var(--text-dim)" }}>
            Merge {selected.length} selected into:
          </span>
          <select style={{ maxWidth: 260 }} value={mergeTarget} onChange={(e) => setMergeTarget(e.target.value)}>
            <option value="">Choose target…</option>
            {merchants.data
              ?.filter((m) => selected.includes(m.id))
              .map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
          </select>
          <button className="btn primary" disabled={!mergeTarget || selected.length < 2} onClick={doMerge}>
            Merge
          </button>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table className="table">
          <thead>
            <tr>
              {mergeMode && <th style={{ width: 36 }}></th>}
              <th>Name</th>
              <th>Default category</th>
              <th>Notes</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {merchants.data?.map((merchant) => (
              <tr key={merchant.id}>
                {mergeMode && (
                  <td>
                    <input
                      type="checkbox"
                      style={{ width: "auto" }}
                      checked={selected.includes(merchant.id)}
                      onChange={(e) =>
                        setSelected(
                          e.target.checked
                            ? [...selected, merchant.id]
                            : selected.filter((id) => id !== merchant.id),
                        )
                      }
                    />
                  </td>
                )}
                <td style={{ fontWeight: 500 }}>{merchant.name}</td>
                <td style={{ color: "var(--text-dim)" }}>
                  {categories.data?.find((c) => c.id === merchant.category_hint_id)?.name ?? "–"}
                </td>
                <td style={{ color: "var(--text-faint)", maxWidth: 300 }}>{merchant.notes}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button className="btn ghost small" onClick={() => setEditing(merchant)}>
                    Edit
                  </button>
                  <button
                    className="btn ghost small danger"
                    onClick={async () => {
                      await api.deleteMerchant(merchant.id);
                      merchants.refetch();
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {merchants.data?.length === 0 && <Empty message="No merchants found" />}
      </div>

      {(creating || editing) && (
        <Modal
          title={editing ? `Edit ${editing.name}` : "New merchant"}
          onClose={() => {
            setCreating(false);
            setEditing(null);
          }}
        >
          <MerchantForm initial={editing ?? undefined} />
        </Modal>
      )}
    </>
  );
}
