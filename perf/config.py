"""Phase 7 profiling — shared paths and constants.

Measurement-only module. Nothing here imports or mutates model weights,
the live blockchain ledger, or dashboard/API source files.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # smartgrid_simulation/
PERF_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PERF_DIR / "results"
REPORTS_DIR = PERF_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"

for d in (RESULTS_DIR, REPORTS_DIR, FIGURES_DIR, TABLES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Live, already-running server exactly as deployed in production (rate limit
# = 120 req/min default, per production/config/settings.py — never altered).
# Used to measure real-world REST/e2e latency AND to document the actual
# deployed rate-limit ceiling — both are legitimate "operational performance"
# findings. All HTTP-level benchmarks respect this budget (small request
# counts, honest reporting of any 429s) rather than working around it.
#
# Throughput/concurrency/soak characterization of the model, preprocessing,
# and blockchain subsystems is done IN-PROCESS instead (bench_throughput.py,
# bench_concurrency.py) — calling ml_pipeline/blockchain code directly via
# threads, with zero HTTP traffic and zero interaction with rate limiting or
# auth. This measures the backend's real compute capacity without touching
# any security control, live or otherwise.
BASE_URL = "http://127.0.0.1:8000"

# Concurrency levels requested by the Phase 7 brief. Levels beyond what the
# hardware can sustain are still attempted; the harness records saturation
# (errors/timeouts) rather than silently capping the list.
CONCURRENCY_LEVELS = [1, 10, 25, 50, 100, 250, 500, 1000]

# Long-run soak window. A full multi-hour soak is impractical inside a single
# interactive session on a laptop; this is a scaled-down window explicitly
# documented as such in the final report (see perf/reports/*).
LONGRUN_DURATION_SEC = 300  # 5 minutes
LONGRUN_SAMPLE_INTERVAL_SEC = 2

THROUGHPUT_WINDOW_SEC = 10

SAMPLE_METER_ID = "SM_0001"
SAMPLE_ZONE = "Zone A"
