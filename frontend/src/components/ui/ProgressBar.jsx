const TONE_COLORS = {
  primary: "var(--color-primary)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  critical: "var(--color-critical)",
  info: "var(--color-info)",
};

export function ProgressBar({ value, tone = "primary", height = 8 }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="progress-track" style={{ height }}>
      <div className="progress-fill" style={{ width: `${pct}%`, background: TONE_COLORS[tone] || TONE_COLORS.primary }} />
    </div>
  );
}
