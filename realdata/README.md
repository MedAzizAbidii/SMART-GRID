# Phase 5b — Real-Data Validation on SGCC

Re-runs the Phase-1 benchmark, the attention ablation, and Phase-4 calibration
on the **real** SGCC electricity-theft dataset (42,372 consumers × 1,034 days,
8.5% theft), at the **consumer level**. Reuses `benchmark.metrics`,
`benchmark.models`, `ablation.model`, and `calibration.methods` — no
duplication of the prior frameworks or the model architecture.

## Run

```powershell
cd smartgrid_simulation
.\.venv\Scripts\python.exe -m realdata.reconcile     # STEP 0: dataset card + label decision (do first)
.\.venv\Scripts\python.exe -m realdata.prepare       # build + cache leak-free consumer split
.\.venv\Scripts\python.exe -m realdata.benchmark     # 7 models, consumer-level
.\.venv\Scripts\python.exe -m realdata.ablation      # attention re-test (the key result)
.\.venv\Scripts\python.exe -m realdata.calibrate     # Phase-4 Platt-on-raw on SGCC
.\.venv\Scripts\python.exe -m realdata.report        # assemble MD+PDF
.\.venv\Scripts\python.exe realdata/tests/test_realdata.py   # 8/8 tests
```

## Step 0 — the label-semantics decision (confronted, not glossed)

SGCC's FLAG is **consumer-level** ("ever stole"), not **event-level** ("this
day was fraud") like the synthetic labels. Decision: **evaluate at the consumer
level** — one prediction per consumer — the only level SGCC ground truth
exists at, and the published-literature framing. Unsupervised sequence models
train on non-theft consumers' windows and aggregate per-window reconstruction
errors into one consumer score; supervised models use one aggregate feature
vector per consumer. **No per-day labels are fabricated.** Full write-up in
`reports/step0_reconciliation.md`.

Also handled: date columns arrive **lexicographically** ordered (sorted
chronologically before windowing); **25.6% missingness** (imputed, with
missingness fraction retained as a feature); electrical features (voltage/
current/PF/frequency) are **not zero-filled** — SGCC models use an SGCC-native
feature set.

## Key measured results

| | ROC-AUC (consumer-level test) |
|---|---|
| **Random Forest (winner)** | **0.745** |
| LightGBM / XGBoost | 0.729 / 0.721 |
| Transformer-AE (proposed) | 0.655 |
| LSTM-AE | 0.654 |
| Isolation Forest / OCSVM | 0.596 / 0.407 |

**Ablation (the decisive re-test):** removing attention *improves* AUC
(full 0.655 → no-attention 0.667 → no-positional 0.715). **On real data with
genuine seasonality, attention still does not help** — the Phase-2.5 finding
survived contact with reality.

**Calibration:** Phase-4 Platt-on-raw transfers cleanly — ECE=0.0014,
Brier=0.0769 on SGCC test consumers.

## What survived synthetic → real

- ✅ Attention doesn't help (synthetic Phase 2.5 **and** real SGCC)
- ✅ Transformer ≈ LSTM (Phase 1 reproduced)
- ✅ Supervised tree/aggregate models win (XGBoost synthetic → Random Forest real)
- ❌ Absolute performance: ~0.99 synthetic → ~0.75 real — the synthetic set was
  far easier; its headline numbers did not transfer (exactly as flagged throughout)

## Limitations

Consumer-level (SGCC) vs per-event (synthetic) framings aren't directly
comparable — transfer is read at the level of *which family wins* and *whether
attention helps*, not raw F1. Stratified 8k-consumer subsample + fast fixed
budget for tractability. SGCC labels are audit-derived/imperfect; 25.6%
missingness imputed.
