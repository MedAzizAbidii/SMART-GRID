"""Phase 7 — long-run / scaling benchmarks.

Covers the brief's "long-run profile" (memory growth, CPU stability, resource
leaks, logging overhead, blockchain performance) plus two scaling
investigations that came directly out of reading production/monitoring/
health.py and blockchain/poa_ledger.py while building this suite:

  1. `/health/detailed` calls `psutil.cpu_percent(interval=0.1)` synchronously
     inside an `async def` handler — a mandatory ~100ms blocking sleep, on
     the event loop, every single call. bench_health_detailed_blocking()
     isolates exactly how much of the endpoint's measured latency (see
     bench_latency.bench_rest_endpoints) that one call accounts for.
  2. The same handler calls `ledger.validate()`, which re-hashes every
     transaction in every block — O(total notarized records). Currently
     cheap (the live ledger has ~1 block) but its cost grows with the
     system's operational lifetime. bench_blockchain_validate_scaling()
     measures that growth curve directly on an isolated, throwaway ledger.

Both are read-only observations of existing code; nothing is changed.

The soak test drives the ALREADY-RUNNING production server with a light,
rate-limit-safe trickle of real traffic while sampling ITS process (by PID)
for memory growth/CPU stability, and separately runs a heavier in-process
loop (own throwaway detector + ledger) to see whether the ml_pipeline/
blockchain code itself leaks memory under sustained, uninterrupted use.
"""
from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perf.config import RESULTS_DIR, BASE_URL, LONGRUN_DURATION_SEC, LONGRUN_SAMPLE_INTERVAL_SEC
from perf.resource_monitor import ResourceMonitor, summarize, samples_to_dicts
from perf.bench_latency import percentiles, _sample_reading


# ---------------------------------------------------------------------------
# 1. /health/detailed blocking-call isolation
# ---------------------------------------------------------------------------
def bench_health_detailed_blocking(n: int = 20) -> dict:
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        psutil.cpu_percent(interval=0.1)
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "name": "psutil_cpu_percent_blocking_call_ms",
        "stats": percentiles(times),
        "note": "production/monitoring/health.py's /health/detailed handler calls "
                "psutil.cpu_percent(interval=0.1) directly inside an `async def` "
                "route with no run_in_executor/asyncio.to_thread — this blocks "
                "the ENTIRE event loop (not just the requesting connection) for "
                "~100ms on every call. Compare to bench_latency's measured "
                "/health/detailed endpoint latency (~109ms observed) — this one "
                "call accounts for essentially all of it.",
    }


# ---------------------------------------------------------------------------
# 2. Blockchain validate() cost vs chain size
# ---------------------------------------------------------------------------
def bench_blockchain_validate_scaling(checkpoints: list[int] = (10, 100, 500, 1000, 3000, 5000)) -> dict:
    from blockchain.poa_ledger import ProofOfAuthorityLedger, AuthorityNode, _sha256_text, _canonical_json

    ledger = ProofOfAuthorityLedger(
        authorities=[AuthorityNode.from_label(l) for l in
                     ("Utility Operator", "Grid Supervisor", "Security Auditor", "Data Custodian")],
        block_size=10, source_file="perf_scaling_isolated_ledger")

    out = {}
    written = 0
    for cp in checkpoints:
        batch = []
        for i in range(written, cp):
            record = {"meter_id": f"SM_SCALE_{i % 20:04d}", "attack_type": "FDIA",
                      "score": 0.01, "timestamp": datetime(2026, 6, 15).isoformat(), "row_index": i}
            record["row_hash"] = _sha256_text(_canonical_json(record))
            batch.append(record)
        ledger.ingest_records(batch)
        written = cp
        t0 = time.perf_counter()
        valid, errors = ledger.validate()
        dt_ms = (time.perf_counter() - t0) * 1000
        out[cp] = {"records": cp, "blocks": len(ledger.chain), "validate_ms": round(dt_ms, 3), "valid": valid}
        print(f"[longrun] validate() at {cp} records ({len(ledger.chain)} blocks): {dt_ms:.2f} ms")

    sizes = list(out.keys())
    times_ms = [out[s]["validate_ms"] for s in sizes]
    slope_ms_per_1000 = None
    if len(sizes) >= 2:
        slope_ms_per_1000 = round((times_ms[-1] - times_ms[0]) / (sizes[-1] - sizes[0]) * 1000, 4)

    return {
        "name": "blockchain_validate_scaling_ms",
        "by_record_count": out,
        "approx_slope_ms_per_1000_records": slope_ms_per_1000,
        "note": "ledger.validate() (called on every /health/detailed and "
                "/api/blockchain/status request) re-hashes every transaction "
                "in every block — cost grows with total records ever notarized, "
                "not just recent activity. The live ledger currently has ~1 "
                "block, so this cost is negligible today but will compound "
                "over the system's operational lifetime.",
    }


