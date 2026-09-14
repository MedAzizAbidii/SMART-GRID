import { useEffect, useRef, useState } from "react";
import { BrainCircuit, Play, Square, Cpu, Target, Gauge, Timer } from "lucide-react";
import { Card } from "../components/ui/Card";
import { KPICard } from "../components/ui/KPICard";
import { Badge, StatusDot } from "../components/ui/Badge";
import { ProgressBar } from "../components/ui/ProgressBar";
import { DataTable } from "../components/ui/DataTable";
import { usePolling } from "../hooks/usePolling";
import { getModelStatus, getRealisticDemoReading } from "../api/client";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

// Meter index for the live feed demo. The backend generates readings from
// smart_meters_simulator._make_row(meter_idx, ...) — the same generator that
// produced the model's training distribution — instead of transforming
// /api/grid/all bus data (a separate, unrelated synthetic engine) into a
// reading shape, which was measured to produce a false anomaly on every run.
const DEMO_METER_IDX = 1;

export default function AIDetection() {
  const model = usePolling(getModelStatus, 6000);
  const [feeding, setFeeding] = useState(false);
  const [history, setHistory] = useState([]);
  const [latest, setLatest] = useState(null);
  const timerRef = useRef(null);
  const tRef = useRef(0);

  useEffect(() => {
    if (!feeding) { clearInterval(timerRef.current); return; }
    timerRef.current = setInterval(async () => {
      tRef.current += 1;
      try {
        const res = await getRealisticDemoReading(DEMO_METER_IDX);
        setLatest(res);
        if (res.anomaly_score !== undefined) {
          setHistory((h) => [...h, { t: tRef.current, score: res.anomaly_score, threshold: res.threshold }].slice(-40));
        }
      } catch { /* transient — next tick retries */ }
    }, 1500);
    return () => clearInterval(timerRef.current);
  }, [feeding]);

  const detector = model.data?.detector;
  const champion = model.data?.registry?.champion_metrics;
  const status = latest?.status; // "insufficient_data" while buffering
  const isBuffering = status === "insufficient_data" || (!latest && feeding);

  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <h1 className="type-h2">AI Detection Engine</h1>
          <Badge tone={detector?.loaded ? "success" : "critical"}>
            <StatusDot tone={detector?.loaded ? "success" : "critical"} /> {detector?.loaded ? "Model Loaded" : "Unavailable"}
          </Badge>
        </div>
        <p className="text-secondary type-small" style={{ marginTop: 4 }}>
          Transformer Autoencoder ensemble (dim=128, heads=4, layers=3) · live inference via /api/detect
        </p>
      </div>

      <Card style={{ marginBottom: "var(--space-4)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div className="kpi-icon" style={{ background: "var(--color-primary-dim)", color: "var(--color-primary)" }}>
              <BrainCircuit size={20} />
            </div>
            <div>
              <div className="card-title">Live Detection Feed</div>
              <div className="type-small text-muted">
                Streams realistic smart-meter readings into the model every 1.5s to build a live sequence buffer (seq_len={detector?.seq_len ?? 8})
              </div>
            </div>
          </div>
          <button
            className={`tab-btn ${feeding ? "active" : ""}`}
            style={{ border: "1px solid var(--color-border)", borderRadius: 8, padding: "8px 16px", display: "flex", gap: 6, alignItems: "center" }}
            onClick={() => setFeeding((f) => !f)}
          >
            {feeding ? <Square size={14} /> : <Play size={14} />} {feeding ? "Stop Feed" : "Start Live Feed"}
          </button>
        </div>
      </Card>

      <div className="grid grid-cols-5" style={{ marginBottom: "var(--space-4)" }}>
        <KPICard label="Anomaly Score" value={latest?.anomaly_score !== undefined ? latest.anomaly_score.toFixed(5) : "—"} icon={Target} tone={latest?.is_anomaly ? "critical" : "success"} />
        <KPICard label="Confidence" value={latest?.confidence !== undefined ? Math.round(latest.confidence * 100) : "—"} unit="%" icon={Gauge} tone="primary" />
        <KPICard label="Inference Time" value={latest?.inference_ms?.toFixed(1) ?? "—"} unit="ms" icon={Timer} tone="info" />
        <KPICard label="Buffer Fill" value={latest?.buffer_fill !== undefined ? `${latest.buffer_fill}/${detector?.seq_len ?? 8}` : "—"} icon={Cpu} tone="neutral" />
        <KPICard label="Model Avg Latency" value={detector?.avg_latency_ms?.toFixed(1) ?? "—"} unit="ms" icon={Timer} tone="info" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "2fr 1fr", marginBottom: "var(--space-4)" }}>
        <Card title="Reconstruction Score Timeline" subtitle="Live session history — accumulated from real /api/detect calls">
          {history.length === 0 ? (
            <div className="empty-state"><div className="empty-state-title">
              {feeding ? "Buffering... start the feed and wait for enough readings" : "Start the live feed to see real-time scores"}
            </div></div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="score-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="t" stroke="var(--text-muted)" fontSize={11} />
                <YAxis stroke="var(--text-muted)" fontSize={11} />
                <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 8 }} />
                <Area type="monotone" dataKey="score" stroke="#3B82F6" strokeWidth={2} fill="url(#score-grad)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="Decision Panel" subtitle="Natural-language explanation of the latest result">
          {isBuffering ? (
            <div className="empty-state"><div className="empty-state-title">Buffering readings — the model needs a full sequence before it can decide.</div></div>
          ) : !latest ? (
            <div className="empty-state"><div className="empty-state-title">No detection run yet</div></div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <Badge tone={latest.is_anomaly ? "critical" : "success"}>
                {latest.is_anomaly ? `Anomaly — ${latest.attack_type}` : "Normal behavior"}
              </Badge>
              <p className="type-small text-secondary">
                {latest.is_anomaly
                  ? `The reconstruction error (${latest.anomaly_score?.toFixed(5)}) exceeds the adaptive threshold (${latest.threshold?.toFixed(5)}) for this meter, classified as ${latest.attack_type} with ${Math.round((latest.confidence || 0) * 100)}% confidence.`
                  : `The reconstruction error (${latest.anomaly_score?.toFixed(5)}) is within the adaptive threshold (${latest.threshold?.toFixed(5)}) — no deviation from learned normal behavior detected.`}
              </p>
              {latest.top_features?.length > 0 && (
                <div>
                  <div className="type-micro text-muted" style={{ marginBottom: 6 }}>Top contributing features</div>
                  {latest.top_features.slice(0, 3).map((f) => (
                    <div key={f.feature} style={{ marginBottom: 6 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                        <span className="text-secondary">{f.feature}</span><span>{(f.contribution * 100).toFixed(1)}%</span>
                      </div>
                      <ProgressBar value={f.contribution * 100} tone="primary" height={5} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card title="Champion Model Metrics" subtitle={`${model.data?.registry?.champion_version || "—"} · ${model.data?.registry?.champion_dir?.split(/[\\/]/).pop() || ""}`}>
        <DataTable
          emptyMessage="Model registry unavailable"
          rows={champion ? [{ id: 1, ...champion }] : []}
          keyField="id"
          columns={[
            { key: "accuracy", header: "Accuracy", className: "mono emphasis", render: (r) => `${(r.accuracy * 100).toFixed(2)}%` },
            { key: "precision", header: "Precision", className: "mono", render: (r) => `${(r.precision * 100).toFixed(2)}%` },
            { key: "recall", header: "Recall", className: "mono", render: (r) => `${(r.recall * 100).toFixed(2)}%` },
            { key: "f1_score", header: "F1", className: "mono", render: (r) => r.f1_score.toFixed(4) },
            { key: "roc_auc", header: "ROC-AUC", className: "mono", render: (r) => `${(r.roc_auc * 100).toFixed(2)}%` },
          ]}
        />
      </Card>
    </div>
  );
}
