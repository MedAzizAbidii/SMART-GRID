/** Smart Grid SCADA — FastAPI client */

const BASE = import.meta.env.VITE_API_URL || '';

async function get(path) {
  const r = await fetch(BASE + path, { signal: AbortSignal.timeout(3000) });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(5000),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function checkBackend() {
  const d = await get('/api/model/status');
  return d;
}

export async function getBlockchainStatus() {
  return get('/api/blockchain/status');
}

export async function detectAnomaly(reading) {
  return post('/api/detect', reading);
}

export async function getModelRegistry() {
  return get('/api/model/registry');
}

/** Send a smart meter reading to the detection endpoint */
export function makeReading(meterId, zone, type, overrides = {}) {
  const now = new Date();
  const h = now.getHours();
  return {
    meter_id: meterId,
    consommation_kw: 1.2 + Math.random() * 2.8,
    tension_v: 226 + Math.random() * 8,
    courant_a: 4 + Math.random() * 5,
    zone: 'zone_' + zone.toLowerCase(),
    type,
    timestamp: now.toISOString(),
    ...overrides,
  };
}

/** Readings for each attack type — matches model training data */
export const ATTACK_READINGS = {
  FDIA:  { consommation_kw: 14.2, tension_v: 258, courant_a: 33, power_factor: 0.95 },
  DoS:   { consommation_kw: 0.3,  tension_v: 199, courant_a: 45, power_factor: 0.3  },
  Fraud: { consommation_kw: 31.0, tension_v: 232, courant_a: 28, power_factor: 0.3  },
  Fault: { consommation_kw: 8.5,  tension_v: 185, courant_a: 50, power_factor: 0.7  },
};