# ---------------------------------------------------------------------------
# 3. Logging overhead (same JsonFormatter/RotatingFileHandler as production,
#    writing to a throwaway directory)
# ---------------------------------------------------------------------------
def bench_logging_overhead(n: int = 2000) -> dict:
    from production.logging.setup import setup_logging, log_extra
    import logging

    with tempfile.TemporaryDirectory(prefix="sgrid_perf_logs_") as tmp:
        loggers = setup_logging(log_dir=tmp, level="INFO")
        logger = loggers["predictions"]

        times = []
        for i in range(n):
            t0 = time.perf_counter()
            logger.info("reading scored", extra=log_extra(
                meter_id=f"SM_LOG_{i % 20:04d}", is_anomaly=(i % 7 == 0),
                anomaly_score=0.001 * (i % 10), threshold=0.00035))
            times.append((time.perf_counter() - t0) * 1000)

        log_file = Path(tmp) / "predictions.log"
        size_bytes = log_file.stat().st_size if log_file.exists() else 0

        # Tear down the handlers we just added WHILE the temp dir still
        # exists — Windows cannot rmtree a directory containing files with
        # open handles, so this must happen before the `with` block exits.
        for lg in loggers.values():
            for h in list(lg.handlers):
                lg.removeHandler(h)
                h.close()
        import production.logging.setup as setup_mod
        setup_mod._configured = False

    return {
        "name": "structured_json_logging_overhead_ms_per_call",
        "stats": percentiles(times),
        "n_calls": n,
        "log_file_bytes": size_bytes,
        "bytes_per_line_avg": round(size_bytes / n, 1) if n else None,
    }


# ---------------------------------------------------------------------------
# 4. Soak test: live server (light real traffic) + in-process heavy load
# ---------------------------------------------------------------------------
def _find_live_server_pid() -> int | None:
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if "api_server.py" in cmdline or ("uvicorn" in cmdline and "api_server:app" in cmdline):
            return proc.info["pid"]
    return None


