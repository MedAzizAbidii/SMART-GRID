"""
scenario_test.py — Attack-scenario test harness for the anomaly detector.

Answers the question: "does the model actually catch every attack type,
and how fast?" Feeds hand-built reading sequences (warm-up normal +
attack burst + recovery) through the live EnsembleDetector for one
representative meter per consumer type, then reports per-attack-type
recall, false-positive rate on pure-normal streams, and detection latency
(ticks from attack start to first alarm).

Usage (from smartgrid_simulation/, ML venv):
    .\.venv\Scripts\python.exe scenario_test.py
    .\.venv\Scripts\python.exe scenario_test.py --v2 outputs/scenario_test_v3 --v3 outputs/scenario_test_v2
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SIM_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from ml_pipeline.realtime_detector import RealtimeDetector, EnsembleDetector, _load_single
from smart_meters_simulator import _make_row, _inject, CYBER_TYPES, FRAUD_TYPES, ATTACK_TYPES, _ZONE_OF

SEQ_WARMUP = 12   # normal readings before the attack (>= seq_len=8, buffer settle)
RECOVERY   = 6    # normal readings after the attack, to see the alarm clear


def build_ensemble(v2_dir: str, v3_dir: str):
    base = ROOT
    v2 = _load_single(base, v2_dir)
    v3 = _load_single(base, v3_dir)
    if v2 is None or v3 is None:
        raise SystemExit(f"Could not load models from {v2_dir} / {v3_dir}")
    return EnsembleDetector(detector_v2=v2, detector_v3=v3)


def seed_zone_peers(detector, mid_idx: int, rng: np.random.Generator, ts: datetime | None = None) -> None:
    """Feed one normal reading from a few same-zone peer meters through the
    detector so the shared cross-meter zone aggregator (see ZoneAggregator in
    realtime_detector.py) reflects a realistic mix, exactly as it would in a
    real deployment where all 50 meters stream through the same detector.
    """
    ts = ts or datetime(2026, 7, 1, 7, 0, 0)
    zone = _ZONE_OF[mid_idx]
    peers = [i for i, z in _ZONE_OF.items() if z == zone and i != mid_idx][:4]
    for peer_idx in peers:
        detector.ingest(_make_row(peer_idx, ts, rng))


def make_scenario(mid_idx: int, attack_type: str, burst_len: int, rng: np.random.Generator):
    """Return list of reading dicts: warmup normal -> attack burst -> recovery."""
    ts = datetime(2026, 7, 1, 8, 0, 0)
    rows = []
    for _ in range(SEQ_WARMUP):
        rows.append(("normal", _make_row(mid_idx, ts, rng)))
        ts += timedelta(minutes=2)
    for _ in range(burst_len):
        base_row = _make_row(mid_idx, ts, rng)
        rows.append(("attack", _inject(attack_type, base_row, rng)))
        ts += timedelta(minutes=2)
    for _ in range(RECOVERY):
        rows.append(("normal", _make_row(mid_idx, ts, rng)))
        ts += timedelta(minutes=2)
    return rows


def run_scenario(detector, mid_idx: int, attack_type: str, burst_len: int, rng: np.random.Generator) -> dict:
    seed_zone_peers(detector, mid_idx, rng)
    rows = make_scenario(mid_idx, attack_type, burst_len, rng)
    detected_at = None
    any_detected_during_attack = False
    fp_during_warmup = 0
    attack_start_tick = SEQ_WARMUP

    for i, (phase, reading) in enumerate(rows):
        result = detector.ingest(reading)
        is_anom = bool(result.get("is_anomaly", False))
        if phase == "normal" and i < SEQ_WARMUP and is_anom:
            fp_during_warmup += 1
        if phase == "attack" and is_anom:
            any_detected_during_attack = True
            if detected_at is None:
                detected_at = i - attack_start_tick   # ticks after burst start

    return {
        "attack_type": attack_type,
        "detected": any_detected_during_attack,
        "latency_ticks": detected_at,
        "fp_during_warmup": fp_during_warmup,
    }


def run_normal_stress(detector, mid_idx: int, n_ticks: int, rng: np.random.Generator) -> dict:
    """Feed pure-normal traffic; count false alarms."""
    seed_zone_peers(detector, mid_idx, rng, ts=datetime(2026, 7, 2, 0, 0, 0))
    ts = datetime(2026, 7, 2, 0, 0, 0)
    false_alarms = 0
    for _ in range(n_ticks):
        reading = _make_row(mid_idx, ts, rng)
        result = detector.ingest(reading)
        if result.get("is_anomaly", False):
            false_alarms += 1
        ts += timedelta(minutes=2)
    return {"n_ticks": n_ticks, "false_alarms": false_alarms,
            "fpr": false_alarms / n_ticks if n_ticks else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", default="outputs/scenario_test_v3",
                    help="Higher-recall model dir (fires the alert)")
    ap.add_argument("--v3", default="outputs/scenario_test_v2",
                    help="Higher-precision model dir (confirms confidence)")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    print("=" * 70)
    print("  ATTACK SCENARIO TEST — Ensemble Detector")
    print("=" * 70)
    print(f"  v2 (alarm)      : {args.v2}")
    print(f"  v3 (confidence) : {args.v3}")
    print()

    detector = build_ensemble(args.v2, args.v3)
    rng = np.random.default_rng(args.seed)

    # One representative meter per consumer type (matches _CTYPE assignment):
    # SM_0001=residentiel(A), SM_0003=industriel? -> use known indices by type.
    from smart_meters_simulator import _CTYPE
    reps = {}
    for idx, ctype in _CTYPE.items():
        if ctype not in reps:
            reps[ctype] = idx
        if len(reps) == 3:
            break

    burst_lengths = {
        "Surcharge": 8, "Tension hors norme": 6, "Pic soudain": 3,
        "Fraude": 40, "Consommation nulle suspecte": 40,
    }

    print("  --- Per-attack-type detection (one run per consumer type) ---")
    print(f"  {'attack_type':<28} {'meter_type':<12} {'detected':<10} {'latency(ticks)':<16} {'warmup_FP'}")
    print("  " + "-" * 78)

    results = []
    for atype in ATTACK_TYPES:
        for ctype, idx in reps.items():
            r = run_scenario(detector, idx, atype, burst_lengths[atype], rng)
            results.append({**r, "meter_type": ctype})
            lat = r["latency_ticks"] if r["latency_ticks"] is not None else "-"
            flag = "YES" if r["detected"] else "**MISSED**"
            print(f"  {atype:<28} {ctype:<12} {flag:<10} {str(lat):<16} {r['fp_during_warmup']}")

    print()
    print("  --- False-positive stress test (pure normal traffic) ---")
    fp_totals = {"n_ticks": 0, "false_alarms": 0}
    for ctype, idx in reps.items():
        r = run_normal_stress(detector, idx, 200, rng)
        fp_totals["n_ticks"] += r["n_ticks"]
        fp_totals["false_alarms"] += r["false_alarms"]
        print(f"    {ctype:<12} ticks={r['n_ticks']:<6} false_alarms={r['false_alarms']:<4} "
              f"FPR={r['fpr']*100:.2f}%")

    overall_fpr = fp_totals["false_alarms"] / fp_totals["n_ticks"]
    print(f"    {'TOTAL':<12} ticks={fp_totals['n_ticks']:<6} "
          f"false_alarms={fp_totals['false_alarms']:<4} FPR={overall_fpr*100:.2f}%")

    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    n_total = len(results)
    n_missed = sum(1 for r in results if not r["detected"])
    detected_lat = [r["latency_ticks"] for r in results if r["detected"]]
    print(f"  Scenarios run      : {n_total}")
    print(f"  Missed attacks     : {n_missed}  {'*** ATTENTION NEEDED ***' if n_missed else '(none)'}")
    if detected_lat:
        print(f"  Avg detect latency : {np.mean(detected_lat):.1f} ticks "
              f"({np.mean(detected_lat)*2:.1f} min at 2-min sampling)")
    print(f"  False-positive rate: {overall_fpr*100:.2f}%")
    if n_missed:
        print()
        print("  Missed attack types:")
        for r in results:
            if not r["detected"]:
                print(f"    - {r['attack_type']} ({r['meter_type']})")
    print("=" * 70)


if __name__ == "__main__":
    main()
