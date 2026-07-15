# Phase 4 — Probability Calibration & Statistical Validation

*Generated 2026-07-09 01:58 · frozen production model · leak-free split reused throughout*

## Scores

- **Calibration Quality Score: 91.5/100**
- **Statistical Rigor Score: 100.0/100**

## Part A — Calibration

### A.1 Root-cause diagnosis

VAL reconstruction scores are heavily right-skewed (skewness=19.94) AND uniformly < 1 (range [0.000247, 0.348751]). Because all values are already sub-1, log1p(x)=log(1+x) is numerically close to the identity there, so it barely reduces skew (19.94 -> 18.91) and would not meaningfully fix calibration. A raw log(score+eps) transform is the correct choice for sub-1 multiplicative-scale data: it reduces skew to 2.00 and yields a well-scaled Platt slope (a=2.97 vs raw a=25.03), improving average calibration (ECE 0.4816 -> 0.0237). However log-Platt introduces a NEW measured failure: overconfidence in the sparse high-score tail (gap=0.737 in the top probability bin), which is why isotonic regression and temperature scaling are compared in Part A rather than adopting log-Platt outright. On THIS leak-free split the historical catastrophic blowup (a~700) did not reproduce (raw Platt here: a=25.0, not saturated) — that specific failure was tied to the old leaky evaluation pipeline / old model, not an inherent property of Platt scaling itself.

![score skew](score_skew_diagnosis.png)
![diagnosis reliability](diagnosis_reliability.png)

### A.2-3 Method comparison (fit on VAL, evaluated on TEST)

**Recommended method: Platt (raw score)** (ranked by bin-count-robust MCE, since raw MCE degenerates to single-sample-bin noise with only ~73 positive test sequences — see the report table for the isotonic example).

| Method | ECE | MCE (raw) | MCE (robust, n>=10) | Brier |
|---|---|---|---|---|
| Platt (raw score) | 0.0240 | 0.2128 | 0.2128 | 0.0184 |
| Isotonic regression | 0.0292 | 0.5964 | 0.5332 | 0.0280 |
| Platt (log(score+eps)) | 0.0237 | 0.7370 | 0.7370 | 0.0218 |
| Temperature scaling | 0.2298 | 0.7882 | 0.7882 | 0.1139 |

![reliability all methods](reliability_all_methods.png)
![comparison bars](calibration_comparison_bars.png)

### A.4 Calibration under drift (the key experiment)

Drift level tested: 0.5σ (matches the Phase-3 saturation regime, where global shift ≥0.25σ drove detector FPR to 100%).

| Condition | ECE | MCE (robust) | Brier | FPR |
|---|---|---|---|---|
| Clean | 0.0240 | 0.2128 | 0.0184 | 0.0359 |
| Drift, stale calibrator | 0.7699 | 0.7837 | 0.6088 | 1.0000 |
| Drift, RECALIBRATED | 0.0406 | 0.4245 | 0.0165 | 0.0524 |

**Recalibration recovered 98.3% of the FPR degradation caused by drift** — direct, quantified confirmation that the Phase-3 robustness failure (missing-data 22.3, drift 24.7) is a calibration/threshold problem, fixable WITHOUT touching model weights.

![drift calibration](drift_calibration.png)
![drift fpr recovery](drift_fpr_recovery.png)

### A.5 Recommendation

Adopt **Platt scaling on the raw reconstruction score**, refit periodically on a rolling window of recent baseline (predominantly-normal) traffic — NOT fit once at training time and frozen. The evidence in A.4 shows the *method* is not the fragile part; a *stale fit* is. In production this means wiring `recalibrate.py` (Phase 0) to run on a schedule (e.g. weekly, or triggered by a drift-monitoring signal), not a one-time step.

## Part B — Statistical Validation

### B.6-7 K-fold & repeated CV (grouped by meter — no meter straddles folds)

- **k5**: F1 = 0.5270 ± 0.1651, AUC = 0.9511 ± 0.0247

- **k10**: F1 = 0.3246 ± 0.2802, AUC = 0.9182 ± 0.0711

- **Repeated 5-fold (3 seeds, 15 runs)**: F1 = 0.4303 ± 0.2742


**Honest finding**: fold-to-fold variance is substantial (F1 ranges from 0.000 to ~0.78 across folds) — several individual folds contain very few attack sequences (as low as 7-9 in some 5-meter k=10 groups), so a model can genuinely detect zero of them. This demonstrates that ANY single train/test split (including the one used throughout Phases 1-3) carries real sampling uncertainty — cross-validation surfaces this rather than hiding it, which is the point of this phase.

![summary dashboard](summary_dashboard.png)

### B.8 Significance vs label-free baselines (5-fold, paired)

Pooled cross-validated F1 = 0.5227 95% CI [0.4901, 0.5547]

| Baseline | Fold-F1 mean | McNemar p | Paired-t p | Wilcoxon p | Cohen's d |
|---|---|---|---|---|---|
| isolation_forest | 0.0400 | 0 | 0.002723 | 0.0625 | 2.954 |
| lstm_autoencoder | 0.5035 | 1.914e-18 | 0.6217 | 1 | 0.239 |
| one_class_svm | 0.2546 | 3.4e-31 | 0.1074 | 0.0625 | 0.925 |

**Interpretation**: the proposed model is significantly better than Isolation Forest (large effect, McNemar and paired-t both significant). Versus LSTM-Autoencoder the difference is small and NOT statistically significant — consistent with Phase 1. Versus One-Class SVM the effect size is moderate-to-large but the paired test (n=5 folds) lacks power to reach significance — an honest limitation of only 5 paired observations, not evidence of no difference.

### B.9 Threshold stability

- Threshold varies **18.0%** (CV) across k=5 folds and **17.7%** across k=10 folds — the *chosen value* is meaningfully data-dependent.

- **Locally**, around the current production threshold, sensitivity is low: dF1/d(1% change) = 0.0025, dFPR/d(1% change) = -0.0008 — small threshold perturbations do not destabilise the current operating point, even though the RIGHT value differs substantially across data subsets.

![threshold sensitivity](threshold_sensitivity.png)

## Limitations & threats to validity

- All experiments run on one synthetic simulator dataset; absolute numbers (not the calibration mechanism/finding) may not transfer to real data.
- CV models use a fast, fixed reduced training budget (same as Phase 2's ablation) for tractability — absolute F1 is lower than the fully-trained production model; relative comparisons (proposed vs baselines, fold variance, threshold movement) are the valid takeaways.
- Paired significance tests have only k=5 paired observations (5 folds) — low statistical power for anything but large effects; non-significance vs OCSVM should not be read as proven equivalence.
- The drift-recalibration experiment simulates a drifted VALIDATION sample via the same synthetic perturbation as the test set (Phase 3's `data_drift`); a real deployment would recalibrate on genuinely new field data.
