import { useState, useEffect, useRef } from 'react';
import './index.css';
import {
  drawFrame, hitBuilding, buildDetail,
  BUILDINGS, ZONE_COLORS, ATK_COLORS, ZONE_LABELS,
  GEN_NODES, HV_NODES, MV_NODES,
} from './canvasEngine';
import {
  checkBackend, getBlockchainStatus, detectAnomaly,
  makeReading, ATTACK_READINGS,
} from './api';

/* ── Seed alerts (match Claude Design — with score/conf) ── */
const SEED_ALERTS = [
  { id: 1, atk: 'FDIA',  meterId: 'SM_0003', zone: 'A', time: '02:43:19', score: 0.01428, conf: 100 },
  { id: 2, atk: 'Fraud', meterId: 'SM_0012', zone: 'C', time: '14:21:08', score: 0.00890, conf: 96  },
  { id: 3, atk: 'DoS',   meterId: 'SM_0007', zone: 'B', time: '14:18:55', score: 0.00210, conf: 98  },
  { id: 4, atk: 'Fault', meterId: 'SM_0018', zone: 'D', time: '14:15:33', score: 0.00150, conf: 88  },
];

const DEMO_STEPS = [
  { title: 'Réseau Normal',           desc: 'Tous les compteurs opérationnels — flux nominal' },
  { title: 'Injection FDIA',          desc: 'SM_0003 : données falsifiées détectées par IA' },
  { title: 'Attaque DoS',             desc: 'SM_0006 : coupure de communication, timeout capteur' },
  { title: "Vol d'Énergie (Fraud)",   desc: 'SM_0011 : consommation sous-déclarée, dérivation +7.3 kW' },
  { title: 'Notarisation Blockchain', desc: 'Anomalies hashées et validées par 4 nœuds PoA' },
];

const XAI_FEATURES = [
  { label: 'Consommation kW', pct: 92, color: '#ef4444' },
  { label: 'Tension V',       pct: 78, color: '#f97316' },
  { label: 'Courant A',       pct: 65, color: '#f59e0b' },
  { label: 'Power Factor',    pct: 54, color: '#8b5cf6' },
  { label: 'Heure (sin)',     pct: 41, color: '#3b82f6' },
  { label: 'Heure (cos)',     pct: 38, color: '#10b981' },
];

const MODEL_METRICS = [
  { label: 'AUC-ROC',   value: '97.95%', pct: 97.95 },
  { label: 'Précision', value: '99.84%', pct: 99.84 },
  { label: 'Rappel',    value: '75.43%', pct: 75.43 },
  { label: 'F1-Score',  value: '85.93%', pct: 85.93 },
];

let _alertId = 10;
function makeAlert(atk, meterId, zone, score, conf) {
  return {
    id: ++_alertId, atk, meterId, zone,
    score: score ?? (0.001 + Math.random() * 0.02),
    conf:  conf  ?? Math.round(85 + Math.random() * 14),
    time: new Date().toLocaleTimeString('fr-FR', { hour:'2-digit', minute:'2-digit', second:'2-digit' }),
  };
}

/* ── Alert card component ──────────────────────────────── */
function AlertCard({ a }) {
  const col = ATK_COLORS[a.atk] || '#ef4444';
  return (
    <div className={`alert-card ${a.atk}`}>
      <div className="alert-head">
        <span className={`alert-type ${a.atk}`}>{a.atk}</span>
        <span className="alert-time">{a.time}</span>
      </div>
      <div className="alert-meter">{a.meterId}</div>
      <div className="alert-zone">Zone {a.zone} — {ZONE_LABELS[a.zone]}</div>
      <div className="alert-score">Score <span style={{ fontFamily:'JetBrains Mono,monospace', color: col }}>{a.score.toFixed(5)}</span></div>
      <div className="alert-conf-wrap">
        <div className="alert-conf-bar">
          <div className="alert-conf-fill" style={{ width:`${a.conf}%`, background: col }}/>
        </div>
        <span className="alert-conf-pct" style={{ color: col }}>{a.conf}% conf.</span>
      </div>
    </div>
  );
}

