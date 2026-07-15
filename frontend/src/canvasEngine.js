/**
 * Smart Grid SCADA — Hierarchical Network Canvas Engine
 * Matches the Claude Design exactly:
 *   Generation (top) → HV 225kV → MV 20kV Zones → LV Smart Meters (bottom)
 */

export const ZONE_COLORS  = { A: '#3b82f6', B: '#10b981', C: '#8b5cf6', D: '#f59e0b' };
export const ATK_COLORS   = { FDIA: '#ef4444', DoS: '#f97316', Fraud: '#8b5cf6', Fault: '#f59e0b' };
export const ZONE_LABELS  = { A: 'Résidentiel', B: 'Commercial', C: 'Industriel', D: 'Mixte' };
export const ZONE_VOLTAGE = { A: 'MV 20 kV', B: 'MV 20 kV', C: 'MV 20 kV', D: 'MV 20 kV' };

/* ── Perspective projection (t ∈ [-1,1], d ∈ [0,1]) → {x,y,s} ── */
function proj(W, H, t, d) {
  const s       = 1 - 0.55 * d;
  const horizon = H * 0.04;
  const frontY  = H * 0.98;
  return {
    x: W * 0.5 + t * W * 0.48 * s,
    y: frontY - d * (frontY - horizon),
    s,
  };
}

/* ── Network node positions ─────────────────────────── */
export const GEN_NODES = [
  { id: 'solar',    t: -0.62, d: 0.07, label: 'Solaire',     sub: '450 kW',  icon: 'sun',    col: '#f59e0b' },
  { id: 'wind',     t: -0.22, d: 0.07, label: 'Éolien',      sub: '320 kW',  icon: 'wind',   col: '#10b981' },
  { id: 'thermal',  t:  0.22, d: 0.07, label: 'Thermique',   sub: '1.2 MW',  icon: 'flame',  col: '#ef4444' },
  { id: 'hydro',    t:  0.62, d: 0.07, label: 'Hydraulique', sub: '800 kW',  icon: 'drop',   col: '#3b82f6' },
];

export const HV_NODES = [
  { id: 'hv1', t: -0.35, d: 0.27, label: 'Poste HV/MT', sub: '225 kV', gen: ['solar','wind']    },
  { id: 'hv2', t:  0.35, d: 0.27, label: 'Poste HV/MT', sub: '225 kV', gen: ['thermal','hydro'] },
];

export const MV_NODES = [
  { id: 'mv_A', zone: 'A', t: -0.46, d: 0.46, hv: 'hv1' },
  { id: 'mv_B', zone: 'B', t: -0.14, d: 0.46, hv: 'hv1' },
  { id: 'mv_C', zone: 'C', t:  0.14, d: 0.46, hv: 'hv2' },
  { id: 'mv_D', zone: 'D', t:  0.46, d: 0.46, hv: 'hv2' },
];

