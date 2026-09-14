import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Network, Gauge, BrainCircuit, ShieldAlert, ReceiptText,
  Lightbulb, Blocks, LineChart, BellRing, Activity, FileText, Users, Settings,
  Zap,
} from "lucide-react";
import "./Sidebar.css";

const NAV_SECTIONS = [
  {
    label: "Operations",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
      { to: "/smart-grid", label: "Smart Grid", icon: Network },
      { to: "/smart-meters", label: "Smart Meters", icon: Gauge },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/ai-detection", label: "AI Detection", icon: BrainCircuit },
      { to: "/explainable-ai", label: "Explainable AI", icon: Lightbulb },
      { to: "/cybersecurity", label: "Cybersecurity", icon: ShieldAlert },
      { to: "/electricity-theft", label: "Electricity Theft", icon: ReceiptText },
    ],
  },
  {
    label: "Trust & Records",
    items: [
      { to: "/blockchain", label: "Blockchain", icon: Blocks },
      { to: "/analytics", label: "Analytics", icon: LineChart },
      { to: "/alerts", label: "Alerts", icon: BellRing },
    ],
  },
  {
    label: "Platform",
    items: [
      { to: "/performance", label: "Performance", icon: Activity },
      { to: "/reports", label: "Reports", icon: FileText },
      { to: "/users", label: "Users", icon: Users },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export default function Sidebar({ systemStatus }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark"><Zap size={20} strokeWidth={2.25} /></div>
        <div>
          <div className="sidebar-brand-name">GridSentinel</div>
          <div className="sidebar-brand-sub">Cybersecurity Platform</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div className="sidebar-section" key={section.label}>
            <div className="sidebar-section-label">{section.label}</div>
            {section.items.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
              >
                <span className="sidebar-link-indicator" />
                <Icon size={18} strokeWidth={2} />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-row">
          <div className="sidebar-avatar">MA</div>
          <div>
            <div className="sidebar-footer-name">M. Aziz</div>
            <div className="sidebar-footer-role">Grid Operator</div>
          </div>
        </div>
        <div className="sidebar-footer-meta">
          <span>v1.0.0-thesis</span>
          <span className={`sidebar-status-dot ${systemStatus || "unknown"}`} />
        </div>
      </div>
    </aside>
  );
}
