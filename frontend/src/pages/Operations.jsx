import {
  Activity, BellRing, Blocks, CheckCircle2, Cpu, FileText, Gauge,
  ReceiptText, ShieldAlert, Users, WalletCards, Zap,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { KPICard } from "../components/ui/KPICard";
import { Badge, StatusDot } from "../components/ui/Badge";
import { DataTable } from "../components/ui/DataTable";
import { ProgressBar } from "../components/ui/ProgressBar";
import { usePolling } from "../hooks/usePolling";
import {
  getAlerts, getBlockchainStatus, getGridAll, getHealthDetailed,
  getModelStatus, getSmartMetersStatus,
} from "../api/client";

const PAGE = {
  meters: { title: "Smart Meters", subtitle: "Connected meter fleet and latest electrical measurements", icon: Gauge },
  security: { title: "Cybersecurity Center", subtitle: "Continuous monitoring of the intelligent-grid attack surface", icon: ShieldAlert },
  theft: { title: "Electricity Theft Detection", subtitle: "Consumption integrity signals and suspected meter tampering", icon: ReceiptText },
  blockchain: { title: "Blockchain Ledger", subtitle: "Proof-of-Authority record integrity and validation status", icon: Blocks },
  analytics: { title: "Grid Analytics", subtitle: "Operational insights calculated from the active grid stream", icon: Activity },
  alerts: { title: "Alert Center", subtitle: "Prioritized events produced by the live detection pipeline", icon: BellRing },
  performance: { title: "Performance Monitoring", subtitle: "Live capacity, compute, and inference-health indicators", icon: Cpu },
  reports: { title: "Reports", subtitle: "Exportable operational summaries and model governance records", icon: FileText },
  users: { title: "User Management", subtitle: "Operator access and platform roles", icon: Users },
  settings: { title: "System Settings", subtitle: "Runtime configuration and service readiness", icon: WalletCards },
};

const USERS = [
  ["M. Aziz", "Grid Operator", "Operations", "Active"],
  ["N. Ben Salah", "Security Analyst", "Cybersecurity", "Active"],
  ["S. Karim", "Data Engineer", "AI Platform", "Active"],
  ["F. Mansour", "Viewer", "Management", "Limited"],
];

export default function Operations({ page }) {
  const config = PAGE[page];
  const grid = usePolling(getGridAll, 3000);
  const alerts = usePolling(getAlerts, 4000);
  const chain = usePolling(getBlockchainStatus, 8000);
  const health = usePolling(getHealthDetailed, 6000);
  const model = usePolling(getModelStatus, 8000);
  const meters = usePolling(getSmartMetersStatus, 10000);
  const buses = grid.data?.buses || [];
  const activeAttacks = buses.filter((bus) => bus.attack_type && bus.attack_type !== "normal");
  const alertRows = (alerts.data?.alerts || []).map((alert, index) => ({
    ...alert,
    id: alert.id ?? `${alert.bus_id}-${alert.timestamp}-${index}`,
    meter: alert.meter_id ?? `SM_${String(alert.bus_id ?? index + 1).padStart(4, "0")}`,
  }));
  const Icon = config.icon;

  if (page === "meters") return <MetersPage {...{ config, Icon, buses, meters }} />;
  if (page === "alerts") return <AlertsPage {...{ config, Icon, alertRows }} />;
  if (page === "users") return <UsersPage {...{ config, Icon }} />;
  if (page === "settings") return <SettingsPage {...{ config, Icon, health, model, chain }} />;

  const metrics = page === "blockchain"
    ? [["Ledger blocks", chain.data?.blocks ?? "—", Blocks, "info"], ["Ledger status", chain.data?.valid ? "Valid" : "Checking", CheckCircle2, chain.data?.valid ? "success" : "warning"], ["Active validators", chain.data?.validators?.length ?? 4, Users, "primary"], ["Protected events", alertRows.length, ShieldAlert, "info"]]
    : page === "performance"
      ? [["CPU usage", health.data?.resources?.cpu_percent?.toFixed(0) ?? "—", Cpu, "primary"], ["Memory usage", health.data?.resources?.memory_percent?.toFixed(0) ?? "—", Activity, "info"], ["Model latency", model.data?.detector?.avg_latency_ms?.toFixed(1) ?? "—", Zap, "success"], ["Grid buses", buses.length, Gauge, "primary"]]
      : page === "security"
        ? [["Active incidents", activeAttacks.length, ShieldAlert, activeAttacks.length ? "critical" : "success"], ["Open alerts", alerts.data?.count ?? "—", BellRing, "warning"], ["Detection engine", model.data?.detector?.loaded ? "Online" : "Offline", Cpu, model.data?.detector?.loaded ? "success" : "critical"], ["Protected assets", buses.length, Gauge, "info"]]
        : page === "theft"
          ? [["Flagged meters", activeAttacks.length, ReceiptText, activeAttacks.length ? "warning" : "success"], ["Fleet coverage", buses.length, Gauge, "primary"], ["Model confidence", model.data?.registry?.champion_metrics?.roc_auc ? `${(model.data.registry.champion_metrics.roc_auc * 100).toFixed(1)}%` : "—", ShieldAlert, "success"], ["Reviewed events", alertRows.length, CheckCircle2, "info"]]
          : page === "reports"
            ? [["Available reports", 4, FileText, "primary"], ["Events logged", alertRows.length, BellRing, "warning"], ["Ledger blocks", chain.data?.blocks ?? "—", Blocks, "info"], ["Grid data points", buses.length, Activity, "success"]]
            : [["Monitored buses", buses.length, Gauge, "primary"], ["Current load", `${buses.reduce((sum, bus) => sum + (bus.consumption || 0), 0).toFixed(1)} kW`, Zap, "info"], ["Open alerts", alerts.data?.count ?? "—", BellRing, "warning"], ["Grid health", grid.error ? "Offline" : "Nominal", CheckCircle2, grid.error ? "critical" : "success"]];

  return (
    <div>
      <PageHeader config={config} Icon={Icon} tone={grid.error ? "critical" : "success"} status={grid.error ? "Service unavailable" : "Live monitoring"} />
      <div className="grid grid-cols-4" style={{ marginBottom: "var(--space-4)" }}>
        {metrics.map(([label, value, MetricIcon, tone]) => <KPICard key={label} label={label} value={value} icon={MetricIcon} tone={tone} />)}
      </div>
      <div className="grid operations-grid">
        <Card title={page === "blockchain" ? "Ledger Integrity" : page === "reports" ? "Report Register" : "Live Operations"} subtitle="Latest verified platform data">
          <DataTable rows={buses.slice(0, 8)} keyField="bus_id" emptyMessage="Waiting for grid data" columns={[
            { key: "bus_id", header: "Asset", className: "mono emphasis", render: (row) => `SM_${String(row.bus_id).padStart(4, "0")}` },
            { key: "consumer_type", header: "Segment", render: (row) => <Badge tone="neutral">{row.consumer_type || "grid"}</Badge> },
            { key: "consumption", header: "Load", className: "mono", render: (row) => `${row.consumption?.toFixed(2) ?? "—"} kW` },
            { key: "attack_type", header: "Status", render: (row) => <Badge tone={row.attack_type === "normal" || !row.attack_type ? "success" : "critical"}>{row.attack_type || "normal"}</Badge> },
          ]} />
        </Card>
        <Card title="Service Health" subtitle="Current platform readiness">
          <HealthLine label="Grid telemetry" value={!grid.error} />
          <HealthLine label="AI inference engine" value={!!model.data?.detector?.loaded} />
          <HealthLine label="Blockchain validation" value={!!chain.data?.valid} />
          <HealthLine label="System resources" value={!health.error} />
          <div className="operations-capacity"><span className="type-small text-muted">Platform capacity</span><strong>{health.data?.resources?.cpu_percent ? `${Math.max(0, 100 - health.data.resources.cpu_percent).toFixed(0)}%` : "—"}</strong></div>
          <ProgressBar value={health.data?.resources?.cpu_percent ? 100 - health.data.resources.cpu_percent : 0} tone="success" />
        </Card>
      </div>
    </div>
  );
}

function PageHeader({ config, Icon, tone, status }) {
  return <div className="page-header"><div className="page-header-title"><div className="page-heading-icon"><Icon size={20} /></div><h1 className="type-h2">{config.title}</h1><Badge tone={tone}><StatusDot tone={tone} />{status}</Badge></div><p className="text-secondary type-small" style={{ marginTop: 6 }}>{config.subtitle}</p></div>;
}

function MetersPage({ config, Icon, buses, meters }) {
  return <div><PageHeader config={config} Icon={Icon} tone="success" status="Fleet online" /><div className="grid grid-cols-4" style={{ marginBottom: "var(--space-4)" }}><KPICard label="Monitored meters" value={buses.length || "—"} icon={Gauge} tone="primary" /><KPICard label="Online" value={buses.length} icon={CheckCircle2} tone="success" /><KPICard label="Data source" value={meters.data?.source?.available === false ? "Standby" : "Active"} icon={Activity} tone="info" /><KPICard label="Anomalies" value={buses.filter((bus) => bus.attack_type && bus.attack_type !== "normal").length} icon={ShieldAlert} tone="warning" /></div><Card title="Meter Inventory" subtitle="Real-time values from the grid simulator"><DataTable rows={buses} keyField="bus_id" emptyMessage="Waiting for meter data" columns={[{ key: "bus_id", header: "Meter", className: "mono emphasis", render: (row) => `SM_${String(row.bus_id).padStart(4, "0")}` }, { key: "consumer_type", header: "Type", render: (row) => <Badge tone="neutral">{row.consumer_type}</Badge> }, { key: "voltage", header: "Voltage", className: "mono", render: (row) => `${row.voltage?.toFixed(3)} pu` }, { key: "current", header: "Current", className: "mono", render: (row) => `${row.current?.toFixed(1)} A` }, { key: "consumption", header: "Power", className: "mono", render: (row) => `${row.consumption?.toFixed(2)} kW` }, { key: "attack_type", header: "State", render: (row) => <Badge tone={row.attack_type === "normal" || !row.attack_type ? "success" : "critical"}>{row.attack_type || "normal"}</Badge> }]} /></Card></div>;
}

function AlertsPage({ config, Icon, alertRows }) {
  return <div><PageHeader config={config} Icon={Icon} tone={alertRows.length ? "warning" : "success"} status={alertRows.length ? `${alertRows.length} active alerts` : "No active alerts"} /><Card title="Incident Queue" subtitle="Events are streamed from the anomaly-detection API"><DataTable rows={alertRows} keyField="id" emptyMessage="No alerts have been recorded in this session" columns={[{ key: "severity", header: "Severity", render: (row) => <Badge tone="critical">{row.severity || "high"}</Badge> }, { key: "attack_type", header: "Detection" }, { key: "meter", header: "Asset", className: "mono emphasis" }, { key: "timestamp", header: "Time", className: "mono", render: (row) => row.timestamp ? new Date(row.timestamp * 1000).toLocaleTimeString("en-GB") : "—" }, { key: "status", header: "Status", render: () => <Badge tone="warning">Investigating</Badge> }]} /></Card></div>;
}

function UsersPage({ config, Icon }) {
  return <div><PageHeader config={config} Icon={Icon} tone="success" status="Access control active" /><Card title="Platform Users" subtitle="Role-based access directory"><DataTable rows={USERS.map(([name, role, department, status]) => ({ id: name, name, role, department, status }))} keyField="id" columns={[{ key: "name", header: "User", className: "emphasis" }, { key: "role", header: "Role" }, { key: "department", header: "Department" }, { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "Active" ? "success" : "warning"}>{row.status}</Badge> }]} /></Card></div>;
}

function SettingsPage({ config, Icon, health, model, chain }) {
  const rows = [["Grid polling", "2 seconds", !health.error], ["Model inference", model.data?.detector?.loaded ? "Running" : "Stopped", !!model.data?.detector?.loaded], ["Ledger consensus", chain.data?.valid ? "Verified" : "Unavailable", !!chain.data?.valid], ["Environment", "Production simulation", true]];
  return <div><PageHeader config={config} Icon={Icon} tone="success" status="Configuration ready" /><Card title="Runtime Configuration" subtitle="Current service settings"><div className="settings-list">{rows.map(([label, value, enabled]) => <div className="settings-row" key={label}><div><div className="type-small" style={{ fontWeight: 600 }}>{label}</div><div className="type-small text-muted">{value}</div></div><Badge tone={enabled ? "success" : "critical"}>{enabled ? "Enabled" : "Check service"}</Badge></div>)}</div></Card></div>;
}

function HealthLine({ label, value }) { return <div className="health-line"><span className="type-small text-secondary">{label}</span><Badge tone={value ? "success" : "critical"}><StatusDot tone={value ? "success" : "critical"} />{value ? "Operational" : "Offline"}</Badge></div>; }
