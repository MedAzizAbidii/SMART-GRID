"""
calibration/diagnose.py — Part A.1: diagnose why Platt scaling is broken.

Attempts to reproduce the historical failure (the pre-existing
calibrate_detector.py: Platt fit directly on raw reconstruction scores,
MCE got WORSE, a≈300-700 — see outputs/*_old9col_backup/calibration_params.json
for the preserved historical evidence) on the CURRENT frozen model and the
NEW leak-free VAL/TEST split. Measured result, reported honestly: on this
split/model, a raw Platt fit is NOT catastrophically broken (a≈25, MCE=0.21,
better than the uncalibrated baseline) — the extreme historical blowup was
specific to the old leaky evaluation pipeline / old 9-column model and does
not reproduce identically here. What IS confirmed by measurement is the
underlying mechanism the historical bug exploited, refined to two precise,
verified findings:
  1. log1p(score) is NEARLY A NO-OP here: every reconstruction score is < 1
     (measured range ~2.5e-4 to 0.35), and log1p(x) = log(1+x) ≈ x for x<<1.
     Skewness barely moves (19.94 -> 18.91). An earlier attempt at "fixing"
     calibration with log1p would not have helped, which is itself a finding.
  2. A raw log(score+eps) transform DOES fix the skew (19.94 -> ~2.0) and
     the average calibration error (ECE), because it is the correct
     transform for sub-1, multiplicative-scale data — but it introduces a
     NEW, measured failure mode: overconfidence in the sparse high-score
     tail (one high-probability bin predicts ~98% confidence while the true
     attack fraction there is only ~24%), which is what MCE is designed to
     catch. This is why Part A compares log-Platt against isotonic
     regression and temperature scaling rather than declaring log-Platt
     sufficient on its own.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import skew
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibration.common import get_val_test_scores
from calibration.methods import PlattRaw, PlattLog, reliability_bins, \
    expected_calibration_error, max_calibration_error, brier_score

HERE = Path(__file__).resolve().parent
PLOTS, REPORTS = HERE / "plots", HERE / "reports"
_PAL = {"good": "#2E9E68", "bad": "#C1443A", "acc": "#2C6FA6"}
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})


def percentile_rank(scores):
    order = np.argsort(scores)
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1) / len(scores)
    return ranks


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    d = get_val_test_scores()
    va_s, va_l, te_s, te_l = d["va_scores"], d["va_labels"], d["te_scores"], d["te_labels"]

    print("=" * 64)
    print("  DIAGNOSIS: why the current Platt scaling is broken")
    print("=" * 64)

    # ── 1. raw score distribution (skew) ─────────────────────────────────────
    eps = 1e-6
    sk_raw = float(skew(va_s))
    sk_log1p = float(skew(np.log1p(va_s)))
    sk_log = float(skew(np.log(va_s + eps)))
    print(f"  VAL raw-score skewness    : {sk_raw:.2f}   (>>0 = heavy right tail)")
    print(f"  VAL score range           : [{va_s.min():.6f}, {va_s.max():.6f}]  (all < 1)")
    print(f"  VAL log1p(score) skewness : {sk_log1p:.2f}  (barely moved -> log1p is ~a no-op here)")
    print(f"  VAL log(score+eps) skewness: {sk_log:.2f}   (correct transform for sub-1 data)")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    axes[0].hist(va_s[va_l == 0], bins=60, color=_PAL["good"], alpha=0.6, label="normal", log=True)
    axes[0].hist(va_s[va_l == 1], bins=60, color=_PAL["bad"], alpha=0.6, label="attack", log=True)
    axes[0].set_title(f"Raw score (skew={sk_raw:.2f})"); axes[0].set_xlabel("reconstruction score")
    axes[0].legend(fontsize=8)
    axes[1].hist(np.log1p(va_s[va_l == 0]), bins=60, color=_PAL["good"], alpha=0.6, label="normal")
    axes[1].hist(np.log1p(va_s[va_l == 1]), bins=60, color=_PAL["bad"], alpha=0.6, label="attack")
    axes[1].set_title(f"log1p(score) (skew={sk_log1p:.2f}) — ~no-op"); axes[1].set_xlabel("log1p(score)")
    axes[1].legend(fontsize=8)
    axes[2].hist(np.log(va_s[va_l == 0] + eps), bins=60, color=_PAL["good"], alpha=0.6, label="normal")
    axes[2].hist(np.log(va_s[va_l == 1] + eps), bins=60, color=_PAL["bad"], alpha=0.6, label="attack")
    axes[2].set_title(f"log(score+eps) (skew={sk_log:.2f}) — fixed"); axes[2].set_xlabel("log(score+eps)")
    axes[2].legend(fontsize=8)
    fig.suptitle("Root cause: scores are right-skewed AND all < 1, so log1p barely helps", y=1.02)
    fig.tight_layout(); fig.savefig(PLOTS / "score_skew_diagnosis.png"); plt.close(fig)

    # ── 2. reproduce the historical approach (VAL) -> evaluate on TEST ───────
    raw = PlattRaw().fit(va_s, va_l)
    log = PlattLog().fit(va_s, va_l)
    print(f"\n  Platt on RAW score      : a={raw.a:.3f}  b={raw.b:.4f}  (measured: NOT catastrophic here)")
    print(f"  Platt on log(score+eps) : a={log.a:.3f}  b={log.b:.4f}  (well-scaled slope after de-skewing)")

    p_raw = raw.predict_proba(te_s)
    p_log = log.predict_proba(te_s)
    p_pct = percentile_rank(te_s)   # naive "uncalibrated" baseline (percentile of raw score)

    metrics = {}
    for name, probs in (("uncalibrated_percentile", p_pct), ("platt_raw", p_raw), ("platt_log", p_log)):
        metrics[name] = {
            "ece": round(expected_calibration_error(probs, te_l), 4),
            "mce": round(max_calibration_error(probs, te_l), 4),
            "brier": round(brier_score(probs, te_l), 4),
        }
        print(f"  [{name:<24}] ECE={metrics[name]['ece']} MCE={metrics[name]['mce']} Brier={metrics[name]['brier']}")

    # tail-overconfidence check: highest-probability bin's conf vs actual acc
    mids, conf, acc, count = reliability_bins(p_log, te_l)
    valid = count > 0
    if valid.any():
        top_bin = np.where(valid)[0][-1]
        tail_gap = float(conf[top_bin] - acc[top_bin])
        print(f"  platt_log highest-probability bin: predicted={conf[top_bin]:.3f} "
              f"actual={acc[top_bin]:.3f} (n={count[top_bin]}) -> overconfidence gap={tail_gap:.3f}")
    else:
        tail_gap = None

    # ── 3. reliability diagrams ────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (name, probs) in zip(axes, (("Uncalibrated (percentile)", p_pct),
                                        ("Platt on RAW score", p_raw),
                                        ("Platt on log(score+eps)", p_log))):
        mids2, conf2, acc2, count2 = reliability_bins(probs, te_l)
        valid2 = count2 > 0
        ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
        ax.plot(conf2[valid2], acc2[valid2], "o-", color=_PAL["acc"])
        ax.set_title(name, fontsize=9.5); ax.set_xlabel("predicted probability")
        ax.set_ylabel("observed attack fraction"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.suptitle("Reliability diagrams — held-out TEST (fit on VAL only)", y=1.02)
    fig.tight_layout(); fig.savefig(PLOTS / "diagnosis_reliability.png"); plt.close(fig)

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "diagnosis_evidence.json").write_text(json.dumps({
        "score_range": [float(va_s.min()), float(va_s.max())],
        "skew_raw": sk_raw, "skew_log1p": sk_log1p, "skew_log_eps": sk_log,
        "platt_raw_a": raw.a, "platt_raw_b": raw.b,
        "platt_log_a": log.a, "platt_log_b": log.b,
        "metrics": metrics,
        "tail_overconfidence_gap_platt_log": tail_gap,
        "root_cause": (
            f"VAL reconstruction scores are heavily right-skewed (skewness={sk_raw:.2f}) "
            f"AND uniformly < 1 (range [{va_s.min():.6f}, {va_s.max():.6f}]). Because all "
            "values are already sub-1, log1p(x)=log(1+x) is numerically close to the "
            f"identity there, so it barely reduces skew ({sk_raw:.2f} -> {sk_log1p:.2f}) and "
            "would not meaningfully fix calibration. A raw log(score+eps) transform is the "
            f"correct choice for sub-1 multiplicative-scale data: it reduces skew to "
            f"{sk_log:.2f} and yields a well-scaled Platt slope (a={log.a:.2f} vs raw a="
            f"{raw.a:.2f}), improving average calibration "
            f"(ECE {metrics['uncalibrated_percentile']['ece']} -> {metrics['platt_log']['ece']}). "
            "However log-Platt introduces a NEW measured failure: overconfidence in the "
            f"sparse high-score tail (gap={tail_gap:.3f} in the top probability bin), which "
            "is why isotonic regression and temperature scaling are compared in Part A "
            "rather than adopting log-Platt outright. On THIS leak-free split the historical "
            f"catastrophic blowup (a~700) did not reproduce (raw Platt here: a={raw.a:.1f}, "
            "not saturated) — that specific failure was tied to the old leaky evaluation "
            "pipeline / old model, not an inherent property of Platt scaling itself."
        ),
    }, indent=2))
    print(f"\n  Evidence saved: {REPORTS / 'diagnosis_evidence.json'}")
    print(f"  Plots: {PLOTS / 'score_skew_diagnosis.png'}, {PLOTS / 'diagnosis_reliability.png'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
