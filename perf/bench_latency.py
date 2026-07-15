"""Phase 7 — latency benchmarks for every subsystem.

Measurement-only: imports and calls existing public functions/classes as-is.
Never edits model weights, the live blockchain ledger, or persisted state.

Blockchain latency is measured against a throwaway, in-memory
ProofOfAuthorityLedger instance (same class, same authorities/block_size as
production) so the real audit trail in data/blockchain/ is never touched.

Cold-start / model-load latency is measured in THIS process (a separate
Python process from the already-running uvicorn server), so it reflects a
genuine from-nothing load, not the warm, already-cached server.
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perf.config import ROOT, RESULTS_DIR, BASE_URL, SAMPLE_METER_ID, SAMPLE_ZONE


def percentiles(values: list[float]) -> dict:
    if not values:
        return {}
    s = sorted(values)
    def pct(p):
        k = (len(s) - 1) * p
        f, c = int(k), min(int(k) + 1, len(s) - 1)
        return round(s[f] + (s[c] - s[f]) * (k - f), 3)
    return {
        "min": round(s[0], 3), "max": round(s[-1], 3),
        "mean": round(statistics.mean(s), 3),
        "p50": pct(0.50), "p90": pct(0.90), "p95": pct(0.95), "p99": pct(0.99),
        "n": len(s),
    }


# ---------------------------------------------------------------------------
# 1. Simulator generation latency
# ---------------------------------------------------------------------------
def bench_simulator(n: int = 500) -> dict:
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator
    gen = RealisticDatasetGenerator(n_meters=20, seed=7)
    mid = gen.meters[0]
    ts = datetime(2026, 6, 15, 14, 30)
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        gen._meter_reading(mid, ts + timedelta(minutes=2 * i))
        times.append((time.perf_counter() - t0) * 1000)
    return {"name": "simulator_generation_ms", "stats": percentiles(times), "raw_ms": times}


# ---------------------------------------------------------------------------
# 2. Preprocessing + model inference latency (in-process, direct call)
# ---------------------------------------------------------------------------
def bench_inference(n: int = 300) -> dict:
    from ml_pipeline.realtime_detector import get_detector
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator

    detector = get_detector()
    if detector is None:
        return {"name": "inference_ms", "error": "model not available (get_detector() returned None)"}

    gen = RealisticDatasetGenerator(n_meters=20, seed=11)
    real_mid = gen.meters[0]      # a meter id the generator's internal tables know about
    mid = "SM_PERF_INF"           # the (arbitrary) buffer key used for ingest()
    ts0 = datetime(2026, 6, 15, 8, 0)

    seq_len = getattr(detector, "seq_len", getattr(getattr(detector, "detector_v3", None), "seq_len", 20))

    # Warm the rolling buffer (these calls return "insufficient_data", not timed)
    for i in range(seq_len):
        r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * i))
        r["meter_id"] = mid
        detector.ingest(r)

    times = []
    for i in range(seq_len, seq_len + n):
        r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * i))
        r["meter_id"] = mid
        t0 = time.perf_counter()
        detector.ingest(r)
        times.append((time.perf_counter() - t0) * 1000)

    return {
        "name": "inference_ms (preprocessing + forward pass + XAI, in-process)",
        "stats": percentiles(times),
        "raw_ms": times,
        "detector_reported_avg_latency_ms": getattr(detector, "avg_latency_ms", lambda: None)(),
    }


# ---------------------------------------------------------------------------
# 3. Blockchain write latency (isolated, in-memory ledger — no disk writes)
# ---------------------------------------------------------------------------
def bench_blockchain(n: int = 500) -> dict:
    from blockchain.poa_ledger import ProofOfAuthorityLedger, AuthorityNode, _sha256_text, _canonical_json

    ledger = ProofOfAuthorityLedger(
        authorities=[
            AuthorityNode.from_label("Utility Operator"),
            AuthorityNode.from_label("Grid Supervisor"),
            AuthorityNode.from_label("Security Auditor"),
            AuthorityNode.from_label("Data Custodian"),
        ],
        block_size=10,
        source_file="perf_isolated_ledger",
    )
    times = []
    for i in range(n):
        record = {
            "meter_id": f"SM_PERF_{i % 20:04d}",
            "attack_type": "FDIA",
            "score": 0.01 + (i % 7) * 0.0001,
            "timestamp": datetime(2026, 6, 15).isoformat(),
            "row_index": i,
        }
        record["row_hash"] = _sha256_text(_canonical_json(record))
        t0 = time.perf_counter()
        ledger.ingest_records([record])
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "name": "blockchain_ingest_records_ms (single record, isolated ledger)",
        "stats": percentiles(times),
        "raw_ms": times,
        "final_block_count": len(ledger.chain),
    }


# ---------------------------------------------------------------------------
# 4. REST API + dashboard asset latency (against the live running server)
# ---------------------------------------------------------------------------
def _sample_reading(meter_id: str, i: int) -> dict:
    return {
        "meter_id": meter_id,
        "timestamp": (datetime(2026, 6, 15, 9, 0) + timedelta(minutes=2 * i)).isoformat(),
        "consommation_kw": 2.0 + (i % 5) * 0.1,
        "tension_v": 228.0,
        "courant_a": 9.0,
        "power_factor": 0.91,
        "frequency_hz": 60.0,
        "zone": SAMPLE_ZONE,
        "type": "residentiel",
    }


def bench_rate_limit_ceiling(burst: int = 150) -> dict:
    """Characterizes the REAL, as-deployed rate limiter (production default:
    120 req/min — production/config/settings.py, never altered) by bursting
    requests against the actual running production instance (BASE_URL, port
    8000) and finding exactly where 429s start. This IS the operational
    ceiling for external API traffic — a deliberate, named finding, not noise.
    """
    times = []
    codes = []
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        for _ in range(burst):
            t0 = time.perf_counter()
            try:
                resp = client.get("/api/blockchain/status")
                codes.append(resp.status_code)
            except Exception:
                codes.append(-1)
            times.append((time.perf_counter() - t0) * 1000)
    first_429_at = next((i for i, c in enumerate(codes) if c == 429), None)
    return {
        "name": "rate_limit_ceiling (production instance, port 8000, as deployed)",
        "burst_requests": burst,
        "first_429_at_request_index": first_429_at,
        "total_429s": codes.count(429),
        "total_200s": codes.count(200),
        "request_latency_stats_ms": percentiles(times),
        "note": "The deployed RateLimitMiddleware default (120 req/min) rejects "
                "requests with 429 well before the backend's own processing "
                "capacity is reached (see inference/blockchain in-process "
                "benchmarks). This is a hard external-traffic ceiling by design, "
                "not a backend performance limit.",
    }


def bench_rest_endpoints(n: int = 15) -> dict:
    """REST latency for a request count that comfortably fits inside the
    production rate-limit budget (120/min) across all endpoints combined,
    measured against the real running instance — no workaround, no second
    instance. Any 429 is reported, not hidden."""
    endpoints = ["/health", "/health/ready", "/health/detailed",
                 "/api/blockchain/status", "/api/model/status", "/dashboard", "/support.js"]
    out = {}
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        for ep in endpoints:
            times = []
            errors = 0
            for _ in range(n):
                t0 = time.perf_counter()
                try:
                    resp = client.get(ep)
                    if resp.status_code >= 400:
                        errors += 1
                except Exception:
                    errors += 1
                    continue
                times.append((time.perf_counter() - t0) * 1000)
            out[ep] = {"stats": percentiles(times), "errors": errors}
    return {"name": "rest_endpoint_latency_ms", "note": f"n={n}/endpoint, kept small to respect the live 120 req/min limiter", "endpoints": out}


def bench_e2e_detect(n: int = 40) -> dict:
    """End-to-end /api/detect latency over real HTTP against the live,
    unmodified production instance. n is kept small (with the earlier
    rest_endpoints + rate_limit_ceiling calls already having consumed part of
    the rolling 120/min budget) so this reflects genuine within-budget
    latency rather than 429s."""
    meter_id = "SM_PERF_E2E"
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # warm the rolling buffer server-side (counts against the same budget)
        for i in range(25):
            client.post("/api/detect", json=_sample_reading(meter_id, i))
        times = []
        errors = 0
        for i in range(25, 25 + n):
            payload = _sample_reading(meter_id, i)
            t0 = time.perf_counter()
            try:
                resp = client.post("/api/detect", json=payload)
                if resp.status_code >= 400:
                    errors += 1
            except Exception:
                errors += 1
                continue
            times.append((time.perf_counter() - t0) * 1000)
    return {"name": "e2e_detect_http_ms", "stats": percentiles(times), "errors": errors}


def bench_batch_vs_single(batch_sizes: list[int] = (1, 5, 10, 25, 50, 100)) -> dict:
    """Batch vs single-reading throughput, measured IN-PROCESS against a
    dedicated detector instance (same code as api_server.py's /api/detect and
    /api/detect/batch handlers) — zero HTTP, zero interaction with the rate
    limiter or auth layer. This isolates the ml_pipeline subsystem's own
    batching behavior from the API-layer rate limit measured separately above.
    """
    from ml_pipeline.realtime_detector import get_detector
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator

    detector = get_detector()
    if detector is None:
        return {"name": "batch_vs_single_ms", "error": "model not available"}

    gen = RealisticDatasetGenerator(n_meters=20, seed=13)
    real_mid = gen.meters[0]
    seq_len = getattr(detector, "seq_len", getattr(getattr(detector, "detector_v3", None), "seq_len", 20))
    ts0 = datetime(2026, 6, 15, 10, 0)

    out = {}
    for bs in batch_sizes:
        # warm bs independent buffer keys so each ingest() does a real forward pass
        keys = [f"SM_PERF_BATCH_{bs}_{j}" for j in range(bs)]
        for k in keys:
            for w in range(seq_len):
                r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * w))
                r["meter_id"] = k
                detector.ingest(r)
        readings = []
        for j, k in enumerate(keys):
            r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * (seq_len + j)))
            r["meter_id"] = k
            readings.append(r)
        t0 = time.perf_counter()
        for r in readings:
            detector.ingest(r)
        dt_ms = (time.perf_counter() - t0) * 1000
        out[bs] = {"total_ms": round(dt_ms, 3), "ms_per_reading": round(dt_ms / bs, 3)}
    return {"name": "batch_vs_single_ms (in-process, ml_pipeline only)", "by_batch_size": out}


# ---------------------------------------------------------------------------
# 5. Cold start (model load) — measured in THIS separate process
# ---------------------------------------------------------------------------
def bench_cold_start() -> dict:
    script = (
        "import time,sys; t0=time.perf_counter(); "
        "sys.path.insert(0, r'%s'); "
        "from ml_pipeline.realtime_detector import get_detector; "
        "d=get_detector(); "
        "print((time.perf_counter()-t0)*1000)"
    ) % str(ROOT)
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    t_wall0 = time.perf_counter()
    proc = subprocess.run([str(venv_py), "-c", script], capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    wall_ms = (time.perf_counter() - t_wall0) * 1000
    reported_ms = None
    try:
        reported_ms = float(proc.stdout.strip().splitlines()[-1])
    except Exception:
        pass
    return {
        "name": "cold_start_model_load_ms",
        "subprocess_wall_ms": round(wall_ms, 1),
        "reported_load_ms": reported_ms,
        "stderr_tail": proc.stderr[-500:] if proc.returncode != 0 else None,
    }


# ---------------------------------------------------------------------------
# 6. Application startup (uvicorn boot to first healthy /health, alt port)
# ---------------------------------------------------------------------------
def bench_app_startup(port: int = 8091, timeout_sec: float = 60.0) -> dict:
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    env_cmd = [
        str(venv_py), "-m", "uvicorn", "api_server:app",
        "--host", "127.0.0.1", "--port", str(port),
    ]
    t0 = time.perf_counter()
    proc = subprocess.Popen(env_cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    healthy_at = None
    try:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
                if r.status_code == 200:
                    healthy_at = time.perf_counter()
                    break
            except Exception:
                pass
            time.sleep(0.1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

    if healthy_at is None:
        return {"name": "app_startup_ms", "error": f"did not become healthy within {timeout_sec}s"}
    return {"name": "app_startup_ms", "startup_ms": round((healthy_at - t0) * 1000, 1)}


def run_all() -> dict:
    print("[latency] simulator...")
    results = {"simulator": bench_simulator()}
    print("[latency] inference (in-process)...")
    results["inference"] = bench_inference()
    print("[latency] blockchain (isolated ledger, in-process)...")
    results["blockchain"] = bench_blockchain()
    print("[latency] batch vs single (in-process)...")
    results["batch_vs_single"] = bench_batch_vs_single()
    print("[latency] cold start (subprocess)...")
    results["cold_start"] = bench_cold_start()
    print("[latency] app startup (subprocess, alt port)...")
    results["app_startup"] = bench_app_startup()
    print("[latency] rate-limit ceiling (live production instance, port 8000, fresh window)...")
    results["rate_limit_ceiling"] = bench_rate_limit_ceiling()
    print("[latency] waiting 65s for the 120/min rate-limit window to reset before further HTTP calls...")
    time.sleep(65)
    print("[latency] REST endpoints (live production instance, port 8000)...")
    results["rest_endpoints"] = bench_rest_endpoints()
    print("[latency] e2e /api/detect (live production instance, port 8000)...")
    results["e2e_detect"] = bench_e2e_detect()

    out_path = RESULTS_DIR / "latency.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[latency] written -> {out_path}")
    return results


if __name__ == "__main__":
    run_all()
