import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import AnalyticsPage from "./pages/AnalyticsPage";
import BudgetsPage from "./pages/BudgetsPage";
import CategoriesPage from "./pages/CategoriesPage";
import DashboardPage from "./pages/DashboardPage";
import ExpensesPage from "./pages/ExpensesPage";
import GoalsPage from "./pages/GoalsPage";
import IncomePage from "./pages/IncomePage";
import MerchantsPage from "./pages/MerchantsPage";
import SettingsPage from "./pages/SettingsPage";

const NAV = [
  { to: "/dashboard", icon: "📊", label: "Dashboard" },
  { to: "/expenses", icon: "💸", label: "Expenses" },
  { to: "/income", icon: "💰", label: "Income" },
  { to: "/categories", icon: "🗂️", label: "Categories" },
  { to: "/merchants", icon: "🏪", label: "Merchants" },
  { to: "/budgets", icon: "🎯", label: "Budgets" },
  { to: "/goals", icon: "🏁", label: "Goals" },
  { to: "/analytics", icon: "📈", label: "Analytics" },
  { to: "/settings", icon: "⚙️", label: "Settings" },
];

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          finance<span>.dash</span>
        </div>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            <span className="icon">{item.icon}</span>
            <span className="label">{item.label}</span>
          </NavLink>
        ))}
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/expenses" element={<ExpensesPage />} />
          <Route path="/income" element={<IncomePage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/merchants" element={<MerchantsPage />} />
          <Route path="/budgets" element={<BudgetsPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