export default function App() {
  const [theme,       setTheme]      = useState('dark');
  const [activeTab,   setActiveTab]  = useState('alerts');
  const [alerts,      setAlerts]     = useState(SEED_ALERTS);
  const [anomaly,     setAnomaly]    = useState(null);
  const [popupMeter,  setPopupMeter] = useState(null);
  const [demoOpen,    setDemoOpen]   = useState(false);
  const [reportOpen,  setReportOpen] = useState(false);
  const [demoStep,    setDemoStep]   = useState(0);
  const [demoRunning, setDemoRunning]= useState(false);
  const [blocks,      setBlocks]     = useState(18);
  const [clock,       setClock]      = useState('');
  const [backendOk,   setBackendOk]  = useState(null);
  const [modelActive, setModelActive]= useState(true);

  const canvasRef   = useRef(null);
  const frameRef    = useRef(0);
  const rafRef      = useRef(null);
  const anomalyRef  = useRef(null);
  const themeRef    = useRef('dark');
  const demoTimers  = useRef([]);
  const backendRef  = useRef(false);
  const autoFeedRef = useRef(null);
  const bcPollRef   = useRef(null);
  const meterIdxRef = useRef(0);
  const gotRealAnom = useRef(false);

  /* ── Theme ── */
  useEffect(() => {
    document.documentElement.setAttribute('data-th', theme);
    themeRef.current = theme;
  }, [theme]);

  /* ── Clock ── */
  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('fr-FR', { hour:'2-digit', minute:'2-digit', second:'2-digit' }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  /* ── Canvas loop ── */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    const loop = () => {
      frameRef.current++;
      drawFrame(ctx, canvas.width, canvas.height, frameRef.current, anomalyRef.current, themeRef.current);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(rafRef.current); ro.disconnect(); };
  }, []);

  useEffect(() => { anomalyRef.current = anomaly; }, [anomaly]);

  /* ── Backend ── */
  useEffect(() => {
    initBackend();
    const t = setTimeout(() => {
      if (!gotRealAnom.current) triggerAnomaly('FDIA', 'SM_0003', 'A', 0.01428, 100);
    }, 3500);
    return () => {
      clearTimeout(t);
      clearInterval(autoFeedRef.current);
      clearInterval(bcPollRef.current);
    };
  }, []);

  async function initBackend() {
    try {
      const st = await checkBackend();
      backendRef.current = true;
      setBackendOk(true);
      if (st?.blockchain?.blocks) setBlocks(st.blockchain.blocks);
    } catch { setBackendOk(false); }
    autoFeedRef.current = setInterval(autoFeedTick, 500);
    bcPollRef.current   = setInterval(pollBlockchain, 10000);
  }

  async function autoFeedTick() {
    if (!backendRef.current) return;
    const b = BUILDINGS[meterIdxRef.current % BUILDINGS.length];
    meterIdxRef.current++;
    try {
      const res = await detectAnomaly(makeReading(b.id, b.zone, b.type));
      if (res.is_anomaly && !res.deduplicated) {
        gotRealAnom.current = true;
        const map = { fdia:'FDIA', dos:'DoS', fraud:'Fraud', fault:'Fault' };
        triggerAnomaly(map[res.attack_type?.toLowerCase()]||'FDIA', b.id, b.zone,
          res.anomaly_score, Math.round((res.confidence||0.9)*100));
        if (res.blockchain_blocks) setBlocks(res.blockchain_blocks);
      }
    } catch { /* ignore */ }
  }

  async function pollBlockchain() {
    try {
      const d = await getBlockchainStatus();
      if (d.blocks !== undefined) setBlocks(d.blocks);
    } catch { /* ignore */ }
  }

  async function sendAttack(atk, meterId, zone, type) {
    if (!backendRef.current) return;
    try {
      const res = await detectAnomaly(makeReading(meterId, zone, type, ATTACK_READINGS[atk]||{}));
      if (res.blockchain_blocks) setBlocks(res.blockchain_blocks);
    } catch { /* ignore */ }
  }

  function triggerAnomaly(atk, meterId, zone, score, conf) {
    setAnomaly({ atk, meterId, zone });
    setAlerts(prev => [makeAlert(atk, meterId, zone, score, conf), ...prev].slice(0, 30));
    setActiveTab('alerts');
  }
  function clearAnomaly() { setAnomaly(null); }

  function handleCanvasClick(e) {
    const cv = canvasRef.current;
    if (!cv) return;
    const rect = cv.getBoundingClientRect();
    const hit = hitBuilding(cv.width, cv.height, e.clientX - rect.left, e.clientY - rect.top);
    if (hit) setPopupMeter(hit);
  }

  function runDemo() {
    stopDemo();
    setDemoOpen(true);
    setDemoRunning(true);
    setDemoStep(1);
    const seq = [
      () => clearAnomaly(),
      () => { triggerAnomaly('FDIA', 'SM_0003','A',0.01428,100); sendAttack('FDIA','SM_0003','A','house'); },
      () => { triggerAnomaly('DoS',  'SM_0006','B',0.00210,98);  sendAttack('DoS', 'SM_0006','B','shop');  },
      () => { triggerAnomaly('Fraud','SM_0011','C',0.00890,96);  sendAttack('Fraud','SM_0011','C','factory'); },
      () => { clearAnomaly(); setBlocks(b => b+3); setDemoRunning(false); },
    ];
    const delays = [0, 3000, 6000, 9000, 13000];
    seq.forEach((fn, i) => {
      const t = setTimeout(() => { setDemoStep(i+1); fn(); }, delays[i]);
      demoTimers.current.push(t);
    });
  }
  function stopDemo() {
    demoTimers.current.forEach(clearTimeout);
    demoTimers.current = [];
    setDemoRunning(false);
    setDemoStep(0);
  }

  const popupDevices = popupMeter
    ? buildDetail(anomaly?.meterId === popupMeter?.id ? anomaly.atk : 'normal')
    : [];

  const anomalyColor = anomaly ? (ATK_COLORS[anomaly.atk] || '#ef4444') : '#ef4444';

  return (
    <div className="shell">

      {/* ══ HEADER ══ */}
      <header className="header">
        {/* Logo + subtitle */}
        <div className="header-brand">
          <div className="header-logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" stroke="#3b82f6" strokeWidth="1.8" fill="none"/>
              <polygon points="14,7 21,11 21,17 14,21 7,17 7,11" stroke="#3b82f6" strokeWidth="1" fill="none" strokeOpacity=".4"/>
              <circle cx="14" cy="14" r="3.5" fill="#3b82f6"/>
              <line x1="14" y1="2"  x2="14" y2="10"  stroke="#3b82f6" strokeWidth="1.4"/>
              <line x1="14" y1="18" x2="14" y2="26"  stroke="#3b82f6" strokeWidth="1.4"/>
              <line x1="2"  y1="8"  x2="9"  y2="12"  stroke="#3b82f6" strokeWidth="1.4"/>
              <line x1="19" y1="16" x2="26" y2="20"  stroke="#3b82f6" strokeWidth="1.4"/>
            </svg>
            <div>
              <div style={{ fontWeight:700, fontSize:14, letterSpacing:'.02em' }}>
                Smart <span className="logo-dot">Grid</span> SCADA
              </div>
              <div style={{ fontSize:9, color:'var(--tx3)', letterSpacing:'.04em', marginTop:1 }}>
                Réseau Intelligent · IA Transformer · Blockchain PoA · IoT Maison
              </div>
            </div>
          </div>
        </div>

        {/* Status badges */}
        <div style={{ display:'flex', gap:6, alignItems:'center', marginLeft:12 }}>
          <span className={`badge${modelActive ? ' ok' : ''}`}>
            <span className="live-dot"/>
            Modèle Actif
          </span>
          <span className="badge" style={{ color:'#f59e0b', borderColor:'#f59e0b' }}>
            AUC 97.95%
          </span>
          <span className="badge" style={{ color:'#06b6d4', borderColor:'#06b6d4' }}>
            ⛓ PoA · {blocks} blocs
          </span>
          {alerts.length > 0 && (
            <span className="badge err">
              <span className="live-dot" style={{ color:'#ef4444' }}/>
              {alerts.length} Alertes
            </span>
          )}
        </div>

        <div className="header-sep"/>

        {/* Right actions */}
        <div style={{ display:'flex', gap:6, alignItems:'center' }}>
          {anomaly && (
            <span className="badge err" style={{ fontSize:11 }}>
              <span className="live-dot" style={{ color:'#ef4444' }}/>
              {anomaly.atk} — {anomaly.meterId}
            </span>
          )}
          <div className="clock">{clock}</div>

          {/* Démo button */}
          <button
            className="hdr-btn demo-btn"
            onClick={demoRunning ? stopDemo : runDemo}
            title="Scénario de démonstration"
          >
            {demoRunning ? '⏹' : '▶'} Démo
          </button>

          {/* Rapport button */}
          <button className="hdr-btn report-btn" onClick={() => setReportOpen(true)} title="Rapport du modèle">
            📊 Rapport
          </button>

          <button className="icon-btn" title="Thème" onClick={() => setTheme(t => t==='dark'?'light':'dark')}>
            {theme==='dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      {/* ══ CANVAS ══ */}
      <main className="canvas-wrap">
        <canvas
          ref={canvasRef}
          className="grid-canvas"
          style={{ cursor:'pointer' }}
          onClick={handleCanvasClick}
        />

        {/* Anomaly banner */}
        {anomaly && (
          <div className="anomaly-banner">
            <span className="banner-dot" style={{ background: anomalyColor }}/>
            <span className="banner-label">{anomaly.atk} détecté</span>
            <span className="banner-meta"> — {anomaly.meterId} · Zone {anomaly.zone}</span>
            <button className="banner-clear" onClick={clearAnomaly}>✕</button>
          </div>
        )}

        {/* Backend status */}
        <div style={{ position:'absolute', top:10, right:12, display:'flex', alignItems:'center', gap:5, fontSize:10, color:'var(--tx3)', fontWeight:600 }}>
          <span style={{ width:6, height:6, borderRadius:'50%', background: backendOk===null?'#f59e0b':backendOk?'#10b981':'#ef4444', display:'inline-block', animation: backendOk===null?'blink-dot 1s ease-in-out infinite':'' }}/>
          {backendOk===null ? 'Connexion…' : backendOk ? 'API connectée' : 'Mode Démo'}
        </div>
      </main>

      {/* ══ SIDEBAR ══ */}
      <aside className="sidebar">
        <div className="sidebar-tabs">
          {[
            { key:'alerts', label:`⚠ ALERTES${alerts.length?` (${alerts.length})`:''}`  },
            { key:'stats',  label:'📈 STATS'  },
            { key:'xai',    label:'🧠 XAI'    },
          ].map(t => (
            <button key={t.key} className={`tab-btn${activeTab===t.key?' active':''}`} onClick={() => setActiveTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="sidebar-body">

          {/* ── Alerts tab ── */}
          {activeTab==='alerts' && (
            alerts.length===0
              ? <div style={{ color:'var(--tx3)', textAlign:'center', padding:'20px 0', fontSize:12 }}>Aucune alerte</div>
              : alerts.map(a => <AlertCard key={a.id} a={a}/>)
          )}

          {/* ── Stats tab ── */}
          {activeTab==='stats' && (<>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="stat-label">Anomalies</div>
                <div className="stat-value">{alerts.length}</div>
                <div className="stat-sub">total détecté</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Blocs PoA</div>
                <div className="stat-value">{blocks}</div>
                <div className="stat-sub">notarisés</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">AUC-ROC</div>
                <div className="stat-value" style={{ color:'var(--ac)', fontSize:16 }}>97.95%</div>
                <div className="stat-sub">modèle v2</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">F1-Score</div>
                <div className="stat-value" style={{ color:'#10b981', fontSize:16 }}>85.93%</div>
                <div className="stat-sub">champion</div>
              </div>
            </div>

            <div className="section-hd">Métriques Modèle</div>
            {MODEL_METRICS.map(m => (
              <div key={m.label} className="metric-row">
                <span className="metric-label">{m.label}</span>
                <div className="metric-bar-wrap">
                  <div className="metric-bar" style={{ width:`${m.pct}%` }}/>
                </div>
                <span className="metric-val">{m.value}</span>
              </div>
            ))}

            <div className="section-hd" style={{ marginTop:8 }}>Distribution</div>
            {['FDIA','DoS','Fraud','Fault'].map(atk => {
              const col = ATK_COLORS[atk];
              const cnt = alerts.filter(a=>a.atk===atk).length;
              return (
                <div key={atk} className="metric-row">
                  <span className="metric-label">{atk}</span>
                  <div className="metric-bar-wrap">
                    <div className="metric-bar" style={{ width:`${alerts.length?(cnt/alerts.length)*100:0}%`, background:col }}/>
                  </div>
                  <span className="metric-val">{cnt}</span>
                </div>
              );
            })}
          </>)}

          {/* ── XAI tab ── */}
          {activeTab==='xai' && (<>
            <div className="xai-title">
              {anomaly ? `Attribution SHAP — ${anomaly.atk}` : 'Importance des Features'}
            </div>
            {XAI_FEATURES.map(f => (
              <div key={f.label} className="xai-row">
                <span className="xai-feat">{f.label}</span>
                <div className="xai-bar-bg">
                  <div className="xai-bar" style={{ width:`${anomaly?f.pct:Math.round(f.pct*0.4)}%`, background:f.color }}/>
                </div>
                <span className="xai-pct">{anomaly?f.pct:Math.round(f.pct*0.4)}%</span>
              </div>
            ))}
            {anomaly && (<>
              <div className="section-hd" style={{ marginTop:8 }}>Détection</div>
              {[
                ['Type',      anomaly.atk,  ATK_COLORS[anomaly.atk]],
                ['Compteur',  anomaly.meterId],
                ['Zone',      `${anomaly.zone} — ${ZONE_LABELS[anomaly.zone]}`],
                ['Seuil',     '0.00035'],
              ].map(([k,v,c]) => (
                <div key={k} className="metric-row">
                  <span className="metric-label">{k}</span>
                  <span className="metric-val" style={c?{color:c}:{}}>{v}</span>
                </div>
              ))}
            </>)}
          </>)}
        </div>

        <div className="action-row">
          <button className="btn" onClick={() => { clearAnomaly(); stopDemo(); }}>Effacer</button>
          <button className="btn primary" onClick={demoRunning ? stopDemo : runDemo}>
            {demoRunning ? '⏹ Stop' : '▶ Scénario'}
          </button>
        </div>
      </aside>

      {/* ══ METER POPUP ══ */}
      {popupMeter && (
        <div className="popup-overlay" onClick={e => { if(e.target===e.currentTarget) setPopupMeter(null); }}>
          <div className="popup">
            <div className="popup-head">
              <div className="popup-title">
                {popupMeter.label}
                {anomaly?.meterId===popupMeter.id && (
                  <span style={{ marginLeft:8, fontSize:10, background:ATK_COLORS[anomaly.atk]+'22', color:ATK_COLORS[anomaly.atk], padding:'2px 8px', borderRadius:10, fontWeight:700 }}>
                    {anomaly.atk}
                  </span>
                )}
              </div>
              <div className="popup-meta">
                {popupMeter.id} · Zone {popupMeter.zone} ({ZONE_LABELS[popupMeter.zone]}) · {popupMeter.type}
              </div>
            </div>
            <div className="popup-body">
              {popupDevices.map((d, i) => (
                <div key={i} className={`dev-card${d.anomaly?' anomaly':''}`}>
                  <span className="dev-icon">{d.icon}</span>
                  <div className="dev-name">{d.name}</div>
                  <div className="dev-val">{d.val}</div>
                  <span className={`dev-status ${d.status}`}>{d.status}</span>
                  <div className="dev-pw"><div className="dev-pw-fill" style={{ width:`${d.pw}%` }}/></div>
                </div>
              ))}
            </div>
            <button className="popup-close" onClick={() => setPopupMeter(null)}>✕</button>
          </div>
        </div>
      )}

      {/* ══ DEMO MODAL ══ */}
      {demoOpen && (
        <div className="overlay" onClick={e => { if(e.target===e.currentTarget){setDemoOpen(false);stopDemo();}}}>
          <div className="modal">
            <button className="modal-close" onClick={() => { setDemoOpen(false); stopDemo(); }}>✕</button>
            <div className="modal-title">🎬 Scénario de Démonstration</div>
            <div className="modal-sub">Simulation d'un cycle complet d'attaques sur le réseau intelligent</div>
            <div className="demo-steps">
              {DEMO_STEPS.map((s,i) => (
                <div key={i} className={`demo-step${demoStep===i+1?' active':demoStep>i+1?' done':''}`}>
                  <div className="step-num">{demoStep>i+1?'✓':i+1}</div>
                  <div className="step-body">
                    <div className="step-title">{s.title}</div>
                    <div className="step-desc">{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display:'flex', gap:8 }}>
              <button className="btn" style={{ flex:1 }} onClick={() => { setDemoOpen(false); stopDemo(); }}>Fermer</button>
              <button className="btn primary" style={{ flex:1 }} onClick={demoRunning?stopDemo:runDemo}>
                {demoRunning?'⏹ Arrêter':'▶ Relancer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══ REPORT MODAL ══ */}
      {reportOpen && (
        <div className="overlay" onClick={e => { if(e.target===e.currentTarget) setReportOpen(false); }}>
          <div className="modal">
            <button className="modal-close" onClick={() => setReportOpen(false)}>✕</button>
            <div className="modal-title">📊 Rapport — Transformer Autoencoder</div>
            <div className="modal-sub">Version Champion v2 · PFE 2026 · Aziz Abidi</div>
            <div className="report-grid">
              {MODEL_METRICS.map(m => (
                <div key={m.label} className="report-card">
                  <div className="report-val">{m.value}</div>
                  <div className="report-label">{m.label}</div>
                </div>
              ))}
            </div>
            {MODEL_METRICS.map(m => (
              <div key={m.label} className="report-bar-row">
                <div className="report-bar-label"><span>{m.label}</span><span>{m.value}</span></div>
                <div className="report-bar-bg"><div className="report-bar-fill" style={{ width:`${m.pct}%` }}/></div>
              </div>
            ))}
            <div className="section-hd" style={{ marginTop:12 }}>Historique des Versions</div>
            <table className="version-table">
              <thead><tr><th>Version</th><th>AUC</th><th>F1</th><th>Seuil</th></tr></thead>
              <tbody>
                <tr><td>v1</td><td>91.2%</td><td>72.1%</td><td>0.00050</td></tr>
                <tr className="champion-row">
                  <td>v2<span className="champion-badge">★ Champion</span></td>
                  <td>97.95%</td><td>85.93%</td><td>0.00035</td>
                </tr>
                <tr><td>v3-exp</td><td>94.1%</td><td>81.4%</td><td>0.00042</td></tr>
              </tbody>
            </table>
            <div className="section-hd" style={{ marginTop:12 }}>Architecture</div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:4 }}>
              {[['Modèle','Transformer Autoencoder'],['Dim.','128'],['Couches','3'],['Têtes','4 (multi-head)'],
                ['Séquence','12 lectures'],['Features','15 colonnes'],['Blockchain','Proof of Authority'],['Nœuds','4 validateurs']
              ].map(([k,v]) => (
                <div key={k} className="metric-row" style={{ padding:'4px 0' }}>
                  <span className="metric-label">{k}</span>
                  <span className="metric-val" style={{ fontSize:11 }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
