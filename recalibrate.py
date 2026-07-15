"""
recalibrate.py — real-data onboarding / threshold recalibration.

THE fix for the failure we proved in the cross-season test: a frozen model's
anomaly-score distribution shifts when the input distribution shifts (e.g.
summer->winter, or synthetic->real hardware), so a threshold calibrated on the
old data produces a flood of false positives. Retraining the whole model is
expensive and needs labels; recalibrating just the THRESHOLD on new NORMAL
data is cheap, unsupervised, and recovers performance (we measured F1 0.14 ->
0.66 on winter data just by re-deriving the threshold).

This keeps the model weights + scaler FROZEN (so it stays the same model) and
only re-derives the decision threshold from the score distribution of new
baseline data. That is exactly what you run once you have a few days of real
smart-meter readings, BEFORE injecting test attacks.

Usage:
  # Unsupervised (real deployment case: you only have normal baseline data)
  .\.venv\Scripts\python.exe recalibrate.py --model outputs/early_stopping_final \
      --data ../data/real_baseline.csv --strategy percentile --percentile 99.0

  # Supervised (you have labelled attacks -> pick F1-optimal)
  .\.venv\Scripts\python.exe recalibrate.py --model outputs/early_stopping_final \
      --data ../data/labelled.csv --strategy f1
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from eval_holdout import load_frozen, score_csv, prf, roc_auc


def best_f1_threshold(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    cands = np.unique(np.quantile(scores, np.linspace(0.50, 0.999, 300)))
    best_t, best_f = float(cands[len(cands) // 2]), -1.0
    for t in cands:
        _, _, _, f1, _ = prf(labels, (scores >= t).astype(int))
        if f1 > best_f:
            best_f, best_t = f1, float(t)
    return best_t, best_f


def main():
    ap = argparse.ArgumentParser(description="Recalibrate a frozen model's threshold on new data")
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path, help="New baseline CSV (normal-dominant)")
    ap.add_argument("--strategy", choices=["conservative", "percentile", "f1"], default="percentile")
    ap.add_argument("--k", type=float, default=3.0, help="sigma multiplier for 'conservative'")
    ap.add_argument("--percentile", type=float, default=99.0, help="percentile for 'percentile'")
    args = ap.parse_args()

    model, scaler, cols, seq_len, old_thr = load_frozen(args.model)

    print("=" * 66)
    print("  THRESHOLD RECALIBRATION (model + scaler stay frozen)")
    print("=" * 66)
    print(f"  Model         : {args.model.name}")
    print(f"  New data      : {args.data.name}")
    print(f"  Old threshold : {old_thr:.6f}")

    scores, labels, anomalies = score_csv(args.data, model, scaler, cols, seq_len)
    normal_scores = scores[labels == 0]
    n_norm, n_atk = int((labels == 0).sum()), int((labels == 1).sum())
    print(f"  Scored        : {len(scores):,} sequences ({n_norm:,} normal, {n_atk:,} attack)")

    # --- derive the new threshold ---
    if args.strategy == "conservative":
        new_thr = float(normal_scores.mean() + args.k * normal_scores.std())
        detail = f"mean + {args.k}*sigma of normal scores"
    elif args.strategy == "percentile":
        new_thr = float(np.quantile(normal_scores, args.percentile / 100.0))
        detail = f"{args.percentile:.1f}th percentile of normal scores"
    else:  # f1 (needs labels)
        if n_atk == 0:
            print("\n  [!] --strategy f1 needs attack labels but none found; "
                  "falling back to percentile 99.")
            new_thr = float(np.quantile(normal_scores, 0.99))
            detail = "99th percentile (f1 fallback)"
        else:
            new_thr, f1 = best_f1_threshold(scores, labels)
            detail = f"F1-optimal (F1={f1:.3f})"

    print(f"\n  Strategy      : {args.strategy}  ({detail})")
    print(f"  NEW threshold : {new_thr:.6f}")

    # --- show the improvement if we have labels ---
    if n_atk > 0:
        auc = roc_auc(labels, scores)
        _, p0, r0, f0, _ = prf(labels, (scores >= old_thr).astype(int))
        _, p1, r1, f1n, _ = prf(labels, (scores >= new_thr).astype(int))
        print(f"\n  On this data (AUC={auc:.4f}, threshold-independent):")
        print(f"    OLD threshold -> Recall={r0:.3f} Precision={p0:.3f} F1={f0:.3f}")
        print(f"    NEW threshold -> Recall={r1:.3f} Precision={p1:.3f} F1={f1n:.3f}")

    # --- persist: back up then update training_report.json ---
    report_path = args.model / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    backup = args.model / "training_report_prerecalib.json"
    if not backup.exists():
        shutil.copy2(report_path, backup)
        print(f"\n  Backed up original report -> {backup.name}")
    report["threshold"] = new_thr
    report["threshold_strategy"] = f"recalibrated:{args.strategy}"
    report.setdefault("recalibration_history", []).append({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": str(args.data),
        "old_threshold": old_thr,
        "new_threshold": new_thr,
        "strategy": args.strategy,
        "detail": detail,
    })
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Updated       : {report_path.name}  (threshold {old_thr:.6f} -> {new_thr:.6f})")
    print("=" * 66)
    print("  Done. Restart the API (or call /api/model/reload) to apply.")
    print("=" * 66)


if __name__ == "__main__":
    main()