def bench_soak(duration_sec: int = LONGRUN_DURATION_SEC,
               interval_sec: float = LONGRUN_SAMPLE_INTERVAL_SEC) -> dict:
    from ml_pipeline.realtime_detector import get_detector
    from blockchain.poa_ledger import ProofOfAuthorityLedger, AuthorityNode, _sha256_text, _canonical_json
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator

    live_pid = _find_live_server_pid()
    live_mon = ResourceMonitor(pid=live_pid, interval_sec=interval_sec) if live_pid else None
    self_mon = ResourceMonitor(interval_sec=interval_sec)  # this profiling process itself

    if live_mon:
        live_mon.start()
    self_mon.start()

    # -- light, rate-limit-safe real traffic against the live server --------
    http_times = []
    http_errors = 0
    meter_id = "SM_SOAK"

    # -- heavier in-process load: isolated detector + isolated ledger -------
    detector = get_detector()
    ledger = ProofOfAuthorityLedger(
        authorities=[AuthorityNode.from_label(l) for l in
                     ("Utility Operator", "Grid Supervisor", "Security Auditor", "Data Custodian")],
        block_size=10, source_file="perf_soak_isolated_ledger")
    gen = RealisticDatasetGenerator(n_meters=20, seed=23)
    real_mid = gen.meters[0]
    soak_mid = "SM_SOAK_INPROCESS"
    seq_len = detector.seq_len if detector else 20
    ts0 = datetime(2026, 6, 15, 16, 0)
    for i in range(seq_len):
        r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * i))
        r["meter_id"] = soak_mid
        if detector:
            detector.ingest(r)

    inprocess_count = 0
    inprocess_anomalies = 0
    throughput_buckets = []  # (elapsed_sec, cumulative_count) sampled periodically

    t_start = time.time()
    t_next_http = t_start
    t_next_bucket = t_start
    i = seq_len
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        while time.time() - t_start < duration_sec:
            now = time.time()

            # heavy in-process work, best-effort every iteration
            if detector:
                r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * i))
                r["meter_id"] = soak_mid
                result = detector.ingest(r)
                inprocess_count += 1
                i += 1
                if result.get("is_anomaly"):
                    inprocess_anomalies += 1
                    record = {"meter_id": soak_mid, "attack_type": result.get("attack_type", "unknown"),
                              "score": result.get("anomaly_score", 0.0),
                              "timestamp": datetime.now().isoformat(), "row_index": inprocess_count}
                    record["row_hash"] = _sha256_text(_canonical_json(record))
                    ledger.ingest_records([record])

            # light real HTTP traffic, paced well under the 120/min budget
            if now >= t_next_http:
                t0 = time.perf_counter()
                try:
                    resp = client.post("/api/detect", json=_sample_reading(meter_id, int(now)))
                    if resp.status_code >= 400:
                        http_errors += 1
                except Exception:
                    http_errors += 1
                http_times.append((time.perf_counter() - t0) * 1000)
                t_next_http = now + 3.0  # ~20 req/min, well under 120/min

            if now >= t_next_bucket:
                throughput_buckets.append({"elapsed_sec": round(now - t_start, 1), "inprocess_count": inprocess_count})
                t_next_bucket = now + max(10.0, duration_sec / 20)

    live_samples = live_mon.stop() if live_mon else []
    self_samples = self_mon.stop()

    return {
        "name": "soak_test",
        "duration_sec": duration_sec,
        "live_server_pid": live_pid,
        "live_server_resources": summarize(live_samples) if live_samples else None,
        "profiling_process_resources": summarize(self_samples),
        "live_http_traffic": {
            "requests": len(http_times), "errors": http_errors,
            "latency_ms": percentiles(http_times),
        },
        "inprocess_heavy_load": {
            "total_readings": inprocess_count,
            "anomalies_detected": inprocess_anomalies,
            "final_block_count": len(ledger.chain),
            "avg_readings_per_sec": round(inprocess_count / duration_sec, 2),
        },
        "throughput_over_time": throughput_buckets,
        "live_server_samples_raw": samples_to_dicts(live_samples) if live_samples else [],
        "profiling_process_samples_raw": samples_to_dicts(self_samples),
    }


def run_all() -> dict:
    print("[longrun] health/detailed blocking-call isolation...")
    results = {"health_detailed_blocking": bench_health_detailed_blocking()}
    print("[longrun] blockchain validate() scaling...")
    results["blockchain_validate_scaling"] = bench_blockchain_validate_scaling()
    print("[longrun] logging overhead...")
    results["logging_overhead"] = bench_logging_overhead()
    print(f"[longrun] soak test ({LONGRUN_DURATION_SEC}s)...")
    results["soak"] = bench_soak()

    out_path = RESULTS_DIR / "longrun.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[longrun] written -> {out_path}")
    return results


if __name__ == "__main__":
    run_all()
