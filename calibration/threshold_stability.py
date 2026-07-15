"""
calibration/threshold_stability.py — Part B.9: threshold-stability analysis.

Two complementary views:
  1. How far does the CHOSEN threshold move across CV folds/seeds? (reuses
     the thresholds already fit inside calibration/cv.py's k=5/k=10/repeated
     runs — no re-fitting, just aggregation.)
  2. How sensitive are F1/FPR to a SMALL perturbation of the frozen
     production model's own threshold? (a local sensitivity sweep around the
     production operating point, on the untouched leak-free TEST split.)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibration.common import get_val_test_scores
from benchmark.metrics import all_metrics

HERE = Path(__file__).resolve().parent
RES, PLOTS = HERE / "results", HERE / "plots"
_PAL = {"acc": "#2C6FA6", "f1": "#2C6FA6", "fpr": "#C1443A"}
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})


def threshold_variability():
    cv_path = RES / "cv_results.json"
    if not cv_path.exists():
        print("  [skip] cv_results.json not found — run calibration.cv first")
        return None
    d = json.loads(cv_path.read_text())
    out = {}
    for key in ("k5", "k10"):
        thr = [f["threshold"] for f in d[key]["folds"]]
        out[key] = {"thresholds": thr, "mean": float(np.mean(thr)), "std": float(np.std(thr)),
                   "cv_pct": float(np.std(thr) / np.mean(thr) * 100) if np.mean(thr) else None}
        print(f"  {key}: threshold = {out[key]['mean']:.5f} +/- {out[key]['std']:.5f} "
              f"(CV%={out[key]['cv_pct']:.1f})")
    return out


def local_sensitivity(n_points=41, span=0.5):
    """Sweep the threshold +/- `span` (fraction) around the frozen model's own
    operating point on the untouched TEST split; plot F1 and FPR response."""
    d = get_val_test_scores()
    te_s, te_l, base_thr = d["te_scores"], d["te_labels"], d["threshold"]
    grid = base_thr * np.linspace(1 - span, 1 + span, n_points)
    f1s, fprs, recalls, precisions = [], [], [], []
    for t in grid:
        pred = (te_s >= t).astype(int)
        m = all_metrics(te_l, te_s, pred)
        f1s.append(m["f1"]); fprs.append(m["fpr"]); recalls.append(m["recall"]); precisions.append(m["precision"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    rel = (grid - base_thr) / base_thr * 100
    axes[0].plot(rel, f1s, "o-", color=_PAL["f1"], ms=3)
    axes[0].axvline(0, color="k", ls="--", lw=1, label="production threshold")
    axes[0].set_xlabel("threshold perturbation (%)"); axes[0].set_ylabel("F1")
    axes[0].set_title("F1 sensitivity to threshold"); axes[0].legend(fontsize=8)
    axes[1].plot(rel, fprs, "o-", color=_PAL["fpr"], ms=3)
    axes[1].axvline(0, color="k", ls="--", lw=1, label="production threshold")
    axes[1].set_xlabel("threshold perturbation (%)"); axes[1].set_ylabel("FPR")
    axes[1].set_title("FPR sensitivity to threshold"); axes[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(PLOTS / "threshold_sensitivity.png"); plt.close(fig)

    # local slope at the operating point (finite difference) — a single number
    # summarising fragility: how much F1/FPR moves per 1% threshold change
    mid = n_points // 2
    d_f1 = (f1s[mid + 1] - f1s[mid - 1]) / (rel[mid + 1] - rel[mid - 1])
    d_fpr = (fprs[mid + 1] - fprs[mid - 1]) / (rel[mid + 1] - rel[mid - 1])
    print(f"  Local sensitivity at production threshold: "
          f"dF1/d(1% thr) = {d_f1:.4f}, dFPR/d(1% thr) = {d_fpr:.4f}")
    return {"base_threshold": base_thr, "grid_pct": rel.tolist(), "f1": f1s, "fpr": fprs,
            "recall": recalls, "precision": precisions,
            "local_slope_f1_per_pct": d_f1, "local_slope_fpr_per_pct": d_fpr}


def main():
    RES.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  THRESHOLD STABILITY ANALYSIS")
    print("=" * 60)
    print("\n  -- Threshold variability across CV folds --")
    variability = threshold_variability()
    print("\n  -- Local F1/FPR sensitivity around production threshold --")
    sensitivity = local_sensitivity()

    (RES / "threshold_stability.json").write_text(json.dumps({
        "cv_variability": variability, "local_sensitivity": sensitivity,
    }, indent=2))
    print(f"\n  Saved: {RES / 'threshold_stability.json'}")
    print(f"  Plot: {PLOTS / 'threshold_sensitivity.png'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
