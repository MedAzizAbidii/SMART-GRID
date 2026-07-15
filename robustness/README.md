# Robustness, Generalization & Resilience Framework

Evaluates how the **frozen production model** (`outputs/early_stopping_final`,
untouched — no retraining) degrades under 12 environmental/adversarial
conditions, plus reliability and stress testing. All on the leak-free
held-out **TEST** split (reused from Phase 1/2, not duplicated).

## Run

```powershell
cd smartgrid_simulation
.\.venv\Scripts\python.exe -m robustness.runner                      # experiments 1-11 (resumable)
.\.venv\Scripts\python.exe -m robustness.runner --only E01_gauss_0.05
.\.venv\Scripts\python.exe -m robustness.adversarial_runner          # experiment 12 (FGSM/PGD)
.\.venv\Scripts\python.exe -m robustness.reliability --seconds 180   # short smoke test
.\.venv\Scripts\python.exe -m robustness.reliability --seconds 86400 # literal 24h soak (run overnight)
.\.venv\Scripts\python.exe -m robustness.stress --max 1000000        # chunked, no huge in-memory arrays
.\.venv\Scripts\python.exe -m robustness.report                      # tables + figures + report
.\.venv\Scripts\python.exe robustness/tests/test_robustness.py       # 14 unit tests
```

## Scope honesty (read before citing numbers)

- **Reliability**: a literal 24/48/72h run cannot execute inside an interactive
  session. The identical instrumented script (`reliability.py`) accepts
  `--seconds 86400/172800/259200`; what's reported by default is a **real,
  measured** short run (proves the code path, memory trend, latency stability)
  — not an extrapolated guess.
- **Stress**: 5M/10M-sequence scales are **engineering throughput/memory
  scaling tests** via chunked synthetic-load generation (never materializing
  the full N — 10M×8×85 float32 would be ~27GB). Scales that exceed the
  per-scale time budget are reported as measured-up-to-N plus a stated
  extrapolation from consistent throughput, never silently assumed.
- **Adversarial**: perturbations are applied in **scaled feature space**
  (white-box, gradient access to the frozen model). This is a worst-case
  upper bound on evasion susceptibility, not a proven raw-sensor-value attack
  — some engineered features (rolling stats, zone aggregates) aren't freely
  invertible to an equivalent raw perturbation. See `adversarial.py` docstring.

## The 12 experiments

| # | Experiment | What's measured |
|---|---|---|
| 1 | Gaussian noise (σ=0.01–0.20) | F1/AUC vs noise level |
| 2 | Sensor noise (offset/drift/quantization/spike) | degradation per fault type |
| 3 | Missing values (1–40%) × 4 imputations | best imputation strategy |
| 4 | Sensor failure (single/critical/multiple) | outage tolerance |
| 5 | Feature corruption | full 85-feature fragility ranking |
| 6 | Packet loss (1–20%) | hold-last-value degradation |
| 7 | Timestamp jitter | bounded reordering tolerance |
| 8 | Data drift | global shift tolerance (drift budget) |
| 9 | Concept drift | frozen-model adaptation as attacks are disguised |
| 10 | Unknown attacks | zero-day-proxy detection rate on 3 novel synthetic patterns |
| 11 | OOD samples | extreme-value flagging rate + score separation |
| 12 | Adversarial (FGSM/PGD) | evasion detect-rate vs L∞ budget |

## Key measured findings

- **No literal drift tolerance at the frozen threshold**: any global shift
  ≥0.25σ saturates FPR to 1.0 (flags everything) — the *same* failure mode
  proven earlier in the cross-season generalization test; recalibration
  (`recalibrate.py`, Phase-0 tooling) is the fix, not architecture change.
- **Concept-drift-disguised attacks became MORE detectable** (recall 0.575→1.0):
  blending an attack toward the population-average "normal" template produces
  a profile that itself looks anomalous to a per-type-aware model — consistent
  with the Phase 2.5 finding that mixed-type averages confuse this model family.
- **PGD (properly-tuned, multi-step) achieves real evasion** at small budgets
  (detect-rate 0.575→0.164 at ε=0.1); **FGSM (single large step) overshoots**
  the non-convex reconstruction-loss surface at higher ε and paradoxically
  *increases* detectability — a textbook, reportable adversarial-ML result.
- **No memory leak**: 60s / ~29k-call smoke test showed stable-to-negative
  memory growth; stress test showed flat ~11,000 seq/s throughput with no
  growing memory delta from 100K to 1M sequences.

## Outputs

- `results/*.json` — one cached file per experiment (resumable)
- `results/robustness_summary.{csv,xlsx,tex}`
- `plots/` — 7 figures (noise curve, missing-data curves, drift curves,
  feature sensitivity, adversarial curve, reliability trend, stress scaling)
- `reports/robustness_report.{md,pdf}` — full report with the Final
  Robustness Score breakdown (0–100 per dimension, each capped so an
  improved metric can't inflate the composite above "fully retained")
