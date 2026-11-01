import { FormEvent, useState } from "react";
import { Empty, ErrorBanner, Modal } from "../components/ui";
import { api } from "../lib/api";
import { useAsync } from "../lib/hooks";
import type { Category, CategoryTree } from "../lib/types";

function CategoryForm({
  categories,
  initial,
  onSaved,
  onCancel,
}: {
  categories: Category[];
  initial?: Category;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [parentId, setParentId] = useState(initial?.parent_id?.toString() ?? "");
  const [icon, setIcon] = useState(initial?.icon ?? "");
  const [color, setColor] = useState(initial?.color ?? "#6366f1");
  const [budgetable, setBudgetable] = useState(initial?.budgetable ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (saving) return; // guard against rapid double-submits
    setSaving(true);
    try {
      const payload = {
        name,
        parent_id: parentId ? Number(parentId) : null,
        icon: icon || null,
        color: color || null,
        budgetable,
      };
      if (initial) await api.updateCategory(initial.id, payload);
      else await api.createCategory(payload);
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
          Name *
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field" style={{ flex: 2 }}>
          Parent
          <select value={parentId} onChange={(e) => setParentId(e.target.value)}>
            <option value="">None (top level)</option>
            {categories
              .filter((c) => !c.parent_id && c.id !== initial?.id)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
        </label>
        <label className="field" style={{ flex: 1 }}>
          Icon (emoji)
          <input value={icon} onChange={(e) => setIcon(e.target.value)} placeholder="🍜" />
        </label>
        <label className="field" style={{ flex: 1 }}>
          Color
          <input type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ height: 37, padding: 3 }} />
        </label>
      </div>
      <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <input type="checkbox" style={{ width: "auto" }} checked={budgetable} onChange={(e) => setBudgetable(e.target.checked)} />
        Budgetable
      </label>
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

export default function CategoriesPage() {
  const tree = useAsync(() => api.categoryTree(), []);
  const flat = useAsync(() => api.listCategories(), []);
  const [modal, setModal] = useState<"create" | Category | null>(null);

  const refetch = () => {
    tree.refetch();
    flat.refetch();
  };

  async function handleDelete(category: Category) {
    await api.deleteCategory(category.id);
    refetch();
  }

  function renderNode(node: CategoryTree) {
    return (
      <div key={node.id}>
        <div className="tree-node">
          <span style={{ fontSize: 16 }}>{node.icon ?? "•"}</span>
          <span className="dot" style={{ background: node.color ?? "var(--text-faint)" }} />
          <span style={{ flex: 1, fontWeight: node.parent_id ? 400 : 600 }}>{node.name}</span>
          {!node.budgetable && <span className="pill">not budgetable</span>}
          <button className="btn ghost small" onClick={() => setModal(node)}>
            Edit
          </button>
          <button className="btn ghost small danger" onClick={() => handleDelete(node)}>
            Delete
          </button>
        </div>
        {node.children.length > 0 && (
          <div className="tree-children">{node.children.map(renderNode)}</div>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Categories</h1>
          <div className="sub">
            Deleting a category in use deactivates it — history is preserved. Non-budgetable
            categories are excluded from budgets but still appear in analytics.
          </div>
        </div>
        <button className="btn primary" onClick={() => setModal("create")}>
          + New category
        </button>
      </div>

      <ErrorBanner error={tree.error} />

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {tree.data?.map(renderNode)}
        {tree.data?.length === 0 && <Empty message="No categories yet" />}
      </div>

      {modal && flat.data && (
        <Modal
          title={modal === "create" ? "New category" : `Edit ${modal.name}`}
          onClose={() => setModal(null)}
        >
          <CategoryForm
            categories={flat.data}
            initial={modal === "create" ? undefined : modal}
            onSaved={() => {
              setModal(null);
              refetch();
            }}
            onCancel={() => setModal(null)}
          />
        </Modal>
      )}
    </>
  );
}
