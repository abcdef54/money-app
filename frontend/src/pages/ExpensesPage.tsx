import { useState } from "react";
import ExpenseForm from "../components/ExpenseForm";
import { Empty, ErrorBanner, Modal } from "../components/ui";
import { api } from "../lib/api";
import { formatDateTime, formatMoney } from "../lib/format";
import { useAsync } from "../lib/hooks";
import type { Expense } from "../lib/types";

export default function ExpensesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [showEntry, setShowEntry] = useState(true);

  const accounts = useAsync(() => api.listAccounts(), []);
  const categories = useAsync(() => api.listCategories(), []);
  const merchants = useAsync(() => api.listMerchants(), []);
  const tags = useAsync(() => api.listTags(), []);

  const expenses = useAsync(
    () =>
      api.listExpenses({
        page,
        page_size: 25,
        search: search || undefined,
        category_id: categoryId || undefined,
        only_deleted: showDeleted || undefined,
      }),
    [page, search, categoryId, showDeleted],
  );

  const refetchAll = () => expenses.refetch();
  const totalPages = expenses.data ? Math.max(Math.ceil(expenses.data.total / 25), 1) : 1;
  const formReady = accounts.data && categories.data && merchants.data && tags.data;

  async function handleDelete(expense: Expense) {
    await api.deleteExpense(expense.id);
    refetchAll();
  }

  async function handleRestore(expense: Expense) {
    await api.restoreExpense(expense.id);
    refetchAll();
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Expenses</h1>
          {expenses.data && <div className="sub">{expenses.data.total} transactions</div>}
        </div>
        <button className="btn" onClick={() => setShowEntry(!showEntry)}>
          {showEntry ? "Hide quick entry" : "Quick entry"}
        </button>
      </div>

      <ErrorBanner error={expenses.error} />

      {showEntry && formReady && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3>Add expense</h3>
          <ExpenseForm
            accounts={accounts.data!}
            categories={categories.data!}
            merchants={merchants.data!}
            tags={tags.data!}
            onSaved={refetchAll}
            onMerchantCreated={() => merchants.refetch()}
          />
        </div>
      )}

      <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", padding: "14px 20px" }}>
        <input
          style={{ maxWidth: 240 }}
          placeholder="Search notes…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          style={{ maxWidth: 220 }}
          value={categoryId}
          onChange={(e) => {
            setCategoryId(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All categories</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.parent_id ? "· " : ""}{c.name}
            </option>
          ))}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-dim)" }}>
          <input
            type="checkbox"
            style={{ width: "auto" }}
            checked={showDeleted}
            onChange={(e) => {
              setShowDeleted(e.target.checked);
              setPage(1);
            }}
          />
          Deleted only
        </label>
      </div>

      <div className="card" style={{ padding: 0, overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>When</th>
              <th>Merchant</th>
              <th>Category</th>
              <th>Note / tags</th>
              <th></th>
              <th className="num">Amount</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {expenses.data?.items.map((expense) => (
              <tr key={expense.id}>
                <td style={{ whiteSpace: "nowrap", color: "var(--text-dim)" }}>
                  {formatDateTime(expense.transaction_datetime)}
                </td>
                <td>{expense.merchant?.name ?? "–"}</td>
                <td>
                  {expense.category ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <span className="dot" style={{ background: expense.category.color ?? "var(--text-faint)" }} />
                      {expense.category.name}
                    </span>
                  ) : (
                    "–"
                  )}
                </td>
                <td style={{ maxWidth: 260 }}>
                  <span style={{ color: "var(--text-dim)" }}>{expense.note}</span>{" "}
                  {expense.tags.map((tag) => (
                    <span key={tag.id} className="pill" style={{ marginRight: 4 }}>
                      {tag.name}
                    </span>
                  ))}
                </td>
                <td>
                  {expense.is_deleted ? (
                    <span className="pill deleted">deleted</span>
                  ) : expense.is_need === true ? (
                    <span className="pill need">need</span>
                  ) : expense.is_need === false ? (
                    <span className="pill want">want</span>
                  ) : null}
                </td>
                <td className="num" style={{ fontWeight: 600 }}>
                  {formatMoney(expense.amount)}
                </td>
                <td style={{ whiteSpace: "nowrap", textAlign: "right" }}>
                  {expense.is_deleted ? (
                    <button className="btn small" onClick={() => handleRestore(expense)}>
                      Restore
                    </button>
                  ) : (
                    <>
                      <button className="btn ghost small" onClick={() => setEditing(expense)}>
                        Edit
                      </button>
                      <button className="btn ghost small danger" onClick={() => handleDelete(expense)}>
                        Delete
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {expenses.data?.items.length === 0 && <Empty message="No expenses found" />}
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16, alignItems: "center" }}>
          <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            ← Prev
          </button>
          <span style={{ color: "var(--text-dim)", fontSize: 13 }}>
            Page {page} / {totalPages}
          </span>
          <button className="btn small" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
            Next →
          </button>
        </div>
      )}

      {editing && formReady && (
        <Modal title={`Edit expense #${editing.id}`} onClose={() => setEditing(null)}>
          <ExpenseForm
            accounts={accounts.data!}
            categories={categories.data!}
            merchants={merchants.data!}
            tags={tags.data!}
            initial={editing}
            onSaved={() => {
              setEditing(null);
              refetchAll();
            }}
            onCancel={() => setEditing(null)}
            onMerchantCreated={() => merchants.refetch()}
          />
        </Modal>
      )}
    </>
  );
}
