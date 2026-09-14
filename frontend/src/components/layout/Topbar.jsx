import { useEffect, useState } from "react";
import { Search, Bell, Zap, BrainCircuit, ShieldCheck, Moon, Sun } from "lucide-react";
import "./Topbar.css";

function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return now;
}

function StatusPill({ icon: Icon, label, value, ok }) {
  return (
    <div className={`status-pill ${ok ? "ok" : "down"}`}>
      <Icon size={14} strokeWidth={2.25} />
      <div className="status-pill-text">
        <span className="status-pill-label">{label}</span>
        <span className="status-pill-value">{value}</span>
      </div>
    </div>
  );
}

export default function Topbar({ connected, gridOk, aiRunning, chainVerified, alertCount = 0 }) {
  const now = useClock();
  const [dark, setDark] = useState(() => localStorage.getItem("grid-theme") !== "light");

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("grid-theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <header className="topbar">
      <div className="topbar-search">
        <Search size={16} strokeWidth={2} />
        <input placeholder="Search anything..." />
        <kbd>⌘K</kbd>
      </div>

      <div className="topbar-status-group">
        <StatusPill icon={Zap} label="Grid Status" value={gridOk ? "OPERATIONAL" : "OFFLINE"} ok={gridOk} />
        <StatusPill icon={BrainCircuit} label="AI Engine" value={aiRunning ? "RUNNING" : "STOPPED"} ok={aiRunning} />
        <StatusPill icon={ShieldCheck} label="Blockchain" value={chainVerified ? "VERIFIED" : "UNVERIFIED"} ok={chainVerified} />
      </div>

      <div className="topbar-right">
        <div className="topbar-datetime">
          <div className="topbar-date">{now.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}</div>
          <div className="topbar-time type-mono">{now.toLocaleTimeString("en-GB", { hour12: false })} · UTC+1</div>
        </div>

        <button className="topbar-icon-btn" aria-label="Notifications">
          <Bell size={18} strokeWidth={2} />
          {alertCount > 0 && <span className="topbar-badge-count">{alertCount > 99 ? "99+" : alertCount}</span>}
        </button>

        <button className="topbar-icon-btn" aria-label="Toggle color theme" title="Toggle color theme" onClick={() => setDark((d) => !d)}>
          {dark ? <Moon size={18} strokeWidth={2} /> : <Sun size={18} strokeWidth={2} />}
        </button>

        <div className="topbar-operator">
          <div className="topbar-avatar">MA</div>
          <div>
            <div className="topbar-operator-name">M. Aziz</div>
            <div className="topbar-operator-role">Grid Operator</div>
          </div>
          <span className={`sidebar-status-dot ${connected ? "ok" : "down"}`} />
        </div>
      </div>
    </header>
  );
}
