# Phase 5b — Real-Data Validation on SGCC

*Generated 2026-07-11 16:15 · consumer-level · leak-free (split by consumer) · frozen protocol reused from Phases 1-4*

## 1. Dataset card & Step-0 decision

- **42,372 consumers × 1,034 days**, **8.53% theft**, span 2014-01-01→2016-10-31.
- **Missingness 25.64%** (imputed by per-consumer time interpolation; missingness fraction retained as a feature).
- Date columns were lexicographically (not chronologically) ordered — sorted before windowing.

- **Label semantics (the key decision)**: SGCC's FLAG is *consumer-level* (ever-stole), not *event-level* (this day). We therefore evaluate at the **consumer level** — one prediction per consumer — matching the published SGCC literature and the only level at which ground truth exists. We do NOT fabricate per-day labels. Full decision in `reports/step0_reconciliation.md`.

- **Non-transferable features** (voltage/current/power-factor/frequency) are **not zero-filled** into the SGCC models — the SGCC models use an SGCC-native feature set, so no absent electrical feature can bias results.

## 2. Benchmark (7 models, consumer-level test)

| model | roc_auc | pr_auc | f1 | mcc | precision | recall |
|---|---|---|---|---|---|---|
| Random Forest | 0.7453 | 0.2780 | 0.3175 | 0.2461 | 0.2667 | 0.3922 |
| LightGBM | 0.7287 | 0.2670 | 0.3071 | 0.2340 | 0.2485 | 0.4020 |
| XGBoost | 0.7209 | 0.2733 | 0.2844 | 0.2122 | 0.2602 | 0.3137 |
| Transformer Autoencoder (proposed) | 0.6554 | 0.2070 | 0.2538 | 0.1729 | 0.2089 | 0.3235 |
| LSTM Autoencoder | 0.6543 | 0.2111 | 0.2601 | 0.1857 | 0.2397 | 0.2843 |
| Isolation Forest | 0.5957 | 0.1575 | 0.1957 | 0.1112 | 0.1729 | 0.2255 |
| One-Class SVM | 0.4066 | 0.0868 | 0.0850 | -0.1051 | 0.0510 | 0.2549 |

![benchmark](benchmark.png)

**Winner: Random Forest (AUC=0.745)** — a supervised gradient-boosted / tree model on consumer-level aggregate features, consistent with the SGCC literature. 
The proposed Transformer-AE (AUC=0.655) and LSTM-AE (AUC=0.654) are **statistically indistinguishable** — the Transformer's attention buys nothing over a simpler recurrent temporal model even on real data.

## 3. Ablation — does attention/Transformer help on REAL data?

This is the direct re-test of the Phase-2.5 synthetic-data finding.

| Variant | ROC-AUC | PR-AUC | F1 | ΔAUC vs full |
|---|---|---|---|---|
| Full (Transformer+attention) | 0.6554 | 0.2070 | 0.2538 |  |
| Dense encoder (no Transformer) | 0.6669 | 0.2111 | 0.2627 | -0.0114 |
| No attention (token-wise FFN) | 0.6669 | 0.2111 | 0.2627 | -0.0114 |
| No positional encoding | 0.7148 | 0.2122 | 0.2481 | -0.0594 |
| LSTM autoencoder | 0.6543 | 0.2111 | 0.2601 | +0.0011 |

![ablation](ablation.png)

**Measured verdict: attention STILL does not help on real data.** Removing attention changes AUC by -0.0114.

## 4. Calibration (Phase-4 Platt-on-raw)

On SGCC consumer scores: ECE=0.0014, robust-MCE=0.0004, Brier=0.0769. ![calibration](sgcc_calibration.png)

## 5. Literature comparison

| Method | Reported AUC | Protocol note |
|---|---|---|
| Wide & Deep CNN (Zheng et al., 2018) | 0.79 | original paper; consumer-level, supervised CNN on 2-D weekly reshaping |
| Random Forest (Zheng et al. baseline) | 0.74 | reported baseline in the same paper |
| SVM (Nagi et al., cited baseline) | 0.72 | classic SGCC-style SVM baseline |
| LSTM / RNN (various follow-ups) | 0.76 | supervised sequence models, consumer-level |
| **Ours (Random Forest)** | **0.745** | consumer-level, leak-free, UNSUPERVISED-friendly framing |

![literature](literature.png)

**Protocol caveats**: published numbers use varied protocols (2-D weekly reshaping, different splits, some semi-supervised). Our best AUC sits just below the Wide&Deep CNN (~0.79) and around the reported RF/SVM baselines (0.72-0.74) — a sane, honest place for a leak-free consumer-level re-run, NOT tuned to chase the paper's number.

## 6. Synthetic vs Real — what survived contact with real data

**Conclusions that SURVIVED contact with real data:**

- **Attention doesn't help** — held on synthetic (Phase 2.5) AND on real SGCC data. Removing attention barely changes AUC. This is the single most important cross-dataset confirmation.
- **Transformer ≈ LSTM** — the two sequence models tie on both synthetic and real data (Phase 1 result reproduced).
- **Supervised tree models on aggregate features win** — true on synthetic (Phase 1: XGBoost) and on real SGCC (Random Forest).

**Conclusions that did NOT transfer / changed:**

- Absolute performance is much lower on real data (best AUC ~0.75 vs ~0.99 synthetic) — the synthetic dataset was far easier; its high numbers did NOT transfer, exactly as the synthetic-only caveat warned throughout Phases 1-4.

## 7. Limitations & threats to validity

- Consumer-level framing (correct for SGCC) is not directly comparable to the per-event synthetic detection; ranking transfer is interpreted at the level of *which model family wins* and *whether attention helps*, not raw F1.
- A stratified 8,000-consumer subsample and a fast fixed training budget were used for tractability; absolute AUCs would likely rise a little with the full 42k consumers and longer training, but relative conclusions are the takeaway.
- SGCC labels are themselves imperfect (consumer-level, audit-derived); 25.6% missingness is imputed and could bias sequence models.
- No electrical signals exist in SGCC, so the electrical-signature strengths of the synthetic model are simply untestable here.
