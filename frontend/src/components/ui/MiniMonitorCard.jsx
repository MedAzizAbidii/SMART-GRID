import { Sparkline } from "./Sparkline";

const TONE_COLORS = {
  primary: "var(--color-primary)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  critical: "var(--color-critical)",
  info: "var(--color-info)",
};

export function MiniMonitorCard({ icon: Icon, label, value, unit, tone = "primary", spark, mock }) {
  const color = TONE_COLORS[tone] || TONE_COLORS.primary;
  return (
    <div className="card mini-monitor-card" style={{ "--tone-color": color }}>
      <div className="mini-monitor-top">
        {Icon && (
          <div className="mini-monitor-icon" style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}>
            <Icon size={14} strokeWidth={2.25} />
          </div>
        )}
        <span className="mini-monitor-label">{label}</span>
        {mock && <span className="mini-monitor-mock-dot" title="Sample data — no live backend source" />}
      </div>
      <div className="mini-monitor-value">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {spark && spark.length > 1 && (
        <div className="mini-monitor-spark"><Sparkline data={spark} color={color} height={24} width={"100%"} /></div>
      )}
    </div>
  );
}
