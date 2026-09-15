import { useMemo, useState } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Layers, Activity, CloudSun } from "lucide-react";
import { Tabs } from "../ui/Tabs";
import { MockFlag } from "../ui/EmptyState";
import "./GridNetwork.css";

const TYPE_COLOR = {
  residential: "#3B82F6",
  commercial: "#06B6D4",
  industrial: "#8B5CF6",
};

const ATTACK_COLOR = {
  normal: null,
  fdia: "#EF4444",
  dos: "#F59E0B",
  fraud: "#EF4444",
  fault: "#F59E0B",
};

const LAYERS = [
  { value: "all", label: "All Layers" },
  { value: "residential", label: "Residential" },
  { value: "commercial", label: "Commercial" },
  { value: "industrial", label: "Industrial" },
];

// Fixed topology layout: 1 substation feeding N buses across rows.
function layoutBuses(buses, width, height) {
  const cols = 7;
  const rows = 2;
  const marginX = width * 0.1;
  const marginY = height * 0.22;
  const stepX = (width - marginX * 2) / (cols - 1);
  const stepY = (height - marginY * 2) / (rows - 1 || 1);
  return buses.map((b, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    return { ...b, x: marginX + col * stepX, y: marginY + row * stepY };
  });
}

export function GridNetwork({ buses = [], height = 340, onSelect, selectedId, showControls = true }) {
  const [hoverId, setHoverId] = useState(null);
  const [layer, setLayer] = useState("all");
  const [zoom, setZoom] = useState(1);
  const [flowOn, setFlowOn] = useState(true);
  const width = 960;

  const filtered = useMemo(
    () => (layer === "all" ? buses : buses.filter((b) => b.consumer_type === layer)),
    [buses, layer]
  );
  const positioned = useMemo(() => layoutBuses(filtered, width, height), [filtered, height]);
  const substation = { x: width / 2, y: 24 };

  const totalLoad = filtered.reduce((s, b) => s + (b.consumption || 0), 0);
  const alertCount = filtered.filter((b) => b.attack_type && b.attack_type !== "normal").length;

  return (
    <div className="grid-network">
      {showControls && (
        <div className="grid-network-toolbar">
          <div className="grid-network-toolbar-group">
            <Layers size={14} className="text-muted" />
            <Tabs tabs={LAYERS} active={layer} onChange={setLayer} />
          </div>
          <div className="grid-network-toolbar-group">
            <button
              className={`topbar-icon-btn ${flowOn ? "active" : ""}`}
              onClick={() => setFlowOn((f) => !f)}
              aria-label="Toggle power flow animation"
              title="Toggle power flow animation"
            >
              <Activity size={15} />
            </button>
            <button className="topbar-icon-btn" onClick={() => setZoom((z) => Math.min(1.6, +(z + 0.2).toFixed(1)))} aria-label="Zoom in"><ZoomIn size={15} /></button>
            <button className="topbar-icon-btn" onClick={() => setZoom((z) => Math.max(0.8, +(z - 0.2).toFixed(1)))} aria-label="Zoom out"><ZoomOut size={15} /></button>
            <button className="topbar-icon-btn" onClick={() => setZoom(1)} aria-label="Reset zoom"><RotateCcw size={15} /></button>
            <span className="grid-network-weather">
              <CloudSun size={14} /> 24°C <MockFlag />
            </span>
          </div>
        </div>
      )}

      <div className="grid-network-stats">
        <div><span className="grid-network-stats-label">Smart Meters</span><span className="grid-network-stats-value">{filtered.length}</span></div>
        <div><span className="grid-network-stats-label">Load</span><span className="grid-network-stats-value">{totalLoad.toFixed(1)} kW</span></div>
        <div><span className="grid-network-stats-label">Alerts</span><span className="grid-network-stats-value" style={{ color: alertCount ? "var(--color-critical)" : undefined }}>{alertCount}</span></div>
      </div>

      <div style={{ transform: `scale(${zoom})`, transformOrigin: "top center", transition: "transform 200ms" }}>
        <svg viewBox={`0 0 ${width} ${height}`} className="grid-network-svg" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="substation-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Feeder lines from substation to each bus */}
          {positioned.map((b) => {
            const attackColor = ATTACK_COLOR[b.attack_type] || null;
            return (
              <line
                key={`line-${b.bus_id}`}
                x1={substation.x} y1={substation.y} x2={b.x} y2={b.y}
                stroke={attackColor || "rgba(148,163,184,0.18)"}
                strokeWidth={attackColor ? 2 : 1}
                strokeDasharray={attackColor || flowOn ? "4 3" : undefined}
                className={`feeder-line ${attackColor ? "alert" : flowOn ? "flow" : ""}`}
              />
            );
          })}

          {/* Substation node */}
          <circle cx={substation.x} cy={substation.y} r={22} fill="url(#substation-glow)" />
          <circle cx={substation.x} cy={substation.y} r={9} fill="#0B1220" stroke="#3B82F6" strokeWidth="2" />
          <text x={substation.x} y={substation.y - 16} textAnchor="middle" className="grid-network-label">
            Substation Alger-Est · 225kV
          </text>

          {/* Bus nodes */}
          {positioned.map((b) => {
            const color = ATTACK_COLOR[b.attack_type] || TYPE_COLOR[b.consumer_type] || "#94A3B8";
            const isAlert = !!ATTACK_COLOR[b.attack_type];
            const isSelected = selectedId === b.bus_id;
            const isHover = hoverId === b.bus_id;
            const r = 8 + Math.min(10, (b.consumption || 1) * 0.5);
            return (
              <g
                key={b.bus_id}
                transform={`translate(${b.x}, ${b.y})`}
                className="grid-node"
                onMouseEnter={() => setHoverId(b.bus_id)}
                onMouseLeave={() => setHoverId(null)}
                onClick={() => onSelect && onSelect(b)}
              >
                {isAlert && <circle r={r + 8} fill={color} opacity="0.18" className="node-pulse" />}
                <circle r={r} fill="#111827" stroke={color} strokeWidth={isSelected ? 3 : 2} />
                <circle r={r * 0.42} fill={color} />
                <text y={r + 16} textAnchor="middle" className="grid-node-label">
                  SM_{String(b.bus_id).padStart(2, "0")}
                </text>
                {(isHover || isSelected) && (
                  <text y={-(r + 10)} textAnchor="middle" className="grid-node-tooltip">
                    {b.voltage?.toFixed(3)}pu · {b.consumption?.toFixed(1)}kW
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="grid-network-legend">
        <span><i style={{ background: TYPE_COLOR.residential }} /> Residential</span>
        <span><i style={{ background: TYPE_COLOR.commercial }} /> Commercial</span>
        <span><i style={{ background: TYPE_COLOR.industrial }} /> Industrial</span>
        <span><i style={{ background: "#EF4444" }} /> Attack detected</span>
      </div>
    </div>
  );
}
