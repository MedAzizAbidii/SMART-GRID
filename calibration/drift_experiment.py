"""
calibration/drift_experiment.py — Part A.4: calibration under drift.

Direct link to the Phase-3 robustness finding: any global feature-space shift
>=0.25 sigma saturated the DETECTOR's false-positive rate to 100% (frozen
threshold + frozen model). This experiment asks the calibration-layer version
of the same question: does a calibrator FIT ON CLEAN VALIDATION data stay
calibrated once the TEST distribution drifts, and does re-fitting the
calibrator (mirroring recalibrate.py's Phase-0 approach: refit on new
baseline data, model/scaler untouched) restore both calibration AND recover
the detector's false-positive rate?

Reuses robustness.perturbations.data_drift (no duplication).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibration.common import get_val_test_scores, recon_scores
from calibration.methods import METHODS, reliability_bins, \
    expected_calibration_error, max_calibration_error_robust, brier_score
from robustness.perturbations import data_drift

HERE = Path(__file__).resolve().parent
RES, PLOTS, REPORTS = HERE / "results", HERE / "plots", HERE / "reports"
_PAL = {"good": "#2E9E68", "bad": "#C1443A", "acc": "#2C6FA6"}
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

DRIFT_LEVEL = 0.5   # matches robustness Phase-3 "saturated" regime (>=0.25 sigma)
BEST_METHOD_KEY = "platt_raw"   # from compare.py's measured recommendation


def main():
    RES.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(parents=True, exist_ok=True)
    d = get_val_test_scores()
    va_s, va_l = d["va_scores"], d["va_labels"]
    model, threshold = d["model"], d["threshold"]

    print("=" * 64)
    print(f"  CALIBRATION UNDER DRIFT (level={DRIFT_LEVEL} sigma, matches Phase-3 saturation regime)")
    print("=" * 64)

    # need the actual TEST sequences (not just their scores) to drift them
    from calibration.common import load_splits
    tr, va, te, cols, scaler, frame = load_splits()
    te_seqs, te_l = te[0], te[1]

    te_s_clean = recon_scores(model, te_seqs)
    te_seqs_drift = data_drift(te_seqs, DRIFT_LEVEL, seed=42)
    te_s_drift = recon_scores(model, te_seqs_drift)

    # 1. calibrator fit on CLEAN VAL, applied AS-IS to drifted TEST scores
    stale = METHODS[BEST_METHOD_KEY]().fit(va_s, va_l)
    p_clean = stale.predict_proba(te_s_clean)
    p_stale_on_drift = stale.predict_proba(te_s_drift)

    # detector-level FPR before/after drift, with the STALE (pre-drift) threshold
    pred_clean = (te_s_clean >= threshold).astype(int)
    pred_drift_stale = (te_s_drift >= threshold).astype(int)
    fpr_clean = float((pred_clean[te_l == 0] == 1).mean())
    fpr_drift_stale = float((pred_drift_stale[te_l == 0] == 1).mean())

    # 2. RECALIBRATION: refit calibrator + threshold on the DRIFTED distribution's
    #    own statistics (the recalibrate.py approach — a small "new baseline"
    #    sample from the drifted stream, model/scaler untouched). We simulate
    #    having access to a drifted VALIDATION-like sample by drifting the
    #    real validation split identically (same generative shift a real
    #    deployment would experience uniformly).
    va_seqs_drift = data_drift(va[0], DRIFT_LEVEL, seed=43)
    va_s_drift = recon_scores(model, va_seqs_drift)
    recal = METHODS[BEST_METHOD_KEY]().fit(va_s_drift, va[1])
    p_recal_on_drift = recal.predict_proba(te_s_drift)

    from calibration.methods import _platt_gd
    # recalibrated threshold: same conservative rule recalibrate.py uses (percentile)
    new_threshold = float(np.percentile(va_s_drift[va[1] == 0], 99.0))
    pred_drift_recal = (te_s_drift >= new_threshold).astype(int)
    fpr_drift_recal = float((pred_drift_recal[te_l == 0] == 1).mean())

    metrics = {
        "clean": {"ece": expected_calibration_error(p_clean, te_l),
                 "mce_robust": max_calibration_error_robust(p_clean, te_l, min_count=10),
                 "brier": brier_score(p_clean, te_l), "fpr": fpr_clean},
        "drift_stale_calibrator": {"ece": expected_calibration_error(p_stale_on_drift, te_l),
                                   "mce_robust": max_calibration_error_robust(p_stale_on_drift, te_l, min_count=10),
                                   "brier": brier_score(p_stale_on_drift, te_l), "fpr": fpr_drift_stale},
        "drift_recalibrated": {"ece": expected_calibration_error(p_recal_on_drift, te_l),
                               "mce_robust": max_calibration_error_robust(p_recal_on_drift, te_l, min_count=10),
                               "brier": brier_score(p_recal_on_drift, te_l), "fpr": fpr_drift_recal},
    }
    for k, v in metrics.items():
        print(f"  [{k:<24}] ECE={v['ece']:.4f} MCE(robust)={v['mce_robust']:.4f} "
              f"Brier={v['brier']:.4f} FPR={v['fpr']:.4f}")

    fpr_recovered_pct = 100 * (fpr_drift_stale - fpr_drift_recal) / max(fpr_drift_stale - fpr_clean, 1e-9)
    print(f"\n  FPR under clean: {fpr_clean:.4f}")
    print(f"  FPR under drift (stale calibration/threshold): {fpr_drift_stale:.4f}  <- Phase-3 saturation")
    print(f"  FPR under drift (RECALIBRATED): {fpr_drift_recal:.4f}")
    print(f"  FPR degradation RECOVERED by recalibration: {fpr_recovered_pct:.1f}%")

    # reliability diagrams: clean / drift-stale / drift-recalibrated
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, (name, probs) in zip(axes, (("Clean (fit+eval both clean)", p_clean),
                                        ("Drift, STALE calibrator", p_stale_on_drift),
                                        ("Drift, RECALIBRATED", p_recal_on_drift))):
        mids, conf, acc, count = reliability_bins(probs, te_l)
        valid = count > 0
        ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
        ax.plot(conf[valid], acc[valid], "o-", color=_PAL["acc"])
        ax.set_title(name, fontsize=9); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xlabel("predicted probability"); ax.set_ylabel("observed attack fraction")
    fig.suptitle(f"Calibration under drift (level={DRIFT_LEVEL}σ) — the recalibration fix", y=1.03)
    fig.tight_layout(); fig.savefig(PLOTS / "drift_calibration.png"); plt.close(fig)

    # FPR bar chart
    fig, ax = plt.subplots(figsize=(6, 4.2))
    names = ["Clean", "Drift\n(stale)", "Drift\n(recalibrated)"]
    vals = [fpr_clean, fpr_drift_stale, fpr_drift_recal]
    ax.bar(names, vals, color=[_PAL["good"], _PAL["bad"], _PAL["acc"]])
    ax.set_ylabel("False Positive Rate"); ax.set_title("FPR recovery via recalibration under drift")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    fig.tight_layout(); fig.savefig(PLOTS / "drift_fpr_recovery.png"); plt.close(fig)

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "drift_calibration_evidence.json").write_text(json.dumps({
        "drift_level_sigma": DRIFT_LEVEL, "method": BEST_METHOD_KEY,
        "metrics": metrics, "fpr_recovered_pct": fpr_recovered_pct,
        "new_threshold_after_recalibration": new_threshold,
    }, indent=2))
    print(f"\n  Evidence: {REPORTS / 'drift_calibration_evidence.json'}")
    print(f"  Plots: {PLOTS / 'drift_calibration.png'}, {PLOTS / 'drift_fpr_recovery.png'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
