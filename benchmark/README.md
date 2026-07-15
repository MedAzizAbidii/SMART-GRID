# Unified Model Benchmark

A reproducible, **leak-free** benchmark that compares the proposed
Transformer-Autoencoder against strong classical and deep baselines under
**identical** experimental conditions.

## Run

```powershell
cd smartgrid_simulation
.\.venv\Scripts\python.exe -m benchmark.run_benchmark            # full run
.\.venv\Scripts\python.exe -m benchmark.run_benchmark --quick   # smoke (fewer epochs/boot)
.\.venv\Scripts\python.exe benchmark/tests/test_benchmark.py     # unit tests
```

Config: [`config.json`](config.json) — data path, split fractions, seed,
bootstrap iterations, model list, and deep-model hyperparameters.

## What it guarantees

- **One split for every model.** The train/validation/test split comes from
  `run_transformer_autoencoder.prepare_split_sequences` (reused, not
  duplicated): per-meter **temporal** split, scaler fit on **train only**,
  windows never cross a split or meter boundary.
- **Threshold on validation only.** Each model's decision threshold is chosen
  F1-optimally on the validation split; the **test split is untouched** until
  final metrics.
- **Automated leakage checks** run before training (`_validate_split`): splits
  non-empty, source rows disjoint across train/val/test, consistent feature
  dimension, scaler fitted.

## Models & the three paradigms

| Model | Family | Uses attack labels? |
|---|---|---|
| Isolation Forest | unsupervised anomaly | no |
| One-Class SVM (SGD) | unsupervised anomaly | no |
| LSTM Autoencoder | unsupervised reconstruction | no |
| **Transformer Autoencoder (proposed)** | unsupervised reconstruction | no |
| Random Forest | supervised | **yes** |
| XGBoost | supervised | **yes** |
| LightGBM | supervised | **yes** |

> **Read the ranking with this in mind.** Supervised models (RF/XGB/LGBM) train
> on attack labels the unsupervised detectors never see, so a raw F1 ranking
> mixes paradigms. The operationally relevant comparison for **unknown-attack**
> grid defence is *among the label-free methods*, where the proposed model leads.

## Outputs

- `results/comparison.{csv,md,tex,xlsx}` — comparison table, sorted by F1,
  best-per-metric highlighted.
- `results/results.json` — machine-readable metrics + CIs + timings.
- `plots/` — ROC & PR overlays, F1 with 95% bootstrap CI, confusion grid,
  score distributions, calibration, tree feature importance.
- `reports/benchmark_report.{md,pdf}` — full methodology → results → discussion.

## Metrics

Accuracy, Precision, Recall/Detection-rate, F1, ROC-AUC, PR-AUC, MCC, Balanced
Accuracy, Specificity, FPR, FNR, plus train time, inference latency, predict
time, peak memory, model size — each F1/AUC/PR-AUC/MCC with **95% bootstrap CI**,
and **paired McNemar** significance tests vs the proposed model.

## Implementation decisions (rationale)

1. **Reuse the production split, don't re-implement it** — the benchmark must
   test the *same* preprocessing the deployed model uses, and duplicating it
   would risk divergence.
2. **Flatten sequences (`seq_len×features`) for non-sequence models** — the
   fairest "identical input": every model sees the same information, reshaped.
3. **F1-optimal threshold on validation for all models** — one consistent,
   leak-free operating-point rule so the comparison is about the score, not the
   threshold.
4. **SGD One-Class SVM, not kernel SVC** — kernel SVC is O(n²) and intractable
   at ~20k sequences; the SGD variant is the scalable, standard choice.
5. **`scale_pos_weight` / `class_weight="balanced"`** on supervised models —
   attacks are ~3%, so imbalance handling is required for a fair baseline.
6. **Bootstrap CIs + McNemar** — the field expects uncertainty and paired
   significance, not point estimates; McNemar is correct because all models are
   evaluated on the identical test samples.
7. **PDF via matplotlib `PdfPages`** — avoids a heavyweight PDF dependency while
   still producing a portable report.

## Add a new model

Implement the `BaselineModel` interface in [`models.py`](models.py)
(`fit(train_seqs, train_labels)`, `score(seqs)->np.ndarray`), register it in
`REGISTRY`, and add its key to `config.json → models`. Nothing else changes.
