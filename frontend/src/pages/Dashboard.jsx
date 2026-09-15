import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BrainCircuit, Blocks, AlertTriangle, Zap,
  Gauge, Wifi, Activity, Cpu, Waves, Timer,
  CheckCircle2, UserCheck, Search as SearchIcon, ArrowRight,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { KPICard } from "../components/ui/KPICard";
import { Badge, StatusDot } from "../components/ui/Badge";
import { DataTable } from "../components/ui/DataTable";
import { MiniMonitorCard } from "../components/ui/MiniMonitorCard";
import { RadialGauge, SemiGauge } from "../components/ui/RadialGauge";
import { DonutRing } from "../components/ui/DonutRing";
import { ThresholdBar } from "../components/ui/ThresholdBar";
import { GridNetwork } from "../components/grid/GridNetwork";
import { usePolling } from "../hooks/usePolling";
import { useHistorySeries } from "../hooks/useHistorySeries";
import {
  getGridAll, getHealthDetailed, getBlockchainStatus, getModelStatus,
  getModelRegistry, getAlerts,
} from "../api/client";

const TONE_BY_LEVEL = { ok: "success", warning: "warning", critical: "critical" };
const CONSUMER_TYPE_COLOR = { residential: "#3B82F6", commercial: "#06B6D4", industrial: "#8B5CF6" };
const CONSUMER_TYPE_LABEL = { residential: "Residential", commercial: "Commercial", industrial: "Industrial" };
const TONE_HEX = { primary: "#3B82F6", success: "#22C55E", warning: "#F59E0B", critical: "#EF4444", info: "#06B6D4" };
const VERSION_STATUS_TONE = { champion: "success", candidate: "info", retired: "neutral", rolled_back: "critical" };
const ACTIONS = [
  { key: "acknowledge", label: "Acknowledge", icon: CheckCircle2 },
  { key: "assign", label: "Assign", icon: UserCheck },
  { key: "investigate", label: "Investigate", icon: SearchIcon },
];

