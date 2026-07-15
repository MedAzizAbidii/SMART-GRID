"""Phase 7 — single entrypoint: runs every benchmark in order, then analysis,
reports, and final regression validation.

Precondition: the production server (api_server.py) must already be running
on BASE_URL (see perf/config.py) — this script does not start/stop it, so
profiling never risks leaving a stray process behind.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perf.config import BASE_URL
from perf import bench_latency, bench_throughput, bench_concurrency, bench_longrun
from perf import bottleneck_analysis, report_generator, validate_regression


def _require_server() -> None:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=3.0)
        if r.status_code != 200:
            raise RuntimeError(f"{BASE_URL}/health returned {r.status_code}")
    except Exception as exc:
        raise RuntimeError(
            f"Server not reachable at {BASE_URL}. Start it first: "
            f"`./.venv/Scripts/python.exe api_server.py`"
        ) from exc


def main() -> None:
    t0 = time.time()
    _require_server()

    print("\n=== [1/6] LATENCY ===")
    bench_latency.run_all()

    print("\n=== [2/6] THROUGHPUT ===")
    bench_throughput.run_all()

    print("\n=== [3/6] CONCURRENCY ===")
    bench_concurrency.run_all()

    print("\n=== [4/6] LONG-RUN / SCALING ===")
    bench_longrun.run_all()

    print("\n=== [5/6] BOTTLENECK ANALYSIS ===")
    bottleneck_analysis.run_all()

    print("\n=== [6/6] REPORTS (figures + tables) ===")
    report_generator.generate_all_figures()
    report_generator.generate_tables()

    print("\n=== VALIDATION (no regressions) ===")
    validate_regression.run_all()

    print(f"\nDone in {time.time() - t0:.0f}s. See perf/results/*.json and perf/reports/.")


if __name__ == "__main__":
    main()
