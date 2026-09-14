// API client — every function here hits a REAL, verified endpoint on
// api_server.py. Response shapes were confirmed live against the running
// server before being coded (see conversation notes); nothing here is
// speculative. Where the backend has no equivalent endpoint yet, the page
// components fall back to clearly-labeled sample data — never this client.

// Empty by default: requests go through Vite's dev-server proxy (see
// vite.config.js), which forwards /api, /health, /auth, /metrics to
// api_server.py — no CORS configuration needed for local development.
// Set VITE_API_BASE_URL only when serving the built frontend from
// somewhere other than behind that proxy (e.g. a separate static host).
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok && res.status !== 429) {
    const body = await res.text().catch(() => "");
    throw new Error(`${path} -> HTTP ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

// ── System / health ──────────────────────────────────────────────────────
export const getHealth = () => request("/health");
export const getHealthReady = () => request("/health/ready");
export const getHealthDetailed = () => request("/health/detailed");

// ── AI model ──────────────────────────────────────────────────────────────
export const getModelStatus = () => request("/api/model/status");
export const getModelThresholds = () => request("/api/model/thresholds");
export const getModelRegistry = () => request("/api/model/registry");

// ── Detection ─────────────────────────────────────────────────────────────
export const detectReading = (reading) =>
  request("/api/detect", { method: "POST", body: JSON.stringify(reading) });
export const detectBatch = (readings) =>
  request("/api/detect/batch", { method: "POST", body: JSON.stringify(readings) });
export const getAlerts = () => request("/api/alerts");
// Demo-only: generates one realistic reading server-side (same distribution
// the model was trained on — see api_server.py's _DEMO_SIM_AVAILABLE comment)
// and scores it via /api/detect internally. Used by the AI Detection and
// Explainable AI "live feed" buttons instead of feeding them /api/grid/all's
// unrelated synthetic engine, which produced consistent false positives.
export const getRealisticDemoReading = (meterIdx = 1) =>
  request(`/api/demo/realistic-reading?meter_idx=${meterIdx}`, { method: "POST" });

// ── Grid ──────────────────────────────────────────────────────────────────
export const getGridAll = () => request("/api/grid/all");
export const getGridBus = (busId) => request(`/api/grid/bus/${busId}`);

// ── Smart meters (legacy CSV-backed; may report unavailable in a fresh
//    session — pages must handle `source.available === false` gracefully) ──
export const getSmartMetersStatus = () => request("/api/smart-meters/status");
export const getEnhancedDetections = () => request("/api/smart-meters/enhanced-detections");

// ── Blockchain ────────────────────────────────────────────────────────────
export const getBlockchainStatus = () => request("/api/blockchain/status");
// Real on-chain layer (Sepolia by default) — see production/blockchain/onchain_bridge.py.
// Disabled by default; returns { enabled: false, reason } until the operator
// sets SGRID_ONCHAIN_ENABLED=1 with a funded deployer wallet.
export const getOnchainStatus = () => request("/api/blockchain/onchain/status");

// ── Simulation (protected; requires auth in production mode) ────────────
export const simulateAttack = (payload) =>
  request("/api/simulate/attack", { method: "POST", body: JSON.stringify(payload) });

// ── Auth ──────────────────────────────────────────────────────────────────
export const login = (username, password) =>
  request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });

export { BASE_URL };
