import { AlertTriangle } from "lucide-react";

const TONE_COLORS = {
  primary: "var(--color-primary)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  critical: "var(--color-critical)",
  info: "var(--color-info)",
};

/** Horizontal instrument bar with a safe-limit marker — e.g. voltage/frequency vs. operating band. */
export function ThresholdBar({ label, value, unit = "", min, max, limit, tone = "primary" }) {
  const color = TONE_COLORS[tone] || TONE_COLORS.primary;
  const clampedValue = Math.max(min, Math.min(max, value));
  const valuePct = ((clampedValue - min) / (max - min)) * 100;
  const limitPct = limit !== undefined ? ((limit - min) / (max - min)) * 100 : null;
  const overLimit = limit !== undefined && value > limit;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span className="type-small text-muted">{label}</span>
        <span className="type-small type-mono" style={{ fontWeight: 700, color: overLimit ? "var(--color-warning)" : "var(--text-primary)" }}>
          {value?.toFixed ? value.toFixed(3) : value} {unit}
        </span>
      </div>
      <div style={{ position: "relative", height: 8, marginTop: 2 }}>
        <div style={{ position: "absolute", inset: 0, borderRadius: 999, background: "rgba(255,255,255,0.06)" }} />
        <div
          style={{
            position: "absolute", top: 0, bottom: 0, left: 0,
            width: `${valuePct}%`, borderRadius: 999,
            background: overLimit ? "var(--color-warning)" : color,
            boxShadow: `0 0 8px ${overLimit ? "rgba(245,158,11,.5)" : color + "80"}`,
            transition: "width 400ms var(--ease-standard), background 200ms",
          }}
        />
        {limitPct !== null && (
          <div
            title={`Safe limit: ${limit} ${unit}`}
            style={{
              position: "absolute", top: -5, left: `calc(${limitPct}% - 6px)`,
              color: "var(--color-warning)", display: "flex",
            }}
          >
            <AlertTriangle size={12} strokeWidth={2.5} fill="rgba(245,158,11,0.18)" />
          </div>
        )}
      </div>
    </div>
  );
}
