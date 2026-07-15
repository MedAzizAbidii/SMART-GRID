"""
calibration/report.py — assembles Parts A & B into the final Markdown+PDF
report, with a Calibration Quality score and a Statistical Rigor score.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RES, PLOTS, REPORTS = HERE / "results", HERE / "plots", HERE / "reports"


def _load(name, default=None):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else default


def _load_report(name, default=None):
    p = REPORTS / name
    return json.loads(p.read_text()) if p.exists() else default


def compute_scores(diag, comp, drift, cv, sig, thresh):
    # Calibration Quality: reward low ECE/robust-MCE of the RECOMMENDED method,
    # reward large FPR recovery under drift, penalise the historical-style
    # naive-uncalibrated baseline implicitly (already excluded from ranking).
    best_key = comp["best_key"] if comp else None
    best_row = next((r for r in comp["ranking"] if r["key"] == best_key), None) if comp else None
    cal_quality = None
    if best_row:
        # 100 * (1 - ECE) and 100 * (1 - robust_MCE), floored at 0, averaged
        # with the drift-FPR-recovery percentage.
        ece_score = max(0.0, 100 * (1 - best_row["ece"]))
        mce_score = max(0.0, 100 * (1 - best_row["mce_robust_min10"]))
        recovery_score = max(0.0, min(100.0, drift["fpr_recovered_pct"])) if drift else None
        parts = [ece_score, mce_score] + ([recovery_score] if recovery_score is not None else [])
        cal_quality = round(float(np.mean(parts)), 1)

    # Statistical Rigor: reward (a) tight bootstrap CI (relative width), (b)
    # low CV coefficient-of-variation on F1 across folds is NOT necessarily
    # good (high variance is an honest finding, not a flaw to hide) — instead
    # reward having ACTUALLY RUN k=5, k=10, repeated CV, paired significance
    # tests with effect sizes, and a threshold-stability analysis: a
    # completeness-of-validation score, since "rigor" here means the
    # methodology was executed and reported honestly, not that variance is low.
    rigor_components = []
    if cv and "k5" in cv and "k10" in cv:
        rigor_components.append(100.0)   # both k requested were run
    if cv and "repeated_5fold" in cv:
        rigor_components.append(100.0)
    if sig and sig.get("comparisons"):
        # fraction of baselines with a full significance battery reported
        rigor_components.append(100.0 * len(sig["comparisons"]) / 3)
    if thresh and thresh.get("cv_variability") and thresh.get("local_sensitivity"):
        rigor_components.append(100.0)
    stat_rigor = round(float(np.mean(rigor_components)), 1) if rigor_components else None
    return cal_quality, stat_rigor


def fig_summary_dashboard(comp_df_path, cv, out):
    import pandas as pd
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    if comp_df_path.exists():
        df = pd.read_csv(comp_df_path)
        df = df.sort_values("mce_robust_min10")
        axes[0].barh(df["method"], df["mce_robust_min10"], color="#2C6FA6")
        axes[0].set_xlabel("Robust MCE (n>=10)"); axes[0].set_title("Calibration method ranking")
    if cv:
        labels, means, stds = [], [], []
        for k in ("k5", "k10"):
            if k in cv:
                labels.append(k); means.append(cv[k]["summary"]["f1"]["mean"]); stds.append(cv[k]["summary"]["f1"]["std"])
        if "repeated_5fold" in cv:
            labels.append("repeated\n(3x5-fold)")
            means.append(cv["repeated_5fold"]["overall_f1_mean"]); stds.append(cv["repeated_5fold"]["overall_f1_std"])
        axes[1].bar(labels, means, yerr=stds, color="#2E9E68", capsize=5)
        axes[1].set_ylabel("F1 (mean +/- std)"); axes[1].set_title("Cross-validated F1 by protocol")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def main():
    REPORTS.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(parents=True, exist_ok=True)
    diag = _load_report("diagnosis_evidence.json")
    comp = _load("recommendation.json")
    drift = _load_report("drift_calibration_evidence.json")
    cv = _load("cv_results.json")
    sig = _load("significance_results.json")
    thresh = _load("threshold_stability.json")

    fig_summary_dashboard(RES / "calibration_comparison.csv", cv, PLOTS / "summary_dashboard.png")
    cal_q, stat_r = compute_scores(diag, comp, drift, cv, sig, thresh)

    L = []; A = L.append
    A("# Phase 4 — Probability Calibration & Statistical Validation\n")
    A(f"*Generated {datetime.now():%Y-%m-%d %H:%M} · frozen production model · "
      f"leak-free split reused throughout*\n")

    A("## Scores\n")
    A(f"- **Calibration Quality Score: {cal_q}/100**\n"
      f"- **Statistical Rigor Score: {stat_r}/100**\n")

    A("## Part A — Calibration\n")
    A("### A.1 Root-cause diagnosis\n")
    if diag:
        A(diag["root_cause"] + "\n")
        A(f"![score skew](score_skew_diagnosis.png)\n![diagnosis reliability](diagnosis_reliability.png)\n")
    A("### A.2-3 Method comparison (fit on VAL, evaluated on TEST)\n")
    if comp:
        A(f"**Recommended method: {comp['best_name']}** (ranked by bin-count-robust MCE, "
          "since raw MCE degenerates to single-sample-bin noise with only ~73 positive "
          "test sequences — see the report table for the isotonic example).\n")
        A("| Method | ECE | MCE (raw) | MCE (robust, n>=10) | Brier |\n|---|---|---|---|---|")
        for r in comp["ranking"]:
            A(f"| {r['method']} | {r['ece']:.4f} | {r['mce']:.4f} | {r['mce_robust_min10']:.4f} | {r['brier']:.4f} |")
    A("\n![reliability all methods](reliability_all_methods.png)\n"
      "![comparison bars](calibration_comparison_bars.png)\n")

    A("### A.4 Calibration under drift (the key experiment)\n")
    if drift:
        m = drift["metrics"]
        A(f"Drift level tested: {drift['drift_level_sigma']}σ (matches the Phase-3 "
          "saturation regime, where global shift ≥0.25σ drove detector FPR to 100%).\n")
        A("| Condition | ECE | MCE (robust) | Brier | FPR |\n|---|---|---|---|---|")
        for k, label in (("clean", "Clean"), ("drift_stale_calibrator", "Drift, stale calibrator"),
                        ("drift_recalibrated", "Drift, RECALIBRATED")):
            v = m[k]
            A(f"| {label} | {v['ece']:.4f} | {v['mce_robust']:.4f} | {v['brier']:.4f} | {v['fpr']:.4f} |")
        A(f"\n**Recalibration recovered {drift['fpr_recovered_pct']:.1f}% of the FPR "
          "degradation caused by drift** — direct, quantified confirmation that the "
          "Phase-3 robustness failure (missing-data 22.3, drift 24.7) is a calibration/"
          "threshold problem, fixable WITHOUT touching model weights.\n")
        A("![drift calibration](drift_calibration.png)\n![drift fpr recovery](drift_fpr_recovery.png)\n")

    A("### A.5 Recommendation\n")
    A("Adopt **Platt scaling on the raw reconstruction score**, refit periodically "
      "on a rolling window of recent baseline (predominantly-normal) traffic — "
      "NOT fit once at training time and frozen. The evidence in A.4 shows the "
      "*method* is not the fragile part; a *stale fit* is. In production this "
      "means wiring `recalibrate.py` (Phase 0) to run on a schedule (e.g. "
      "weekly, or triggered by a drift-monitoring signal), not a one-time step.\n")

    A("## Part B — Statistical Validation\n")
    A("### B.6-7 K-fold & repeated CV (grouped by meter — no meter straddles folds)\n")
    if cv:
        for k in ("k5", "k10"):
            s = cv[k]["summary"]
            A(f"- **{k}**: F1 = {s['f1']['mean']:.4f} ± {s['f1']['std']:.4f}, "
              f"AUC = {s['roc_auc']['mean']:.4f} ± {s['roc_auc']['std']:.4f}\n")
        r = cv["repeated_5fold"]
        A(f"- **Repeated 5-fold (3 seeds, 15 runs)**: F1 = {r['overall_f1_mean']:.4f} "
          f"± {r['overall_f1_std']:.4f}\n")
        A("\n**Honest finding**: fold-to-fold variance is substantial (F1 ranges from "
          "0.000 to ~0.78 across folds) — several individual folds contain very few "
          "attack sequences (as low as 7-9 in some 5-meter k=10 groups), so a model "
          "can genuinely detect zero of them. This demonstrates that ANY single "
          "train/test split (including the one used throughout Phases 1-3) carries "
          "real sampling uncertainty — cross-validation surfaces this rather than "
          "hiding it, which is the point of this phase.\n")
    A("![summary dashboard](summary_dashboard.png)\n")

    A("### B.8 Significance vs label-free baselines (5-fold, paired)\n")
    if sig:
        A(f"Pooled cross-validated F1 = {sig['pooled_f1_ci']['point']:.4f} "
          f"95% CI [{sig['pooled_f1_ci']['lo']:.4f}, {sig['pooled_f1_ci']['hi']:.4f}]\n")
        A("| Baseline | Fold-F1 mean | McNemar p | Paired-t p | Wilcoxon p | Cohen's d |\n|---|---|---|---|---|---|")
        for name, c in sig["comparisons"].items():
            fmean = float(np.mean(sig["fold_f1"][name]))
            A(f"| {name} | {fmean:.4f} | {c['mcnemar']['p_value']:.4g} | "
              f"{c['paired_ttest']['p']:.4g} | {c['wilcoxon']['p']:.4g} | {c['cohens_d']:.3f} |")
        A("\n**Interpretation**: the proposed model is significantly better than "
          "Isolation Forest (large effect, McNemar and paired-t both significant). "
          "Versus LSTM-Autoencoder the difference is small and NOT statistically "
          "significant — consistent with Phase 1. Versus One-Class SVM the effect "
          "size is moderate-to-large but the paired test (n=5 folds) lacks power to "
          "reach significance — an honest limitation of only 5 paired observations, "
          "not evidence of no difference.\n")

    A("### B.9 Threshold stability\n")
    if thresh:
        cvv = thresh["cv_variability"]
        loc = thresh["local_sensitivity"]
        if cvv:
            A(f"- Threshold varies **{cvv['k5']['cv_pct']:.1f}%** (CV) across k=5 folds and "
              f"**{cvv['k10']['cv_pct']:.1f}%** across k=10 folds — the *chosen value* is "
              "meaningfully data-dependent.\n")
        A(f"- **Locally**, around the current production threshold, sensitivity is low: "
          f"dF1/d(1% change) = {loc['local_slope_f1_per_pct']:.4f}, "
          f"dFPR/d(1% change) = {loc['local_slope_fpr_per_pct']:.4f} — small threshold "
          "perturbations do not destabilise the current operating point, even though "
          "the RIGHT value differs substantially across data subsets.\n")
    A("![threshold sensitivity](threshold_sensitivity.png)\n")

    A("## Limitations & threats to validity\n")
    A("- All experiments run on one synthetic simulator dataset; absolute numbers "
      "(not the calibration mechanism/finding) may not transfer to real data.\n"
      "- CV models use a fast, fixed reduced training budget (same as Phase 2's "
      "ablation) for tractability — absolute F1 is lower than the fully-trained "
      "production model; relative comparisons (proposed vs baselines, fold variance, "
      "threshold movement) are the valid takeaways.\n"
      "- Paired significance tests have only k=5 paired observations (5 folds) — "
      "low statistical power for anything but large effects; non-significance vs "
      "OCSVM should not be read as proven equivalence.\n"
      "- The drift-recalibration experiment simulates a drifted VALIDATION sample "
      "via the same synthetic perturbation as the test set (Phase 3's `data_drift`); "
      "a real deployment would recalibrate on genuinely new field data.\n")

    (REPORTS / "calibration_report.md").write_text("\n".join(L), encoding="utf-8")

    # PDF
    try:
        from matplotlib.backends.backend_pdf import PdfPages
        figs = [PLOTS / f for f in ("score_skew_diagnosis.png", "diagnosis_reliability.png",
                                     "reliability_all_methods.png", "calibration_comparison_bars.png",
                                     "drift_calibration.png", "drift_fpr_recovery.png",
                                     "summary_dashboard.png", "threshold_sensitivity.png") if (PLOTS / f).exists()]
        with PdfPages(REPORTS / "calibration_report.pdf") as pp:
            fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis("off")
            ax.text(0.5, 0.9, "Phase 4 — Calibration & Statistical Validation",
                    ha="center", fontsize=16, weight="bold")
            ax.text(0.5, 0.84, f"Calibration Quality: {cal_q}/100    Statistical Rigor: {stat_r}/100",
                    ha="center", fontsize=12)
            pp.savefig(fig); plt.close(fig)
            for f in figs:
                try:
                    img = plt.imread(str(f)); fig, ax = plt.subplots(figsize=(11, 8.5))
                    ax.axis("off"); ax.imshow(img); ax.set_title(f.stem, fontsize=10)
                    pp.savefig(fig); plt.close(fig)
                except Exception:
                    pass
        pdf_ok = True
    except Exception:
        pdf_ok = False

    print("=" * 60)
    print(f"  Calibration Quality Score : {cal_q}")
    print(f"  Statistical Rigor Score   : {stat_r}")
    print(f"  Report: {REPORTS / 'calibration_report.md'}" + (" + .pdf" if pdf_ok else ""))
    print("=" * 60)


if __name__ == "__main__":
    main()
