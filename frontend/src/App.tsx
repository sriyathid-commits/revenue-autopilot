import { NavLink, Route, Routes } from "react-router-dom";
import { Activity, CreditCard, Gauge, ShieldAlert, SlidersHorizontal } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Incidents from "./pages/Incidents";
import Investigation from "./pages/Investigation";
import EvaluationPage from "./pages/Evaluation";
import Transactions from "./pages/Transactions";
import LiveFeed from "./components/LiveFeed";
import { RealtimeProvider } from "./context/RealtimeContext";

export default function App() {
  return (
    <RealtimeProvider>
      <div className="app">
        <aside className="sidebar">
          <div className="brand">Revenue Autopilot</div>
          <div className="tagline">Detect. Decide. Recover. Verify.</div>
          <nav className="nav">
            <NavLink to="/" end>
              <Gauge size={16} /> Dashboard
            </NavLink>
            <NavLink to="/incidents">
              <Activity size={16} /> Incidents
            </NavLink>
            <NavLink to="/transactions">
              <CreditCard size={16} /> Transactions
            </NavLink>
            <NavLink to="/evaluation">
              <SlidersHorizontal size={16} /> Evaluation
            </NavLink>
          </nav>

          <div style={{ marginTop: 28 }}>
            <LiveFeed />
          </div>

          <p className="subtitle" style={{ marginTop: 20 }}>
            <ShieldAlert size={14} style={{ verticalAlign: "middle" }} />{" "}
            Synthetic test-mode only. Does not move real money.
          </p>
        </aside>

        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/incidents" element={<Incidents />} />
            <Route path="/incidents/:id" element={<Investigation />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/evaluation" element={<EvaluationPage />} />
          </Routes>
        </main>
      </div>
    </RealtimeProvider>
  );
}
