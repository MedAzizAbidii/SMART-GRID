"""
robustness/stress.py — chunked stress test (throughput / latency / memory / failure point).

Synthesizes load by resampling+jittering real test sequences in CHUNKS (never
materializing the full N in memory — 10M sequences x 8 x 85 float32 would be
~27 GB) and streams them through the frozen production model, exactly as a
real high-volume deployment would batch inference. This measures genuine
engineering throughput/latency/memory scaling; it does not claim 10M distinct
"real" grid readings — it is a scale/engineering stress test, not a realism
claim, and that distinction is stated in the report.

Usage:
  .\.venv\Scripts\python.exe -m robustness.stress                 # 100K..1M (fast)
  .\.venv\Scripts\python.exe -m robustness.stress --max 10000000  # attempt up to 10M
"""
from __future__ import annotations

import argparse
import gc
import json
import time
import tracemalloc
from pathlib import Path

import numpy as np
import psutil
import torch

from robustness.common import load_detector, load_test_split

RES = Path(__file__).resolve().parent / "results"
SCALES = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
CHUNK = 20_000
TIME_BUDGET_S = 90     # per-scale wall-clock cap; if exceeded, mark and stop scaling up


def synth_batch(base: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    idx = rng.integers(0, len(base), n)
    noise = rng.normal(0, 0.02, (n, *base.shape[1:])).astype("float32")
    return base[idx] + noise


def run_scale(model, base, n_target: int, seed=0):
    rng = np.random.default_rng(seed)
    gc.collect(); tracemalloc.start()
    proc = psutil.Process()
    rss0 = proc.memory_info().rss
    t0 = time.perf_counter()
    processed = 0
    lat_samples = []
    failed = False
    reason = ""
    try:
        while processed < n_target:
            n = min(CHUNK, n_target - processed)
            batch = synth_batch(base, n, rng)
            tb0 = time.perf_counter()
            with torch.no_grad():
                for i in range(0, len(batch), 256):
                    xb = torch.tensor(batch[i:i+256], dtype=torch.float32)
                    rec, _ = model(xb)
                    _ = ((rec - xb) ** 2).mean(dim=(1, 2))
            lat_samples.append((time.perf_counter() - tb0) / len(batch) * 1000)
            processed += n
            if time.perf_counter() - t0 > TIME_BUDGET_S:
                reason = f"time budget ({TIME_BUDGET_S}s) reached"
                break
    except MemoryError:
        failed = True; reason = "MemoryError"
    except Exception as exc:
        failed = True; reason = str(exc)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    rss1 = proc.memory_info().rss
    throughput = processed / elapsed if elapsed > 0 else 0.0
    return {
        "target": n_target, "processed": processed, "completed": processed >= n_target,
        "elapsed_s": round(elapsed, 2), "throughput_seq_per_s": round(throughput, 1),
        "latency_ms_per_seq_mean": round(float(np.mean(lat_samples)), 5) if lat_samples else None,
        "peak_traced_mb": round(peak / 1e6, 2), "rss_delta_mb": round((rss1 - rss0) / 1e6, 2),
        "failed": failed, "stop_reason": reason or ("completed" if processed >= n_target else "n/a"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=1_000_000)
    args = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    scales = [s for s in SCALES if s <= args.max]

    det = load_detector()
    te_s, te_l, cols, frame, te_end = load_test_split()
    print("=" * 60)
    print(f"  STRESS TEST — scales up to {args.max:,} (chunked, {CHUNK:,}/chunk)")
    print("=" * 60)
    results = []
    for n in scales:
        r = run_scale(det.model, te_s, n)
        results.append(r)
        print(f"  N={n:>10,}  processed={r['processed']:>10,}  "
              f"throughput={r['throughput_seq_per_s']:>9,.0f} seq/s  "
              f"lat/seq={r['latency_ms_per_seq_mean']}ms  mem+{r['rss_delta_mb']}MB  "
              f"[{r['stop_reason']}]")
        if not r["completed"]:
            print(f"    -> stopped scaling further ({r['stop_reason']}); "
                  "larger scales are extrapolated in the report, not measured.")
            break
    (RES / "stress_results.json").write_text(json.dumps(results, indent=2))
    print(f"  saved: {RES / 'stress_results.json'}")


if __name__ == "__main__":
    main()
