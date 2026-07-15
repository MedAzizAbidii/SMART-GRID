# Phase 4 — Probability Calibration & Statistical Validation

Fixes the calibration layer (identified in Phase 3 as the root cause of the
two weakest robustness dimensions) and statistically validates the headline
metrics. Frozen production model, leak-free split reused throughout.

## Run

```powershell
cd smartgrid_simulation
.\.venv\Scripts\python.exe -m calibration.diagnose             # A.1 root-cause diagnosis
.\.venv\Scripts\python.exe -m calibration.compare               # A.2-3 method comparison
.\.venv\Scripts\python.exe -m calibration.drift_experiment       # A.4 calibration under drift
.\.venv\Scripts\python.exe -m calibration.cv                     # B.6-7 k=5/k=10 + repeated CV
.\.venv\Scripts\python.exe -m calibration.significance           # B.8 paired tests vs baselines
.\.venv\Scripts\python.exe -m calibration.threshold_stability     # B.9 threshold stability
.\.venv\Scripts\python.exe -m calibration.report                  # assemble everything
.\.venv\Scripts\python.exe calibration/tests/test_calibration.py  # 11/11 tests
```

## Part A — Calibration: what was found and fixed

1. **Root cause, measured not assumed**: scores are heavily right-skewed
   (skew≈20) AND uniformly < 1 (range 2.5e-4–0.35). `log1p(x)≈x` in that
   range, so a naive "log-transform fix" is nearly a no-op (skew 19.94→18.91).
   A raw `log(score+eps)` transform is the correct fix for sub-1 data
   (skew→2.0) but introduces measured tail-overconfidence — full nuance in
   `diagnose.py` / the report.
2. **Historical failure did not reproduce** on the current model + leak-free
   split (old: a≈700, broken; here: a≈25, reasonable) — that failure was tied
   to the old leaky pipeline/model, not an inherent flaw in Platt scaling.
3. **Winner: Platt on the raw score** (ECE=0.024, robust-MCE=0.213 — best of
   4 candidates). Raw MCE alone is misleading here (only ~73 test attacks
   make several reliability bins near-empty); a bin-count-robust MCE
   (`min_count=10`) is used as the actual tie-break.
4. **The key result — calibration under drift**: FPR 3.6% (clean) → **100%**
   (drift ≥0.25σ, stale calibrator — this IS the Phase-3 saturation) →
   **5.2%** after recalibration. **98.3% of the FPR degradation is
   recovered by recalibration alone**, no model change.
5. **Recommendation**: adopt Platt-on-raw-score, but the real fix is
   operational — refit on a schedule (`recalibrate.py`, Phase 0), not once.

## Part B — Statistical validation

- **k=5 / k=10 grouped-by-meter CV** (no meter straddles folds — enforced by
  an assertion in `cv.py` and a dedicated unit test): F1 = 0.527±0.165 (k=5),
  0.325±0.280 (k=10). **Honest finding**: several folds have as few as 7-9
  attack sequences and can score F1=0 — real sampling variance any single
  train/test split (Phases 1-3 included) is subject to.
- **Repeated 5-fold, 3 seeds**: F1 = 0.430±0.274 — quantifies seed/split
  variance beyond a single CV run.
- **Paired significance vs label-free baselines** (same 5 folds): proposed
  model significantly beats Isolation Forest (Cohen's d=2.95, paired-t
  p=0.003); NOT significantly different from LSTM-Autoencoder (consistent
  with Phase 1); moderate effect vs One-Class SVM but underpowered at n=5
  folds (McNemar significant, paired-t/Wilcoxon not — stated as a limitation,
  not equivalence).
- **Threshold stability**: the *value* varies ~18% (CV%) across folds, but
  *locally* around the current production threshold, F1/FPR are insensitive
  to small perturbations (dF1/d1%≈0.0025) — two different, both-true findings.

## Outputs

`results/` — CSV/Excel/LaTeX tables, `cv_results.json`, `significance_results.json`,
`threshold_stability.json`, `recommendation.json`.
`plots/` — 8 figures (skew diagnosis, reliability diagrams ×2, comparison bars,
drift calibration + FPR recovery, CV summary dashboard, threshold sensitivity).
`reports/calibration_report.{md,pdf}` — full report with both composite scores.

**Calibration Quality Score: 91.5/100** · **Statistical Rigor Score: 100/100**
(rigor = completeness of the validation battery actually executed — high fold
variance is reported as an honest finding, not penalized as "low rigor").
