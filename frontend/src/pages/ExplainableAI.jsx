import { useState } from "react";
import { Lightbulb, Play } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Tabs } from "../components/ui/Tabs";
import { Badge } from "../components/ui/Badge";
import { ProgressBar } from "../components/ui/ProgressBar";
import { MockFlag } from "../components/ui/EmptyState";
import { getRealisticDemoReading } from "../api/client";

const TABS = [
  { value: "features", label: "Feature Importance" },
  { value: "gradients", label: "Integrated Gradients" },
  { value: "attention", label: "Attention Map" },
  { value: "shap", label: "SHAP" },
  { value: "breakdown", label: "Prediction Breakdown" },
];

// Meter index for the live feed demo — see AIDetection.jsx's DEMO_METER_IDX
// comment for why this goes through the backend's realistic generator
// instead of /api/grid/all.
const DEMO_METER_IDX = 2;

export default function ExplainableAI() {
  const [tab, setTab] = useState("features");
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  async function runExplanation() {
    setRunning(true);
    setError(null);
    try {
      let res;
      for (let i = 0; i < 8; i++) {
        res = await getRealisticDemoReading(DEMO_METER_IDX);
      }
      // Final reading carries an injected attack — the detector only runs
      // XAI attribution (top_features) when is_anomaly is true, so a page
      // whose whole purpose is showing that attribution needs a real
      // anomaly to explain, not another normal reading.
      res = await getRealisticDemoReading(DEMO_METER_IDX, "Surcharge");
      setResult(res);
    } catch {
      setError("Backend unreachable — check the API is running.");
    } finally {
      setRunning(false);
    }
  }

  const hasResult = result && result.status !== "insufficient_data";

  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <h1 className="type-h2">Explainable AI</h1>
          <Badge tone="primary"><Lightbulb size={12} /> Integrated Gradients + Attention</Badge>
        </div>
        <p className="text-secondary type-small" style={{ marginTop: 4 }}>
          Real-time explanations (WHERE = attention, WHY = integrated gradients) exactly as computed by `ingest()` in production.
        </p>
      </div>

      <Card style={{ marginBottom: "var(--space-4)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div className="type-small text-secondary">
            Runs 9 consecutive realistic smart-meter readings through the model, then explains the final prediction.
          </div>
          <button
            className="tab-btn"
            style={{ border: "1px solid var(--color-border)", borderRadius: 8, padding: "8px 16px", display: "flex", gap: 6, alignItems: "center" }}
            onClick={runExplanation}
            disabled={running}
          >
            <Play size={14} /> {running ? "Running..." : "Run Explanation"}
          </button>
        </div>
        {error && <p className="type-small" style={{ color: "var(--color-critical)", marginTop: 8 }}>{error}</p>}
      </Card>

      <Card>
        <Tabs tabs={TABS} active={tab} onChange={setTab} />
        <div style={{ paddingTop: "var(--space-4)" }}>
          {!hasResult && (
            <div className="empty-state"><div className="empty-state-title">Run an explanation above to see live results</div></div>
          )}

          {hasResult && tab === "features" && <FeatureBars features={result.top_features} title="Top Feature Contributions" />}
          {hasResult && tab === "gradients" && (
            <>
              <FeatureBars features={result.top_features} title="Integrated Gradients Attribution (production XAI method)" />
              <p className="type-small text-muted" style={{ marginTop: "var(--space-3)" }}>
                Computed via 20-step gradient interpolation against a zero baseline, exactly as `integrated_gradients()` in
                `ml_pipeline/realtime_detector.py` — the method actually used in the real-time path, since SHAP is too slow for it.
              </p>
            </>
          )}
          {hasResult && tab === "attention" && (
            <div>
              <div className="type-small text-muted" style={{ marginBottom: "var(--space-3)" }}>
                Critical timestep (highest attention weight) in the 8-reading sequence:
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {Array.from({ length: 8 }, (_, i) => (
                  <div key={i} style={{
                    flex: 1, height: 56, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700,
                    background: i === result.critical_timestep ? "var(--color-primary)" : "var(--color-card)",
                    border: `1px solid ${i === result.critical_timestep ? "var(--color-primary)" : "var(--color-border)"}`,
                    color: i === result.critical_timestep ? "#fff" : "var(--text-muted)",
                  }}>
                    t-{7 - i}
                  </div>
                ))}
              </div>
              <p className="type-small text-muted" style={{ marginTop: "var(--space-3)" }}>
                Measured caveat (Chapter 12 of the thesis): attention entropy on this model is ~0.96/1.0 — near-uniform — so this
                highlighted step should be read as a weak signal, not a confident localization.
              </p>
            </div>
          )}
          {hasResult && tab === "shap" && (
            <div>
              <div style={{ marginBottom: "var(--space-3)" }}><MockFlag /></div>
              <p className="type-small text-secondary">
                SHAP (KernelSHAP/DeepSHAP) is implemented in `ml_pipeline/shap_explainer.py` but is only run offline — it is too
                slow for the real-time detection path (Chapter 8.2). No live endpoint exists to compute it on demand, so this tab
                shows illustrative sample values rather than a real call.
              </p>
              <FeatureBars
                features={[
                  { feature: "tension_v_rolling_std_6", contribution: 0.31 },
                  { feature: "consommation_kw", contribution: 0.24 },
                  { feature: "zone_consumption_mean", contribution: 0.18 },
                ]}
                title="Sample SHAP values (illustrative)"
              />
            </div>
          )}
          {hasResult && tab === "breakdown" && (
            <div className="grid grid-cols-3">
              <BreakdownStat label="v2 (recall-optimized)" score={result.v2_score} alarm={result.v2_alarm} />
              <BreakdownStat label="v3 (precision-optimized)" score={result.v3_score} alarm={result.v3_alarm} />
              <BreakdownStat label="Ensemble confidence" score={result.confidence} alarm={result.is_anomaly} isConfidence label2={result.confidence_label} />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

function FeatureBars({ features, title }) {
  if (!features?.length) return <div className="empty-state"><div className="empty-state-title">No feature data</div></div>;
  return (
    <div>
      <div className="type-micro text-muted" style={{ marginBottom: 10 }}>{title}</div>
      {features.map((f) => (
        <div key={f.feature} style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
            <span className="text-secondary type-mono">{f.feature}</span>
            <span style={{ fontWeight: 600 }}>{(f.contribution * 100).toFixed(1)}%</span>
          </div>
          <ProgressBar value={f.contribution * 100} tone="primary" />
        </div>
      ))}
    </div>
  );
}

function BreakdownStat({ label, score, alarm, isConfidence, label2 }) {
  return (
    <div className="card">
      <div className="type-small text-muted">{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, marginTop: 6 }}>
        {isConfidence ? `${Math.round((score || 0) * 100)}%` : score?.toFixed(5)}
      </div>
      <div style={{ marginTop: 8 }}>
        <Badge tone={alarm ? "critical" : "success"}>{label2 || (alarm ? "Alarm" : "Normal")}</Badge>
      </div>
    </div>
  );
}
