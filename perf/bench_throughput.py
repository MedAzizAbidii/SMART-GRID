"""Phase 7 — throughput benchmarks (samples/sec, detections/sec, batch vs
streaming), measured in-process against the same ml_pipeline/blockchain code
the live server uses. No HTTP, no rate limiter, no auth involved — this
isolates backend compute throughput from the deployed API traffic ceiling
(see bench_latency.bench_rate_limit_ceiling for that, measured separately,
honestly, against the real running instance).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perf.config import RESULTS_DIR, THROUGHPUT_WINDOW_SEC


def bench_simulator_throughput(window_sec: float = THROUGHPUT_WINDOW_SEC) -> dict:
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator
    gen = RealisticDatasetGenerator(n_meters=20, seed=3)
    mid = gen.meters[0]
    ts = datetime(2026, 6, 15, 12, 0)
    count = 0
    t_end = time.perf_counter() + window_sec
    i = 0
    while time.perf_counter() < t_end:
        gen._meter_reading(mid, ts + timedelta(minutes=2 * i))
        count += 1
        i += 1
    return {"name": "simulator_samples_per_sec", "window_sec": window_sec,
            "count": count, "samples_per_sec": round(count / window_sec, 1)}


def bench_ingest_throughput(window_sec: float = THROUGHPUT_WINDOW_SEC) -> dict:
    """Single-threaded streaming throughput of the full ingest pipeline
    (preprocessing + model forward pass + XAI) — this is the realistic
    ceiling for a single synchronous worker, matching how api_server.py
    actually calls _ml_detector.ingest() (a direct, blocking call inside the
    async handler — see bench_concurrency.py for why that architecture
    means concurrency doesn't parallelize this cost)."""
    from ml_pipeline.realtime_detector import get_detector
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator

    detector = get_detector()
    if detector is None:
        return {"name": "ingest_samples_per_sec", "error": "model not available"}

    gen = RealisticDatasetGenerator(n_meters=20, seed=5)
    real_mid = gen.meters[0]
    mid = "SM_PERF_THROUGHPUT"
    seq_len = getattr(detector, "seq_len", getattr(getattr(detector, "detector_v3", None), "seq_len", 20))
    ts0 = datetime(2026, 6, 15, 13, 0)
    for i in range(seq_len):
        r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * i))
        r["meter_id"] = mid
        detector.ingest(r)

    count = 0
    i = seq_len
    t_end = time.perf_counter() + window_sec
    while time.perf_counter() < t_end:
        r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * i))
        r["meter_id"] = mid
        detector.ingest(r)
        count += 1
        i += 1
    return {"name": "ingest_samples_per_sec (streaming, single-threaded)",
            "window_sec": window_sec, "count": count,
            "samples_per_sec": round(count / window_sec, 2),
            "implied_max_ms_per_sample": round(1000 * window_sec / count, 2) if count else None}


def bench_detection_throughput_with_blockchain(window_sec: float = THROUGHPUT_WINDOW_SEC) -> dict:
    """Worst-case end-to-end throughput: every reading is a confirmed
    anomaly, so every ingest() ALSO triggers a blockchain ingest_records()
    call, exactly like _finalize_detection() does in api_server.py. Uses the
    same isolated, throwaway ledger pattern as bench_latency.bench_blockchain
    — never touches the live audit trail."""
    from ml_pipeline.realtime_detector import get_detector
    from blockchain.poa_ledger import ProofOfAuthorityLedger, AuthorityNode, _sha256_text, _canonical_json

    detector = get_detector()
    if detector is None:
        return {"name": "detections_per_sec", "error": "model not available"}

    ledger = ProofOfAuthorityLedger(
        authorities=[AuthorityNode.from_label(l) for l in
                     ("Utility Operator", "Grid Supervisor", "Security Auditor", "Data Custodian")],
        block_size=10, source_file="perf_throughput_isolated_ledger")

    seq_len = getattr(detector, "seq_len", getattr(getattr(detector, "detector_v3", None), "seq_len", 20))
    mid = "SM_PERF_ANOM"
    ts0 = datetime(2026, 6, 15, 14, 0)
    # An extreme, clearly-anomalous reading (matches the FDIA pattern used
    # elsewhere in the dashboard demo: implausible consumption spike).
    for i in range(seq_len):
        reading = {"meter_id": mid, "timestamp": (ts0 + timedelta(minutes=2 * i)).isoformat(),
                   "consommation_kw": 2.0, "tension_v": 228.0, "courant_a": 9.0,
                   "power_factor": 0.9, "frequency_hz": 60.0, "zone": "Zone A", "type": "residentiel"}
        detector.ingest(reading)

    count = 0
    anomalies = 0
    i = seq_len
    t_end = time.perf_counter() + window_sec
    while time.perf_counter() < t_end:
        reading = {"meter_id": mid, "timestamp": (ts0 + timedelta(minutes=2 * i)).isoformat(),
                   "consommation_kw": 45.0, "tension_v": 260.0, "courant_a": 90.0,
                   "power_factor": 0.5, "frequency_hz": 60.0, "zone": "Zone A", "type": "residentiel"}
        result = detector.ingest(reading)
        if result.get("is_anomaly"):
            anomalies += 1
            record = {"meter_id": mid, "attack_type": result.get("attack_type", "unknown"),
                      "score": result.get("anomaly_score", 0.0), "timestamp": reading["timestamp"], "row_index": i}
            record["row_hash"] = _sha256_text(_canonical_json(record))
            ledger.ingest_records([record])
        count += 1
        i += 1
    return {"name": "detections_per_sec (ingest + conditional blockchain notarization)",
            "window_sec": window_sec, "total_readings": count, "anomalies_detected": anomalies,
            "readings_per_sec": round(count / window_sec, 2),
            "detections_per_sec": round(anomalies / window_sec, 2),
            "final_block_count": len(ledger.chain)}


def run_all() -> dict:
    print("[throughput] simulator...")
    results = {"simulator": bench_simulator_throughput()}
    print("[throughput] ingest (streaming, single-threaded)...")
    results["ingest_streaming"] = bench_ingest_throughput()
    print("[throughput] detection + blockchain (worst case, all-anomaly)...")
    results["detection_with_blockchain"] = bench_detection_throughput_with_blockchain()

    out_path = RESULTS_DIR / "throughput.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[throughput] written -> {out_path}")
    return results


if __name__ == "__main__":
    run_all()