export const BUILDINGS = [
  // Zone A — Résidentiel (t centred ≈ -0.46)
  { id: 'SM_0001', zone: 'A', type: 'house',     t: -0.52, d: 0.66, label: 'Maison A1'   },
  { id: 'SM_0002', zone: 'A', type: 'apartment', t: -0.44, d: 0.66, label: 'Appt A2'     },
  { id: 'SM_0003', zone: 'A', type: 'house',     t: -0.36, d: 0.66, label: 'Maison A3'   },
  { id: 'SM_0004', zone: 'A', type: 'office',    t: -0.48, d: 0.83, label: 'Bureau A4'   },
  { id: 'SM_0005', zone: 'A', type: 'house',     t: -0.40, d: 0.83, label: 'Maison A5'   },
  // Zone B — Commercial (t centred ≈ -0.14)
  { id: 'SM_0006', zone: 'B', type: 'shop',      t: -0.20, d: 0.66, label: 'Boutique B1' },
  { id: 'SM_0007', zone: 'B', type: 'office',    t: -0.12, d: 0.66, label: 'Bureau B2'   },
  { id: 'SM_0008', zone: 'B', type: 'hospital',  t: -0.04, d: 0.66, label: 'Hôpital B3'  },
  { id: 'SM_0009', zone: 'B', type: 'shop',      t: -0.16, d: 0.83, label: 'Boutique B4' },
  { id: 'SM_0010', zone: 'B', type: 'office',    t: -0.08, d: 0.83, label: 'Bureau B5'   },
  // Zone C — Industriel (t centred ≈ 0.14)
  { id: 'SM_0011', zone: 'C', type: 'factory',   t:  0.04, d: 0.66, label: 'Usine C1'    },
  { id: 'SM_0012', zone: 'C', type: 'warehouse', t:  0.12, d: 0.66, label: 'Entrepôt C2' },
  { id: 'SM_0013', zone: 'C', type: 'factory',   t:  0.20, d: 0.66, label: 'Usine C3'    },
  { id: 'SM_0014', zone: 'C', type: 'warehouse', t:  0.08, d: 0.83, label: 'Entrepôt C4' },
  { id: 'SM_0015', zone: 'C', type: 'factory',   t:  0.16, d: 0.83, label: 'Usine C5'    },
  // Zone D — Mixte (t centred ≈ 0.46)
  { id: 'SM_0016', zone: 'D', type: 'hospital',  t:  0.36, d: 0.66, label: 'Clinique D1' },
  { id: 'SM_0017', zone: 'D', type: 'school',    t:  0.44, d: 0.66, label: 'École D2'    },
  { id: 'SM_0018', zone: 'D', type: 'house',     t:  0.52, d: 0.66, label: 'Maison D3'   },
  { id: 'SM_0019', zone: 'D', type: 'school',    t:  0.40, d: 0.83, label: 'École D4'    },
  { id: 'SM_0020', zone: 'D', type: 'apartment', t:  0.48, d: 0.83, label: 'Appt D5'     },
];

/* ── Icon drawing helpers ───────────────────────────── */
function iconSun(ctx, x, y, r, col) {
  ctx.fillStyle = col;
  ctx.beginPath(); ctx.arc(x, y, r * 0.45, 0, Math.PI * 2); ctx.fill();
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    ctx.strokeStyle = col; ctx.lineWidth = r * 0.12;
    ctx.beginPath();
    ctx.moveTo(x + Math.cos(a) * r * 0.55, y + Math.sin(a) * r * 0.55);
    ctx.lineTo(x + Math.cos(a) * r * 0.85, y + Math.sin(a) * r * 0.85);
    ctx.stroke();
  }
}
function iconWind(ctx, x, y, r, col) {
  ctx.strokeStyle = col; ctx.lineWidth = r * 0.14; ctx.lineCap = 'round';
  for (let i = 0; i < 3; i++) {
    const cy = y - r * 0.3 + i * r * 0.3;
    ctx.beginPath(); ctx.moveTo(x - r * 0.6, cy); ctx.lineTo(x + r * 0.6, cy); ctx.stroke();
  }
}
function iconFlame(ctx, x, y, r, col) {
  ctx.fillStyle = col;
  ctx.beginPath();
  ctx.moveTo(x, y + r);
  ctx.bezierCurveTo(x - r * 0.6, y + r * 0.4, x - r * 0.5, y - r * 0.4, x, y - r);
  ctx.bezierCurveTo(x + r * 0.2, y - r * 0.2, x + r * 0.5, y + r * 0.3, x + r * 0.5, y + r * 0.5);
  ctx.bezierCurveTo(x + r * 0.3, y + r * 0.8, x + r * 0.2, y + r, x, y + r);
  ctx.fill();
}
function iconDrop(ctx, x, y, r, col) {
  ctx.fillStyle = col;
  ctx.beginPath();
  ctx.moveTo(x, y - r);
  ctx.bezierCurveTo(x + r * 0.7, y - r * 0.2, x + r * 0.6, y + r * 0.6, x, y + r);
  ctx.bezierCurveTo(x - r * 0.6, y + r * 0.6, x - r * 0.7, y - r * 0.2, x, y - r);
  ctx.fill();
}

