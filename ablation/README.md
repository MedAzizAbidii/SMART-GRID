# Ablation & Contribution Study

Scientifically demonstrates **which components of the proposed Transformer-
Autoencoder actually matter**, by removing/changing exactly one at a time and
measuring the effect on the held-out test split.

## Run

```powershell
cd smartgrid_simulation
.\.venv\Scripts\python.exe -m ablation.runner            # run all (resumable)
.\.venv\Scripts\python.exe -m ablation.runner --only E05_no_attention
.\.venv\Scripts\python.exe -m ablation.runner --fresh    # ignore cached results
.\.venv\Scripts\python.exe -m ablation.report            # tables + figures + report
.\.venv\Scripts\python.exe ablation/tests/test_ablation.py
```

## Design

- **Reuses Phase-1 infrastructure** — the same leak-free split
  (`prepare_split_sequences`), the same metric kernels (`benchmark.metrics`),
  the same reporting style. Nothing is duplicated.
- **One configurable model** (`model.py::AblationAE`) whose flags reproduce the
  full architecture and each ablated variant, so only one thing changes per run.
- **Fixed reduced training budget** (`experiments.py::BASE`) so **relative**
  ΔF1 effects are comparable and the whole 38-experiment study runs in ~20 min.
  Absolute F1 is lower than a fully-trained model *by design*.
- **Resumable** — each experiment writes `results/<id>.json`; re-running skips
  completed ones. Threshold and XAI experiments reuse the baseline's weights.
- **Leak-free** — the split, scaler-on-train, and threshold-on-val rules are
  inherited unchanged; feature selection is fit on train variance only.

## 20 experiments

Architecture (Transformer vs dense, bottleneck, positional, attention),
capacity (latent dim, embedding dim, heads, layers, sequence length), training
(loss MSE/MAE/Huber, optimizer, LR, dropout, batch, activation), decision
(threshold strategy: F1 / p95 / p99 / MAD / adaptive), preprocessing
(normalization, feature selection), and runtime (with/without XAI).

## Outputs

- `results/ablation_comparison.{csv,md,tex,xlsx}` — every experiment, sorted by F1.
- `results/<id>.json` — per-experiment metrics + 95% bootstrap CIs.
- `plots/` — contribution (ΔF1) bars, metric heatmap, hyperparameter
  sensitivity, radar, training-cost.
- `reports/ablation_report.{md,pdf}` — methodology, results, **contribution
  ranking**, and **auto-generated conclusions** (measured deltas only).

## Reading the result

`ΔF1 = baseline_F1 − variant_F1`. Positive ⇒ ablating that component **hurt**
(it helps, keep it). Negative ⇒ the change **helped** (revisit it). Conclusions
are generated purely from measured numbers — no invented explanations.

> **Honesty note.** At this fixed budget on this synthetic data, the biggest
> levers are the **threshold strategy**, **normalization**, and **sequence
> length** — not the attention mechanism (whose removal was roughly neutral).
> This is reported faithfully rather than massaged: a credible ablation states
> what the data shows, including where the headline component is not decisive.
