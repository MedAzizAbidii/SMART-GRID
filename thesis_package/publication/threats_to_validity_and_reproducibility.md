# Threats to Validity & Reproducibility Statement

## Threats to validity

### Internal validity

- **Frozen-model reuse across phases** (§10.3): robustness, calibration,
  and part of the ablation analysis reuse a single frozen trained model
  rather than retraining per phase. Findings from these phases are valid
  statements about *that specific trained instance*, not a general claim
  about the architecture — a distinction the paper must preserve
  explicitly in any generalized phrasing.
- **Reduced-budget ablation** (dim=64, 5 pretraining epochs) trades
  absolute-value comparability against the full benchmark configuration
  (dim=128, 20 epochs) for tractability across 38 runs. Relative deltas
  (ΔF1) remain interpretable; absolute F1 values across the two studies
  are not directly comparable.
- **Sampling variance in cross-validation**: some folds contain as few as
  7-9 attack sequences, producing F1=0 in isolated folds purely from small
  sample size, not model failure — reported transparently rather than
  smoothed over by only reporting aggregate means.

### External validity

- **Single rule-based simulator** underlies all experiments except the
  SGCC real-data phase. The synthetic-to-real validation shows that
  *qualitative* conclusions (attention neutrality, Transformer≈LSTM,
  supervised trees winning) transfer, but *absolute* performance does not
  (≈0.99 synthetic → ≈0.75 real) — any claim of real-world performance
  must cite the SGCC numbers, not the synthetic-benchmark numbers.
  **Deployment corollary**: because the synthetic corpus is measurably
  easier than SGCC, thresholds, F1-based configuration choices, and any
  go/no-go decision derived from Chapters 11-13 should be re-validated on
  representative operational data before being trusted for production
  deployment — the synthetic numbers characterize the method, not a
  deployment-ready operating point.
- **Real-data validation uses a single external dataset** (SGCC, Chinese
  electricity-theft fraud, consumer-level labels only, no electrical
  signal features). Generalization to other grids, other fraud/attack
  types, or datasets with richer per-reading labels is untested.
- **Stratified 8,000-consumer subsample** (of 42,372) with a fixed
  training budget was used for tractability on the SGCC phase — a full-
  scale run was not performed.

### Construct validity

- **Consumer-level vs. reading-level ground truth mismatch** (SGCC): the
  available label is "ever committed fraud," not "this specific day was
  fraudulent." Evaluation is deliberately performed at the consumer level
  to match the only ground truth that actually exists, rather than
  fabricating a finer-grained label — a documented, explicit choice
  (Chapter 14.3), not a silent approximation.
- **Attention entropy as evidence of non-informativeness**: a high
  entropy value (0.961/1.0) is used as evidence that attention does not
  select specific timesteps. This is one operationalization of "attention
  usefulness" among several possible in the literature (see the general
  "attention is not explanation" debate, Chapter 3.3); the paper's claim
  is scoped to this specific operationalization plus the three converging
  pieces of evidence (temporal shuffling, last-timestep sufficiency,
  cross-dataset replication), not to attention interpretability in general.

### Statistical conclusion validity

- **McNemar tests assume paired binary outcomes** on the same test set —
  valid here since all models are evaluated on the identical held-out
  sequences, but the test does not itself establish effect size; bootstrap
  CIs and Cohen's d are reported alongside for this reason.
- **5-fold paired comparisons are underpowered** for detecting moderate
  effect sizes (e.g., vs. One-Class SVM: Cohen's d=0.925 but paired test
  not significant at n=5) — explicitly flagged rather than treated as
  "no difference."

## Reproducibility statement

- **Fixed random seed** (`seed=42`) for all data splits and model
  initialization across every experimental phase.
- **Deterministic split function** (`prepare_split_sequences()`) shared
  and imported (not reimplemented) across all phases — eliminates the risk
  of two phases silently using different split definitions.
- **Automated leakage checks**: `_validate_split()` verifies disjoint
  source rows between splits at every benchmark run, not only at
  development time.
- **Per-phase automated test suites** (9 to 46 tests depending on module,
  Chapter 10.6) run against every phase's core logic, including dedicated
  no-leakage and reproducibility tests in the calibration module.
- **Resumable experiment orchestration**: long-running experiment
  batches (the 38-run ablation study) checkpoint and resume after
  interruption — used in practice after a real crash at run 14/38.
- **All raw results retained**: every phase exports both a human-readable
  report (Markdown/PDF) and raw machine-readable results
  (`results.json`, `.csv`, `.xlsx`), enabling independent re-analysis
  without rerunning the experiments.
- **Known non-reproducibility gap, stated rather than hidden**: the
  currently deployed production model artifacts predate the leak-free
  protocol fix (no `"protocol"` field in their `training_report.json`) —
  reproducing the leak-free numbers requires retraining under the current
  (non-`--legacy`) pipeline, not loading the shipped artifacts as-is.
- **Docker topology not build-verified** (Chapter 15.5) — deployment
  reproducibility via the provided `docker-compose.yml` is unverified
  pending a build on a Docker-enabled machine.