function drawIcon(ctx, icon, x, y, r, col) {
  switch (icon) {
    case 'sun':   iconSun(ctx, x, y, r, col);   break;
    case 'wind':  iconWind(ctx, x, y, r, col);  break;
    case 'flame': iconFlame(ctx, x, y, r, col); break;
    case 'drop':  iconDrop(ctx, x, y, r, col);  break;
  }
}

/* ── Building icon drawing ──────────────────────────── */
function drawBuilding(ctx, type, cx, by, s, zoneCol, tick, anomAtk) {
  const ac = anomAtk ? (ATK_COLORS[anomAtk] || '#ef4444') : zoneCol;
  const dark = '#0a1628';

  switch (type) {
    case 'house': {
      const w = 22*s, h = 18*s;
      ctx.fillStyle = anomAtk ? '#2a0808' : '#0e2040';
      ctx.fillRect(cx - w/2, by - h, w, h);
      ctx.fillStyle = ac + '99';
      ctx.beginPath();
      ctx.moveTo(cx - w/2 - 2*s, by - h);
      ctx.lineTo(cx, by - h - h*0.6);
      ctx.lineTo(cx + w/2 + 2*s, by - h);
      ctx.closePath(); ctx.fill();
      // windows
      ctx.fillStyle = anomAtk ? '#ef444460' : '#3b82f650';
      ctx.fillRect(cx - w*0.3, by - h*0.65, w*0.22, h*0.22);
      ctx.fillRect(cx + w*0.08, by - h*0.65, w*0.22, h*0.22);
      // door
      ctx.fillStyle = '#1e3a5f';
      ctx.fillRect(cx - w*0.1, by - h*0.4, w*0.2, h*0.4);
      break;
    }
    case 'apartment': {
      const w = 18*s, h = 32*s;
      ctx.fillStyle = anomAtk ? '#2a0808' : '#0d1e3c';
      ctx.fillRect(cx - w/2, by - h, w, h);
      for (let r = 0; r < 4; r++) {
        for (let c = 0; c < 3; c++) {
          ctx.fillStyle = (tick + r*3+c) % 7 !== 0
            ? (anomAtk ? '#ef444440' : '#3b82f640')
            : '#0a1628';
          ctx.fillRect(cx - w*0.38 + c*w*0.33, by - h*0.88 + r*h*0.2, w*0.22, h*0.12);
        }
      }
      break;
    }
    case 'office': {
      const w = 26*s, h = 28*s;
      ctx.fillStyle = anomAtk ? '#1a0a00' : '#08182e';
      ctx.fillRect(cx - w/2, by - h, w, h);
      ctx.fillStyle = anomAtk ? '#f9731620' : '#1d4ed825';
      ctx.fillRect(cx - w*0.38, by - h*0.9, w*0.76, h*0.8);
      for (let r = 0; r < 4; r++) {
        ctx.strokeStyle = anomAtk ? '#f9731615' : '#1e3a5f30';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(cx - w*0.38, by - h*0.9 + r*h*0.2);
        ctx.lineTo(cx + w*0.38, by - h*0.9 + r*h*0.2);
        ctx.stroke();
      }
      break;
    }
    case 'factory': {
      const w = 36*s, h = 22*s;
      ctx.fillStyle = anomAtk ? '#0a1a08' : '#0c1e10';
      ctx.fillRect(cx - w/2, by - h, w, h);
      // chimneys
      const stopped = anomAtk === 'DoS' || anomAtk === 'Fault';
      for (let i = 0; i < 2; i++) {
        const cx2 = cx - w*0.22 + i*w*0.44;
        ctx.fillStyle = '#0e2614';
        ctx.fillRect(cx2 - 4*s, by - h - 14*s, 8*s, 14*s);
        if (!stopped) {
          for (let p = 0; p < 3; p++) {
            const py = ((tick*0.8 + p*20) % 40)*s;
            const pa = 1 - py/(40*s);
            ctx.beginPath();
            ctx.arc(cx2 + Math.sin((tick+p*7)*0.05)*4*s, by - h - 14*s - py, (3+py*0.06)*s, 0, Math.PI*2);
            ctx.fillStyle = `rgba(150,180,140,${pa*0.25})`;
            ctx.fill();
          }
        }
      }
      // gear window
      const ga = tick*0.04*(stopped?0:1);
      drawGearSmall(ctx, cx-6*s, by-h*0.5, 5*s, 7, ga, stopped?'#334':'#06b6d4');
      drawGearSmall(ctx, cx+4*s, by-h*0.5, 3.5*s, 5, -ga*1.4, stopped?'#334':'#3b82f6');
      break;
    }
    case 'warehouse': {
      const w = 38*s, h = 18*s;
      ctx.fillStyle = '#1a1410';
      ctx.fillRect(cx - w/2, by - h, w, h);
      // rolling door
      ctx.fillStyle = '#2a2010';
      ctx.fillRect(cx - w*0.3, by - h*0.75, w*0.6, h*0.65);
      for (let i = 0; i < 5; i++) {
        ctx.strokeStyle = '#3a3020'; ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.moveTo(cx - w*0.3, by - h*0.75 + i*h*0.13);
        ctx.lineTo(cx + w*0.3, by - h*0.75 + i*h*0.13);
        ctx.stroke();
      }
      break;
    }
    case 'hospital': {
      const w = 28*s, h = 26*s;
      ctx.fillStyle = '#0a1825';
      ctx.fillRect(cx - w/2, by - h, w, h);
      ctx.fillStyle = '#ef444490';
      const cs = 5*s;
      ctx.fillRect(cx - cs/2, by - h*0.8, cs, cs*2.5);
      ctx.fillRect(cx - cs*1.2, by - h*0.6, cs*2.4, cs);
      for (let c2 = 0; c2 < 3; c2++) {
        ctx.fillStyle = '#3b82f645';
        ctx.fillRect(cx - w*0.38 + c2*w*0.3, by - h*0.35, w*0.2, h*0.2);
      }
      break;
    }
    case 'school': {
      const w = 30*s, h = 20*s;
      ctx.fillStyle = '#1a1200';
      ctx.fillRect(cx - w/2, by - h, w, h);
      ctx.fillStyle = '#221800';
      ctx.fillRect(cx - 4*s, by - h - 10*s, 8*s, 10*s);
      for (let c2 = 0; c2 < 4; c2++) {
        ctx.fillStyle = '#f59e0b35';
        ctx.fillRect(cx - w*0.42 + c2*w*0.26, by - h*0.7, w*0.18, h*0.35);
      }
      break;
    }
    case 'shop': {
      const w = 22*s, h = 16*s;
      ctx.fillStyle = '#1a0a20';
      ctx.fillRect(cx - w/2, by - h, w, h);
      ctx.fillStyle = '#7c3aed50';
      ctx.fillRect(cx - w*0.52, by - h*0.55, w*1.04, 5*s);
      ctx.fillStyle = '#8b5cf640';
      ctx.fillRect(cx - w*0.38, by - h*0.48, w*0.76, h*0.32);
      break;
    }
  }

  // SM label below building
  ctx.fillStyle = anomAtk ? ac : '#7a95b8';
  ctx.font = `${Math.max(7, Math.round(8*s))}px JetBrains Mono, monospace`;
  ctx.textAlign = 'center';
  ctx.fillText(type === 'factory' ? '🏭' : type === 'hospital' ? '🏥' : type === 'school' ? '🏫' : type === 'shop' ? '🏪' : type === 'warehouse' ? '🏢' : type === 'apartment' ? '🏬' : type === 'office' ? '🏢' : '🏠', cx, by + 10*s);
}

