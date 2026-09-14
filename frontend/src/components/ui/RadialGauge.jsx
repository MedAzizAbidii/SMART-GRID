const TONE_COLORS = {
  primary: "#3B82F6",
  success: "#22C55E",
  warning: "#F59E0B",
  critical: "#EF4444",
  info: "#06B6D4",
};

/** Tick marks around a circle — gives the ring an "instrument dial" read, like an analog gauge. */
function Ticks({ size, count = 40, majorEvery = 5, r, color }) {
  const ticks = [];
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * 2 * Math.PI;
    const isMajor = i % majorEvery === 0;
    const len = isMajor ? 7 : 3;
    const x1 = size / 2 + (r + 4) * Math.cos(angle);
    const y1 = size / 2 + (r + 4) * Math.sin(angle);
    const x2 = size / 2 + (r + 4 + len) * Math.cos(angle);
    const y2 = size / 2 + (r + 4 + len) * Math.sin(angle);
    ticks.push(
      <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeOpacity={isMajor ? 0.55 : 0.25} strokeWidth={isMajor ? 1.75 : 1.1} />
    );
  }
  return <g>{ticks}</g>;
}

/** Circular progress gauge — used for AI Confidence, System Health, Threat Level. */
export function RadialGauge({ value, size = 84, strokeWidth = 7, tone = "primary", label, sublabel, ticks = false }) {
  const color = TONE_COLORS[tone] || TONE_COLORS.primary;
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const offset = circumference * (1 - pct / 100);
  const glowId = `gauge-glow-${color.replace("#", "")}`;

  return (
    <div style={{ position: "relative", width: size, height: size, flex: "0 0 auto" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", overflow: "visible" }}>
        <defs>
          <filter id={glowId} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation={strokeWidth * 0.4} result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {ticks && <Ticks size={size} r={r} color={color} />}
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          filter={`url(#${glowId})`}
          style={{ transition: "stroke-dashoffset 400ms var(--ease-standard)" }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", textAlign: "center",
      }}>
        <div style={{ fontSize: size * 0.19, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.1 }}>
          {label ?? `${pct.toFixed(0)}%`}
        </div>
        {sublabel && <div style={{ fontSize: size * 0.1, color: "var(--text-muted)", fontWeight: 600, marginTop: 2 }}>{sublabel}</div>}
      </div>
    </div>
  );
}

/** Half-circle (gauge-style) variant — used for Threat Level. */
export function SemiGauge({ value, max = 100, size = 160, tone = "warning", label, sublabel }) {
  const color = TONE_COLORS[tone] || TONE_COLORS.warning;
  const strokeWidth = 10;
  const r = (size - strokeWidth) / 2;
  const circumference = Math.PI * r;
  const pct = Math.max(0, Math.min(1, value / max));
  const offset = circumference * (1 - pct);
  const glowId = `semigauge-glow-${color.replace("#", "")}`;

  const majorTicks = Array.from({ length: 11 }, (_, i) => {
    const t = i / 10;
    const angle = Math.PI - t * Math.PI;
    const rOuter = r + strokeWidth / 2 + 3;
    const rInner = r + strokeWidth / 2 + (i % 5 === 0 ? 8 : 5);
    const cx = size / 2;
    const cy = size / 2;
    return {
      x1: cx + rOuter * Math.cos(angle), y1: cy - rOuter * Math.sin(angle),
      x2: cx + rInner * Math.cos(angle), y2: cy - rInner * Math.sin(angle),
      major: i % 5 === 0,
    };
  });

  return (
    <div style={{ position: "relative", width: size, height: size / 2 + 16 }}>
      <svg width={size} height={size / 2 + strokeWidth + 8} viewBox={`0 0 ${size} ${size / 2 + strokeWidth + 8}`} style={{ overflow: "visible" }}>
        <defs>
          <filter id={glowId} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation={strokeWidth * 0.35} result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {majorTicks.map((t, i) => (
          <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} stroke={color} strokeOpacity={t.major ? 0.5 : 0.22} strokeWidth={t.major ? 1.75 : 1.1} />
        ))}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${r} ${r} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={strokeWidth} strokeLinecap="round"
        />
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${r} ${r} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          filter={`url(#${glowId})`}
          style={{ transition: "stroke-dashoffset 400ms var(--ease-standard)" }}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", paddingBottom: 4 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color }}>{label}</div>
        {sublabel && <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>{sublabel}</div>}
      </div>
    </div>
  );
}
