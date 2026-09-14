/** Segmented donut ring with center readout + legend — e.g. load mix, detection mix. */
export function DonutRing({ segments = [], size = 148, thickness = 16, centerLabel, centerSublabel, showLegend = true }) {
  const total = segments.reduce((s, seg) => s + (seg.value || 0), 0) || 1;
  const r = (size - thickness) / 2;
  const circumference = 2 * Math.PI * r;

  const gapDeg = segments.length > 1 ? 3 : 0;
  const gapLen = (gapDeg / 360) * circumference;
  let cursor = 0;
  const arcs = segments.map((seg) => {
    const pct = (seg.value || 0) / total;
    const rawDash = pct * circumference;
    const dash = Math.max(0, rawDash - gapLen);
    const gap = circumference - dash;
    const offset = -cursor * circumference;
    cursor += pct;
    return { ...seg, dash, gap, offset, pct };
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
      <div style={{ position: "relative", width: size, height: size, flex: "0 0 auto" }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={thickness} />
          {arcs.map((a, i) => (
            <circle
              key={a.label ?? i}
              cx={size / 2} cy={size / 2} r={r} fill="none"
              stroke={a.color} strokeWidth={thickness}
              strokeDasharray={`${a.dash} ${a.gap}`}
              strokeDashoffset={a.offset}
              strokeLinecap="round"
              style={{ transition: "stroke-dasharray 400ms var(--ease-standard)" }}
            />
          ))}
        </svg>
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", textAlign: "center", padding: thickness,
        }}>
          <div style={{ fontSize: size * 0.16, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.1 }}>{centerLabel}</div>
          {centerSublabel && <div style={{ fontSize: size * 0.075, color: "var(--text-muted)", fontWeight: 600, marginTop: 3 }}>{centerSublabel}</div>}
        </div>
      </div>

      {showLegend && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
          {arcs.map((a, i) => (
            <div key={a.label ?? i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "var(--text-small)" }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: a.color, flex: "0 0 auto", boxShadow: `0 0 6px ${a.color}99` }} />
              <span className="text-secondary" style={{ flex: 1 }}>{a.label}</span>
              <span style={{ fontWeight: 700 }}>{(a.pct * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