function drawGearSmall(ctx, gx, gy, r, teeth, angle, col) {
  ctx.save(); ctx.translate(gx, gy); ctx.rotate(angle);
  const step = Math.PI*2/teeth;
  ctx.beginPath();
  for (let i = 0; i < teeth; i++) {
    const a = i*step;
    ctx.lineTo(Math.cos(a)*r*0.62, Math.sin(a)*r*0.62);
    ctx.lineTo(Math.cos(a+step*0.25)*(r*1.4), Math.sin(a+step*0.25)*(r*1.4));
    ctx.lineTo(Math.cos(a+step*0.75)*(r*1.4), Math.sin(a+step*0.75)*(r*1.4));
    ctx.lineTo(Math.cos(a+step)*r*0.62, Math.sin(a+step)*r*0.62);
  }
  ctx.closePath(); ctx.fillStyle = col; ctx.fill();
  ctx.beginPath(); ctx.arc(0, 0, r*0.28, 0, Math.PI*2);
  ctx.fillStyle = '#050a14'; ctx.fill();
  ctx.restore();
}

/* ── Draw an animated power line with particles ──────── */
function drawPowerLine(ctx, x1, y1, x2, y2, col, tick, width, pCount, dark, anomaly) {
  // Line
  ctx.strokeStyle = col + (dark ? '50' : '60');
  ctx.lineWidth   = width;
  ctx.setLineDash(anomaly ? [5,5] : []);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  ctx.setLineDash([]);
  // Particles flowing from source to dest
  for (let p = 0; p < pCount; p++) {
    const frac = ((tick * 0.014 + p / pCount) % 1);
    const px = x1 + (x2 - x1) * frac;
    const py = y1 + (y2 - y1) * frac;
    ctx.beginPath();
    ctx.arc(px, py, width * 1.1 + 0.5, 0, Math.PI*2);
    ctx.fillStyle = col + 'dd';
    ctx.fill();
  }
}