export default function Dashboard() {
  const grid = usePolling(getGridAll, 2000);
  const health = usePolling(getHealthDetailed, 5000);
  const chain = usePolling(getBlockchainStatus, 8000);
  const model = usePolling(getModelStatus, 8000);
  const registry = usePolling(getModelRegistry, 15000);
  const alerts = usePolling(getAlerts, 4000);
  const [selectedBus, setSelectedBus] = useState(null);
  const [alertStatus, setAlertStatus] = useState({});

  const buses = grid.data?.buses || [];
  const totalLoad = buses.reduce((sum, b) => sum + (b.consumption || 0), 0);
  const avgVoltage = buses.length ? buses.reduce((s, b) => s + (b.voltage || 0), 0) / buses.length : 0;
  const avgCurrent = buses.length ? buses.reduce((s, b) => s + (b.current || 0), 0) / buses.length : 0;
  const avgFrequency = buses.length ? buses.reduce((s, b) => s + (b.frequency || 0), 0) / buses.length : 0;
  const attacksNow = buses.filter((b) => b.attack_type && b.attack_type !== "normal");

  const loadMix = useMemo(() => {
    const byType = {};
    buses.forEach((b) => {
      const t = b.consumer_type || "residential";
      byType[t] = (byType[t] || 0) + (b.consumption || 0);
    });
    return Object.entries(byType)
      .map(([type, value]) => ({ label: CONSUMER_TYPE_LABEL[type] || type, value, color: CONSUMER_TYPE_COLOR[type] || "#94A3B8" }))
      .sort((a, b) => b.value - a.value);
  }, [buses]);

  const threatLevel = attacksNow.length > 0 ? "critical" : (alerts.data?.count > 0 ? "warning" : "ok");
  const aiStatus = model.data?.detector?.loaded ? "ok" : "critical";

  const championAcc = model.data?.registry?.champion_metrics;
  const aiConfidence = championAcc?.roc_auc ? Math.round(championAcc.roc_auc * 1000) / 10 : null;
  const cpuPct = health.data?.resources?.cpu_percent;
  const memPct = health.data?.resources?.memory_percent;
  const latencyMs = model.data?.detector?.avg_latency_ms;

  const loadHistory = useHistorySeries(Number(totalLoad.toFixed(2)), 30);
  const voltageHistory = useHistorySeries(Number(avgVoltage.toFixed(4)), 30);
  const currentHistory = useHistorySeries(Number(avgCurrent.toFixed(2)), 30);
  const freqHistory = useHistorySeries(Number(avgFrequency.toFixed(3)), 30);
  const cpuHistory = useHistorySeries(cpuPct !== undefined ? Number(cpuPct.toFixed(1)) : undefined, 30);
  const memHistory = useHistorySeries(memPct !== undefined ? Number(memPct.toFixed(1)) : undefined, 30);
  const alertHistory = useHistorySeries(alerts.data?.count, 30);
  const blockHistory = useHistorySeries(chain.data?.blocks, 30);
  const confidenceHistory = useHistorySeries(aiConfidence, 30);
  const latencyHistory = useHistorySeries(latencyMs !== undefined ? Number(latencyMs.toFixed(1)) : undefined, 30);

  const recentAlerts = (alerts.data?.alerts || [])
    .slice(0, 6)
    .map((a) => ({ ...a, id: a.id ?? `${a.bus_id}-${a.timestamp}`, meter_id: a.meter_id ?? `SM_${String(a.bus_id).padStart(2, "0")}` }));
  const versions = useMemo(() => [...(registry.data?.versions || [])].reverse().slice(0, 5), [registry.data]);

  const threatPct = threatLevel === "critical" ? 88 : threatLevel === "warning" ? 52 : 14;
  const threatLabel = threatLevel === "critical" ? "HIGH" : threatLevel === "warning" ? "ELEVATED" : "LOW";

  function setAction(alertId, action) {
    setAlertStatus((prev) => ({ ...prev, [alertId]: action }));
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <h1 className="type-h2">National Grid Overview</h1>
          {grid.error ? (
            <Badge tone="critical"><StatusDot tone="critical" /> Grid feed offline</Badge>
          ) : (
            <span className="badge-live"><StatusDot tone="neutral" /> LIVE</span>
          )}
        </div>
        <p className="text-secondary type-small" style={{ marginTop: 4 }}>
          Region: Alger-Est · {buses.length || 14} monitored smart meters · Transformer Autoencoder ensemble active
        </p>
      </div>

      {/* Essential operational indicators */}
      <div className="grid grid-cols-5" style={{ marginBottom: "var(--space-4)" }}>
        <KPICard label="Total Smart Meters" value={buses.length || "—"} icon={Gauge} tone="primary" />
        <KPICard label="Online Devices" value={buses.length} icon={Wifi} tone="success" />
        <KPICard label="Current Load" value={totalLoad.toFixed(1)} unit="kW" icon={Activity} tone="info" spark={loadHistory} />
        <KPICard label="Anomalies (live)" value={attacksNow.length} icon={AlertTriangle} tone={attacksNow.length ? "critical" : "success"} />
        <GaugeKPICard label="AI Confidence" icon={BrainCircuit} tone="primary" value={aiConfidence} sublabel="ROC-AUC" />
      </div>

      {/* Network + asset inspector + threat/model status */}
      <div className="grid" style={{ gridTemplateColumns: "1.7fr 1fr 1fr", marginBottom: "var(--space-4)", alignItems: "start" }}>
        <Card title="Live Grid Topology" subtitle="Alger-Est substation · click a node for detail">
          {grid.error ? (
            <div className="empty-state"><div className="empty-state-title">Grid feed unavailable — check api_server.py is running</div></div>
          ) : (
            <GridNetwork buses={buses} onSelect={setSelectedBus} selectedId={selectedBus?.bus_id} />
          )}
        </Card>

        <Card title="Grid Overview" subtitle={selectedBus ? `SM_${String(selectedBus.bus_id).padStart(2, "0")}` : "No asset selected"}>
          {!selectedBus ? (
            <div className="empty-state"><div className="empty-state-title">Click a node on the network map</div></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <AssetRow label="Consumer type" value={selectedBus.consumer_type} />
              <ThresholdBar label="Voltage" value={selectedBus.voltage} unit="pu" min={0.9} max={1.1} limit={1.05} tone="info" />
              <ThresholdBar label="Frequency" value={selectedBus.frequency} unit="Hz" min={59} max={61} limit={60.5} tone="success" />
              <AssetRow label="Current" value={`${selectedBus.current?.toFixed(2)} A`} />
              <AssetRow label="Consumption" value={`${selectedBus.consumption?.toFixed(2)} kW`} />
              <AssetRow
                label="Status"
                value={selectedBus.attack_type === "normal" ? "Normal" : selectedBus.attack_type}
                badge={selectedBus.attack_type === "normal" ? "success" : "critical"}
              />
              <AssetRow label="Health" value="Nominal" badge="success" />
              <AssetRow label="Maintenance" value="No action required" badge="neutral" />
            </div>
          )}
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Card title="Load Distribution" subtitle="By consumer type" className="hero">
            {loadMix.length === 0 ? (
              <div className="empty-state"><div className="empty-state-title">No smart meter data yet</div></div>
            ) : (
              <DonutRing segments={loadMix} size={156} thickness={17} centerLabel={`${totalLoad.toFixed(0)}`} centerSublabel="kW total" />
            )}
          </Card>

          <Card title="Threat Level" subtitle={`${attacksNow.length} active attack(s)`}>
            <div style={{ display: "flex", justifyContent: "center" }}>
              <SemiGauge value={threatPct} tone={TONE_BY_LEVEL[threatLevel]} label={threatLabel} sublabel={`${threatPct}/100`} />
            </div>
          </Card>

          <Card title="AI Model Status" subtitle={model.data?.detector?.loaded ? "Detector running" : "Detector offline"}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span className="type-small" style={{ fontWeight: 600 }}>Transformer Autoencoder (live)</span>
                <Badge tone={aiStatus === "ok" ? "success" : "critical"}>
                  <StatusDot tone={aiStatus === "ok" ? "success" : "critical"} /> {aiStatus === "ok" ? "Running" : "Stopped"}
                </Badge>
              </div>
              {versions.length === 0 ? (
                <div className="type-small text-muted">No registered model versions yet</div>
              ) : versions.map((v) => (
                <div key={v.version} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span className="type-small text-muted">{v.tag || v.version} · AUC {v.metrics?.roc_auc ? v.metrics.roc_auc.toFixed(3) : "—"}</span>
                  <Badge tone={VERSION_STATUS_TONE[v.status] || "neutral"}>{v.status}</Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Real-time monitoring row — 10 independent live metrics */}
      <Card title="Real-Time Monitoring" subtitle="Individually polled live metrics, updated every 2-8s" style={{ marginBottom: "var(--space-4)" }}>
        <div className="grid grid-cols-10">
          <MiniMonitorCard icon={Zap} label="Power Demand" value={totalLoad.toFixed(1)} unit="kW" tone="primary" spark={loadHistory} />
          <MiniMonitorCard icon={Waves} label="Avg Voltage" value={avgVoltage.toFixed(3)} unit="pu" tone="info" spark={voltageHistory} />
          <MiniMonitorCard icon={Activity} label="Avg Current" value={avgCurrent.toFixed(1)} unit="A" tone="info" spark={currentHistory} />
          <MiniMonitorCard icon={Gauge} label="Avg Frequency" value={avgFrequency.toFixed(2)} unit="Hz" tone="success" spark={freqHistory} />
          <MiniMonitorCard icon={Cpu} label="CPU Usage" value={cpuPct !== undefined ? cpuPct.toFixed(0) : "—"} unit="%" tone={cpuPct > 80 ? "critical" : "primary"} spark={cpuHistory} />
          <MiniMonitorCard icon={Cpu} label="Memory Usage" value={memPct !== undefined ? memPct.toFixed(0) : "—"} unit="%" tone={memPct > 80 ? "critical" : "primary"} spark={memHistory} />
          <MiniMonitorCard icon={AlertTriangle} label="Active Alerts" value={alerts.data?.count ?? "—"} tone={alerts.data?.count ? "warning" : "success"} spark={alertHistory} />
          <MiniMonitorCard icon={Blocks} label="Blockchain Blocks" value={chain.data?.blocks ?? "—"} tone="info" spark={blockHistory} />
          <MiniMonitorCard icon={BrainCircuit} label="AI Confidence" value={aiConfidence ?? "—"} unit="%" tone="primary" spark={confidenceHistory} />
          <MiniMonitorCard icon={Timer} label="Inference Latency" value={latencyMs !== undefined ? latencyMs.toFixed(1) : "—"} unit="ms" tone="success" spark={latencyHistory} />
        </div>
      </Card>

      {/* Recent alerts */}
      <Card
        title="Recent Alerts"
        subtitle="Live from /api/alerts"
        action={<Link to="/alerts" className="type-small" style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--color-primary)", fontWeight: 600 }}>View All <ArrowRight size={14} /></Link>}
        style={{ marginBottom: "var(--space-4)" }}
      >
        <DataTable
          emptyMessage="No alerts recorded yet in this session — trigger a detection via AI Detection or the demo scenario to populate this table."
          columns={[
            { key: "severity", header: "Severity", render: (r) => <Badge tone="critical">{r.severity || "High"}</Badge> },
            { key: "attack_type", header: "Attack" },
            { key: "meter_id", header: "Device" },
            { key: "source", header: "Source", render: () => "Grid Simulator" },
            {
              key: "time", header: "Time",
              render: (r) => {
                const ts = r.timestamp || r.time;
                return ts ? new Date(ts * 1000).toLocaleTimeString("en-GB", { hour12: false }) : "—";
              },
            },
            {
              key: "status", header: "Status",
              render: (r) => {
                const st = alertStatus[r.id];
                return <Badge tone={st ? "success" : "warning"}>{st ? st : "Investigating"}</Badge>;
              },
            },
            {
              key: "actions", header: "Actions",
              render: (r) => (
                <div style={{ display: "flex", gap: 6 }}>
                  {ACTIONS.map((a) => (
                    <button
                      key={a.key}
                      className="topbar-icon-btn"
                      title={a.label}
                      aria-label={a.label}
                      onClick={() => setAction(r.id, a.label)}
                    >
                      <a.icon size={14} />
                    </button>
                  ))}
                </div>
              ),
            },
          ]}
          rows={recentAlerts}
          keyField="id"
        />
      </Card>

      <footer className="dashboard-footer">
        <span>© 2026 Smart Grid Cybersecurity Platform — PFE Project</span>
        <div className="dashboard-footer-links">
          <Link to="/reports">Reports</Link>
          <Link to="/settings">Settings</Link>
          <span>v1.0.0-thesis</span>
        </div>
      </footer>
    </div>
  );
}

function GaugeKPICard({ label, icon: Icon, tone, value, sublabel }) {
  return (
    <div className="card kpi-card" style={{ alignItems: "center", "--tone-color": TONE_HEX[tone] || TONE_HEX.primary }}>
      <div className="kpi-card-top" style={{ width: "100%" }}>
        <div className="kpi-label">{label}</div>
        {Icon && (
          <div className="kpi-icon" style={{ width: 28, height: 28 }}>
            <Icon size={14} strokeWidth={2} />
          </div>
        )}
      </div>
      <div style={{ display: "flex", justifyContent: "center", width: "100%" }}>
        <RadialGauge size={72} strokeWidth={6} tone={tone} value={value ?? 0} label={value !== null && value !== undefined ? `${value}%` : "—"} sublabel={sublabel} ticks />
      </div>
    </div>
  );
}

function AssetRow({ label, value, badge }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span className="type-small text-muted">{label}</span>
      {badge ? <Badge tone={badge}>{value}</Badge> : <span className="type-small" style={{ fontWeight: 600 }}>{value}</span>}
    </div>
  );
}
