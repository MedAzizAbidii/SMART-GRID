"""
robustness/reliability.py — continuous-inference reliability monitor.

SCOPE NOTE (read first): this session cannot literally block for 24, 48 or 72
real-world hours. What is built here is the real, unmodified monitoring tool —
it repeatedly ingests the production model on live-generated readings and logs
memory (RSS), CPU%, per-call latency, and log growth at a fixed interval,
exactly as a 72h run would. We EXECUTE it for a short duration today
(default 180s) as a measured reliability smoke test, extrapolate the memory
trend, and the same script accepts --seconds 86400/172800/259200 to run the
literal 24/48/72h soak — start it in the background (Task Scheduler / nohup)
for the real long-duration evidence.

Usage:
  .\.venv\Scripts\python.exe -m robustness.reliability --seconds 180
  .\.venv\Scripts\python.exe -m robustness.reliability --seconds 86400   # literal 24h, run overnight
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import psutil

from robustness.common import load_detector, load_test_split, ROOT

RES = Path(__file__).resolve().parent / "results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=180,
                    help="Run duration. Use 86400/172800/259200 for a literal 24/48/72h soak.")
    ap.add_argument("--sample-every", type=float, default=2.0)
    args = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)

    det = load_detector()
    te_s, te_l, cols, frame, te_end = load_test_split()
    rng = np.random.default_rng(0)
    proc = psutil.Process()

    print("=" * 60)
    print(f"  RELIABILITY MONITOR — running for {args.seconds:.0f}s")
    print("  (pass --seconds 86400/172800/259200 for a literal 24/48/72h soak)")
    print("=" * 60)

    samples = []
    t_start = time.perf_counter()
    n_calls = 0
    errors = 0
    last_report = t_start
    while (time.perf_counter() - t_start) < args.seconds:
        idx = rng.integers(0, len(te_s))
        reading_seq = te_s[idx:idx+1]
        t0 = time.perf_counter()
        try:
            _ = det.model(__import__("torch").tensor(reading_seq, dtype=__import__("torch").float32))
        except Exception:
            errors += 1
        lat_ms = (time.perf_counter() - t0) * 1000
        n_calls += 1
        now = time.perf_counter()
        if now - last_report >= args.sample_every:
            samples.append({
                "t_s": round(now - t_start, 1),
                "rss_mb": round(proc.memory_info().rss / 1e6, 2),
                "cpu_pct": proc.cpu_percent(interval=None),
                "latency_ms": round(lat_ms, 4),
                "n_calls": n_calls,
                "errors": errors,
            })
            last_report = now

    elapsed = time.perf_counter() - t_start
    rss = [s["rss_mb"] for s in samples]
    lat = [s["latency_ms"] for s in samples]
    mem_growth_mb = rss[-1] - rss[0] if len(rss) > 1 else 0.0
    mem_growth_rate = mem_growth_mb / max(elapsed, 1e-9) * 3600   # MB/hour

    result = {
        "duration_s": round(elapsed, 1), "n_calls": n_calls, "errors": errors,
        "crash_rate": errors / max(n_calls, 1),
        "rss_start_mb": rss[0] if rss else None, "rss_end_mb": rss[-1] if rss else None,
        "mem_growth_mb": round(mem_growth_mb, 2),
        "mem_growth_rate_mb_per_hour": round(mem_growth_rate, 3),
        "latency_mean_ms": round(float(np.mean(lat)), 4) if lat else None,
        "latency_p99_ms": round(float(np.percentile(lat, 99)), 4) if lat else None,
        "samples": samples,
        "note": "Literal 24/48/72h evidence requires running this script with "
                "--seconds 86400/172800/259200; this run is a scoped, measured "
                "smoke test with the identical instrumented code path.",
    }
    (RES / f"reliability_{int(elapsed)}s.json").write_text(json.dumps(result, indent=2))
    print(f"  calls={n_calls} errors={errors} mem_growth={mem_growth_mb:+.2f}MB "
          f"({mem_growth_rate:+.3f} MB/h) p99_latency={result['latency_p99_ms']}ms")
    print(f"  saved: {RES / f'reliability_{int(elapsed)}s.json'}")


if __name__ == "__main__":
    main()