/* ── Draw a network node circle ─────────────────────── */
function drawNode(ctx, x, y, r, fillCol, strokeCol, label, sub, dark) {
  // Glow
  const grd = ctx.createRadialGradient(x, y, 0, x, y, r*2);
  grd.addColorStop(0, strokeCol + '25'); grd.addColorStop(1, 'transparent');
  ctx.fillStyle = grd;
  ctx.beginPath(); ctx.arc(x, y, r*2, 0, Math.PI*2); ctx.fill();
  // Circle
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
  ctx.fillStyle = fillCol;
  ctx.fill();
  ctx.strokeStyle = strokeCol;
  ctx.lineWidth = 1.5;
  ctx.stroke();
  // Labels
  if (label) {
    ctx.fillStyle = dark ? '#e2eaf6' : '#0f1923';
    ctx.font = `bold ${Math.round(r*0.55)}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(label, x, y + r + r*0.9);
  }
  if (sub) {
    ctx.fillStyle = strokeCol;
    ctx.font = `${Math.round(r*0.45)}px Inter, sans-serif`;
    ctx.fillText(sub, x, y + r + r*1.6);
  }
}

/* ── Main draw function ──────────────────────────────── */
export function drawFrame(ctx, W, H, tick, anomaly, theme) {
  ctx.clearRect(0, 0, W, H);
  const dark = theme !== 'light';

  // ── Background
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  if (dark) {
    bg.addColorStop(0, '#020810');
    bg.addColorStop(1, '#040c1a');
  } else {
    bg.addColorStop(0, '#cddcee');
    bg.addColorStop(1, '#e0eaf5');
  }
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

  // Subtle grid
  ctx.strokeStyle = dark ? '#0d1e3415' : '#a0b8d018';
  ctx.lineWidth = 0.5;
  for (let i = 0; i < W; i += 40) {
    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, H); ctx.stroke();
  }
  for (let j = 0; j < H; j += 40) {
    ctx.beginPath(); ctx.moveTo(0, j); ctx.lineTo(W, j); ctx.stroke();
  }

  // ── Compute projected positions for all nodes
  const genPos  = {};
  const hvPos   = {};
  const mvPos   = {};
  const bldgPos = {};

  GEN_NODES.forEach(n => { genPos[n.id]  = proj(W, H, n.t, n.d); });
  HV_NODES.forEach(n  => { hvPos[n.id]   = proj(W, H, n.t, n.d); });
  MV_NODES.forEach(n  => { mvPos[n.id]   = proj(W, H, n.t, n.d); });
  BUILDINGS.forEach(b => { bldgPos[b.id] = proj(W, H, b.t, b.d); });

  const anomalyId = anomaly?.meterId;

  // ── Draw connections (back to front) ─────────────────

  // 1. Gen → HV lines (blue, thickest)
  HV_NODES.forEach(hv => {
    const hp = hvPos[hv.id];
    hv.gen.forEach(gId => {
      const gp = genPos[gId];
      drawPowerLine(ctx, gp.x, gp.y, hp.x, hp.y, '#3b82f6', tick, 1.5, 2, dark, false);
    });
  });

  // 2. HV → MV lines (teal)
  MV_NODES.forEach(mv => {
    const hvp = hvPos[mv.hv];
    const mp  = mvPos[mv.id];
    const col = ZONE_COLORS[mv.zone];
    drawPowerLine(ctx, hvp.x, hvp.y, mp.x, mp.y, '#06b6d4', tick, 1.2, 2, dark, false);
  });

  // 3. MV → Building lines (per zone color, thinner)
  BUILDINGS.forEach(b => {
    const mvId = 'mv_' + b.zone;
    const mp   = mvPos[mvId];
    const bp   = bldgPos[b.id];
    const zc   = ZONE_COLORS[b.zone];
    const isAn = b.id === anomalyId;
    const lc   = isAn ? (ATK_COLORS[anomaly.atk] || '#ef4444') : zc;
    drawPowerLine(ctx, mp.x, mp.y, bp.x, bp.y - 10*bp.s, lc, tick, 0.6, isAn ? 3 : 1, dark, isAn);
  });

  // ── Draw zone background halos under buildings
  MV_NODES.forEach(mv => {
    const mp  = mvPos[mv.id];
    const col = ZONE_COLORS[mv.zone];
    const blds = BUILDINGS.filter(b => b.zone === mv.zone);
    const xs  = blds.map(b => bldgPos[b.id].x);
    const ys  = blds.map(b => bldgPos[b.id].y);
    if (xs.length === 0) return;
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const rx = (Math.max(...xs) - Math.min(...xs)) / 2 + 22;
    const ry = (Math.max(...ys) - Math.min(...ys)) / 2 + 20;
    const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(rx, ry) * 1.2);
    grd.addColorStop(0, col + '18');
    grd.addColorStop(1, 'transparent');
    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx * 1.3, ry * 1.2, 0, 0, Math.PI*2);
    ctx.fill();
    // Zone label above buildings
    ctx.fillStyle = col + 'aa';
    ctx.font = `bold ${Math.round(10*mvPos[mv.id].s)}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(`Zone ${mv.zone} • ${ZONE_LABELS[mv.zone]}`, cx, Math.min(...ys) - 14);
  });

  // ── Draw buildings (with anomaly glow)
  BUILDINGS.forEach(b => {
    const bp  = bldgPos[b.id];
    const zc  = ZONE_COLORS[b.zone];
    const isAn = b.id === anomalyId;

    if (isAn) {
      const ac    = ATK_COLORS[anomaly.atk] || '#ef4444';
      const pulse = 0.5 + 0.5 * Math.sin(tick * 0.14);
      const grad  = ctx.createRadialGradient(bp.x, bp.y, 0, bp.x, bp.y, 45*bp.s);
      grad.addColorStop(0, ac + Math.round(100*pulse).toString(16).padStart(2,'0'));
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.fillRect(bp.x - 50*bp.s, bp.y - 50*bp.s, 100*bp.s, 70*bp.s);
      // Pulsing ring
      ctx.strokeStyle = ac;
      ctx.lineWidth   = 2;
      ctx.globalAlpha = 0.6 * pulse;
      ctx.beginPath();
      ctx.arc(bp.x, bp.y - 10*bp.s, 22*bp.s + pulse*8, 0, Math.PI*2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    drawBuilding(ctx, b.type, bp.x, bp.y, bp.s, zc, tick, isAn ? anomaly.atk : null);

    // SM ID label
    ctx.fillStyle = isAn ? (ATK_COLORS[anomaly.atk] || '#ef4444') : (dark ? '#3d5a82' : '#7a95b8');
    ctx.font = `${Math.max(6, Math.round(7*bp.s))}px JetBrains Mono, monospace`;
    ctx.textAlign = 'center';
    ctx.fillText(b.id.replace('SM_0', ''), bp.x, bp.y + 20*bp.s);
  });

  // ── Draw MV zone nodes
  MV_NODES.forEach(mv => {
    const mp  = mvPos[mv.id];
    const col = ZONE_COLORS[mv.zone];
    const r   = 13 * mp.s;
    drawNode(ctx, mp.x, mp.y, r, dark ? '#0b1428' : '#ffffff', col,
      `Zone ${mv.zone}`, `MV 20 kV`, dark);
  });

  // ── Draw HV substation nodes
  HV_NODES.forEach(hv => {
    const hp = hvPos[hv.id];
    const r  = 18 * hp.s;
    drawNode(ctx, hp.x, hp.y, r, dark ? '#081428' : '#f0f5fa', '#06b6d4',
      hv.label, hv.sub, dark);
  });

  // ── Draw Generation nodes
  GEN_NODES.forEach(n => {
    const gp = genPos[n.id];
    const r  = 14 * gp.s;
    // Outer ring
    ctx.beginPath(); ctx.arc(gp.x, gp.y, r, 0, Math.PI*2);
    ctx.fillStyle = dark ? '#070e1c' : '#f8fafc';
    ctx.fill();
    ctx.strokeStyle = n.col; ctx.lineWidth = 1.5; ctx.stroke();
    // Icon inside
    drawIcon(ctx, n.icon, gp.x, gp.y, r * 0.52, n.col);
    // Labels
    ctx.fillStyle = dark ? '#e2eaf6' : '#0f1923';
    ctx.font = `bold ${Math.round(r*0.52)}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(n.label, gp.x, gp.y + r + r*0.9);
    ctx.fillStyle = n.col;
    ctx.font = `${Math.round(r*0.42)}px Inter, sans-serif`;
    ctx.fillText(n.sub, gp.x, gp.y + r + r*1.65);
  });

  // ── Bottom legend bar
  const legendY = H - 14;
  const items = [
    { col: '#3b82f6', label: 'HV 225 kV' },
    { col: '#06b6d4', label: 'MV 20 kV'  },
    { col: '#ffffff', label: 'LV Compteurs'},
  ];
  ctx.fillStyle = dark ? '#0b142888' : '#ffffff88';
  ctx.fillRect(0, H - 28, W, 28);
  ctx.fillStyle = dark ? '#7a95b8' : '#344a62';
  ctx.font = '10px Inter, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('FLUX', 12, legendY + 2);
  let lx = 52;
  items.forEach(it => {
    ctx.beginPath(); ctx.arc(lx, legendY, 4, 0, Math.PI*2);
    ctx.fillStyle = it.col; ctx.fill();
    ctx.fillStyle = dark ? '#7a95b8' : '#344a62';
    ctx.fillText(it.label, lx + 8, legendY + 3);
    lx += ctx.measureText(it.label).width + 26;
  });
}

/* ── Hit-test: return building at click (x, y) ──────── */
export function hitBuilding(W, H, x, y) {
  for (const b of BUILDINGS) {
    const bp = proj(W, H, b.t, b.d);
    const r  = 24 * bp.s;
    if (Math.abs(x - bp.x) < r && Math.abs(y - bp.y) < r) return b;
  }
  return null;
}

/* ── Device detail for popup ─────────────────────────── */
export function buildDetail(atk) {
  const DEVICES = {
    FDIA: [
      { icon:'⚡', name:'Compteur',    val:'14.2 kW', status:'error',  pw:90,  anomaly:true  },
      { icon:'🌡️', name:'Thermostat', val:'47 °C',   status:'error',  pw:95,  anomaly:true  },
      { icon:'❄️', name:'Clim.',       val:'30.5 kW', status:'warning',pw:80,  anomaly:true  },
      { icon:'💡', name:'Éclairage',   val:'0.6 kW',  status:'normal', pw:15                 },
      { icon:'📺', name:'TV',          val:'0.2 kW',  status:'normal', pw:10                 },
      { icon:'🫙', name:'Réfrigér.',   val:'0.15 kW', status:'normal', pw:8                  },
      { icon:'🔌', name:'Prise',       val:'1.1 kW',  status:'normal', pw:28                 },
      { icon:'📡', name:'Hub IoT',     val:'ALERTE',  status:'warning',pw:70,  anomaly:true  },
      { icon:'📱', name:'Alerte',      val:'FDIA!',   status:'error',  pw:100, anomaly:true  },
    ],
    DoS: [
      { icon:'⚡', name:'Compteur',    val:'0 kW',    status:'offline',pw:0,   anomaly:true  },
      { icon:'🌡️', name:'Thermostat', val:'—',       status:'offline',pw:0                  },
      { icon:'❄️', name:'Clim.',       val:'—',       status:'offline',pw:0                  },
      { icon:'💡', name:'Éclairage',   val:'—',       status:'offline',pw:0                  },
      { icon:'📺', name:'TV',          val:'—',       status:'offline',pw:0                  },
      { icon:'🫙', name:'Réfrigér.',   val:'—',       status:'offline',pw:0                  },
      { icon:'📡', name:'Hub IoT',     val:'HORS L.', status:'offline',pw:0,   anomaly:true  },
      { icon:'📱', name:'Alerte',      val:'DoS!',    status:'error',  pw:100, anomaly:true  },
    ],
    Fraud: [
      { icon:'⚡', name:'Compteur',    val:'1.1 kW',  status:'warning',pw:8,   anomaly:true  },
      { icon:'🔌', name:'Dérivation',  val:'+7.3 kW', status:'error',  pw:85,  anomaly:true  },
      { icon:'🌡️', name:'Thermostat', val:'22 °C',   status:'normal', pw:30                 },
      { icon:'❄️', name:'Clim.',       val:'3.5 kW',  status:'normal', pw:45                 },
      { icon:'💡', name:'Éclairage',   val:'0.5 kW',  status:'normal', pw:12                 },
      { icon:'📡', name:'Hub IoT',     val:'ALERTE',  status:'warning',pw:70,  anomaly:true  },
      { icon:'📱', name:'Alerte',      val:'Fraude!', status:'error',  pw:100, anomaly:true  },
    ],
    Fault: [
      { icon:'⚡', name:'Compteur',    val:'ERR',     status:'error',  pw:0,   anomaly:true  },
      { icon:'⚙️', name:'Machine',    val:'SURCH.',  status:'error',  pw:100, anomaly:true  },
      { icon:'🌡️', name:'Capteur',    val:'92 °C',   status:'error',  pw:98,  anomaly:true  },
      { icon:'🔧', name:'Moteur',      val:'KO',      status:'error',  pw:0,   anomaly:true  },
      { icon:'💡', name:'Éclairage',   val:'Urgence', status:'warning',pw:100                },
      { icon:'📡', name:'Hub IoT',     val:'ALERTE',  status:'warning',pw:80,  anomaly:true  },
      { icon:'🚨', name:'Alarme',      val:'ACTIVE',  status:'error',  pw:100, anomaly:true  },
    ],
    normal: [
      { icon:'⚡', name:'Compteur',    val:'2.4 kW',  status:'normal', pw:35                 },
      { icon:'🌡️', name:'Thermostat', val:'22 °C',   status:'normal', pw:30                 },
      { icon:'❄️', name:'Clim.',       val:'1.2 kW',  status:'normal', pw:25                 },
      { icon:'💡', name:'Éclairage',   val:'0.4 kW',  status:'normal', pw:10                 },
      { icon:'📺', name:'TV',          val:'0.15 kW', status:'normal', pw:8                  },
      { icon:'🫙', name:'Réfrigér.',   val:'0.12 kW', status:'normal', pw:7                  },
      { icon:'📡', name:'Hub IoT',     val:'OK',      status:'normal', pw:5                  },
      { icon:'📱', name:'Tel',         val:'Normal',  status:'normal', pw:3                  },
    ],
  };
  return DEVICES[atk] || DEVICES.normal;
}
