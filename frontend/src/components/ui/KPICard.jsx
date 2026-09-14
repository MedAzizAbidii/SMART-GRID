import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Sparkline } from "./Sparkline";

const TONE_COLORS = {
  primary: "var(--color-primary)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  critical: "var(--color-critical)",
  info: "var(--color-info)",
};

export function KPICard({ label, value, unit, icon: Icon, tone = "primary", trend, trendLabel, spark, badge }) {
  const color = TONE_COLORS[tone] || TONE_COLORS.primary;
  const trendDir = trend > 0 ? "up" : trend < 0 ? "down" : "flat";
  const TrendIcon = trendDir === "up" ? TrendingUp : trendDir === "down" ? TrendingDown : Minus;

  return (
    <div className="card kpi-card interactive" style={{ "--tone-color": color }}>
      <div className="kpi-card-top">
        <div>
          <div className="kpi-label">{label}</div>
          <div className="kpi-value">
            {value}
            {unit && <span className="unit">{unit}</span>}
          </div>
        </div>
        {Icon && (
          <div className="kpi-icon" style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}>
            <Icon size={20} strokeWidth={2} />
          </div>
        )}
      </div>
      <div className="kpi-footer">
        {trend !== undefined ? (
          <span className={`kpi-trend ${trendDir}`}>
            <TrendIcon size={14} strokeWidth={2.5} />
            {trendLabel || `${trend > 0 ? "+" : ""}${trend}%`}
          </span>
        ) : badge ? badge : <span />}
        {spark && <Sparkline data={spark} color={color} />}
      </div>
    </div>
  );
}
