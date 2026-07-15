"""
calibration/compare.py — Part A.2-3: fit all calibration methods on VALIDATION
only, evaluate ECE/MCE/Brier + reliability diagrams on the untouched TEST
split, and produce the comparison table that drives the recommendation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibration.common import get_val_test_scores
from calibration.methods import METHODS, reliability_bins, \
    expected_calibration_error, max_calibration_error, max_calibration_error_robust, brier_score
from calibration.diagnose import percentile_rank

HERE = Path(__file__).resolve().parent
RES, PLOTS, REPORTS = HERE / "results", HERE / "plots", HERE / "reports"
_PAL = ["#2C6FA6", "#C4892A", "#2E9E68", "#C1443A", "#7A5BA6"]
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})


def fit_all(va_s, va_l):
    fitted = {}
    for key, cls in METHODS.items():
        fitted[key] = cls().fit(va_s, va_l)
    return fitted


def evaluate_all(fitted, te_s, te_l, uncal_probs):
    rows = []
    all_probs = {"uncalibrated": uncal_probs}
    for key, method in fitted.items():
        p = method.predict_proba(te_s)
        all_probs[key] = p
        rows.append({
            "method": method.name, "key": key,
            "ece": expected_calibration_error(p, te_l),
            "mce": max_calibration_error(p, te_l),
            "mce_robust_min10": max_calibration_error_robust(p, te_l, min_count=10),
            "brier": brier_score(p, te_l),
        })
    rows.insert(0, {"method": "Uncalibrated (percentile)", "key": "uncalibrated",
                    "ece": expected_calibration_error(uncal_probs, te_l),
                    "mce": max_calibration_error(uncal_probs, te_l),
                    "mce_robust_min10": max_calibration_error_robust(uncal_probs, te_l, min_count=10),
                    "brier": brier_score(uncal_probs, te_l)})
    return pd.DataFrame(rows), all_probs


def fig_reliability_all(all_probs, te_l, out):
    n = len(all_probs)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n, 4.2))
    axes = np.atleast_1d(axes)
    for ax, (name, probs) in zip(axes, all_probs.items()):
        mids, conf, acc, count = reliability_bins(probs, te_l)
        valid = count > 0
        ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
        ax.plot(conf[valid], acc[valid], "o-", color=_PAL[0])
        ax.set_title(name, fontsize=8.5); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xlabel("predicted"); ax.set_ylabel("observed")
    fig.suptitle("Reliability diagrams — held-out TEST (all fit on VAL only)", y=1.03)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_comparison_bars(df, out):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, metric in zip(axes, ["ece", "mce", "brier"]):
        d = df.sort_values(metric)
        ax.barh(range(len(d)), d[metric], color=_PAL[1])
        ax.set_yticks(range(len(d))); ax.set_yticklabels(d["method"], fontsize=7.5)
        ax.set_xlabel(metric.upper()); ax.set_title(metric.upper())
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def recommend(df):
    """Pick the method minimising the bin-count-ROBUST MCE (raw MCE is a
    single-worst-bin statistic that measurably degenerates to noise here: with
    only ~73 positive test sequences several bins hold 1-3 samples — see
    compare.py output / report for the isotonic n=1-bin example). Tie-broken
    by ECE and Brier. Raw MCE is still reported alongside for standard
    comparability, but is not used to choose the winner."""
    cand = df[df["key"] != "uncalibrated"].copy()
    cand = cand.sort_values(["mce_robust_min10", "ece", "brier"])
    best = cand.iloc[0]
    return best["key"], best["method"], cand


def main():
    RES.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(parents=True, exist_ok=True)
    d = get_val_test_scores()
    va_s, va_l, te_s, te_l = d["va_scores"], d["va_labels"], d["te_scores"], d["te_labels"]

    print("=" * 64)
    print("  CALIBRATION METHOD COMPARISON (fit on VAL, eval on TEST)")
    print("=" * 64)
    fitted = fit_all(va_s, va_l)
    uncal = percentile_rank(te_s)
    df, all_probs = evaluate_all(fitted, te_s, te_l, uncal)
    print(df.round(4).to_string(index=False))

    fig_reliability_all(all_probs, te_l, PLOTS / "reliability_all_methods.png")
    fig_comparison_bars(df, PLOTS / "calibration_comparison_bars.png")

    df.to_csv(RES / "calibration_comparison.csv", index=False)
    try:
        df.to_excel(RES / "calibration_comparison.xlsx", index=False)
    except Exception:
        pass
    df.round(4).to_latex(RES / "calibration_comparison.tex", index=False,
                         caption="Calibration method comparison (held-out test).",
                         label="tab:calibration")

    best_key, best_name, ranked = recommend(df)
    print(f"\n  RECOMMENDATION (min robust-MCE[n>=10], tie-break ECE/Brier): {best_name}")
    (RES / "recommendation.json").write_text(json.dumps({
        "best_key": best_key, "best_name": best_name,
        "ranking": ranked[["key", "method", "mce", "mce_robust_min10", "ece", "brier"]].to_dict("records"),
    }, indent=2))

    print(f"\n  Table: {RES / 'calibration_comparison.csv'}")
    print(f"  Plots: {PLOTS / 'reliability_all_methods.png'}, {PLOTS / 'calibration_comparison_bars.png'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
