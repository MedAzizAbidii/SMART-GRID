# IEEE-style paper package

Target format: IEEE conference paper (double-column, 6-8 pages). This
package provides the outline, abstract, keywords, contribution summary,
and novelty statement — all grounded in the verified project results
(`thesis_package/research_notes/verified_facts.md`). No fabricated
citations are included; the student must add a proper related-work
bibliography (§II of the outline) from their own literature search.

---

## Title (suggested)

**"Rethinking Attention for Smart Grid Anomaly Detection: A Rigorous
Empirical Study of a Transformer Autoencoder with Blockchain-Notarized
Explainability"**

*(Alternative, more conservative title: "A Leak-Free Evaluation Protocol
for Transformer-Based Anomaly Detection in Smart Grids, with Blockchain
Notarization and Real-Data Validation")*

## Abstract (≈220 words)

Smart grid digitization introduces a new attack surface — false data
injection, denial of service, and energy-theft fraud — that demands
detection methods robust to previously unseen attack types. This paper
presents a Transformer-autoencoder-based anomaly detector evaluated under
a leak-free protocol (per-meter temporal train/validation/test split),
correcting a measured 0.91→0.64 F1 optimism gap caused by a naive
evaluation protocol. Under this protocol, the proposed model is compared
against six baselines spanning unsupervised-distance, unsupervised-
reconstruction, and supervised families. While supervised gradient-
boosted trees achieve higher F1 (0.986) by exploiting attack labels, the
proposed model significantly outperforms all label-free alternatives
(F1=0.582, McNemar p<10⁻⁹ against each). A 38-configuration ablation
study, followed by a dedicated diagnostic investigation (temporal
shuffling, attention entropy, single-timestep sufficiency), provides
convergent evidence that the Transformer's self-attention mechanism
contributes no measurable benefit on this data — a finding independently
reproduced on a real-world, 42,372-consumer public fraud dataset (SGCC).
Robustness testing identifies a critical failure mode (100% false-positive
saturation at 0.25σ distribution shift) and demonstrates that periodic
recalibration alone — with no model retraining — recovers 98.3% of the
resulting degradation. Confirmed detections are notarized on a
Proof-of-Authority ledger for tamper-evident audit. A systematic
performance-profiling phase further reveals and precisely localizes a
concurrency bottleneck (a blocking synchronous call inside an async
handler) that caps throughput at ~2.4 req/s regardless of load.

## Keywords

Smart grid security; anomaly detection; Transformer autoencoder;
explainable AI; attention mechanism analysis; blockchain notarization;
Proof-of-Authority; data leakage; model calibration; concept drift;
adversarial robustness; energy theft detection.

---

## Suggested section outline

**I. Introduction**
- Smart grid attack surface (FDIA, DoS, energy-theft fraud).
- Why unsupervised/label-free detection matters for unknown attacks.
- Contribution list (mirrors `thesis_package/defense/contributions.md`).

**II. Related Work** *(student to complete with a literature search;
see `thesis_package/thesis/chapitre_03_travaux_connexes.md` for the axes
to cover and the two verified external citations available: Zheng et al.
2018 Wide&Deep CNN on SGCC, AUC≈0.79; Nagi et al. SVM baseline, AUC≈0.72)*

**III. System Design**
- Realistic simulator (4 zones, 5 consumer types, 5 injected attack types
  at a realistic ~1.5% rate) — Chapter 6.
- Transformer autoencoder architecture (dim=128, heads=4, layers=3,
  seq_len=8) and EnsembleDetector (recall-optimized + precision-optimized
  pair) — Chapter 7.
- XAI layer: attention, integrated gradients (real-time), SHAP
  (offline) — Chapter 8.
- Proof-of-Authority ledger for tamper-evident notarization — Chapter 9.

**IV. Evaluation Methodology**
- Data-leakage diagnosis and fix: per-meter temporal split, scaler fit on
  train only (`prepare_split_sequences()`) — Chapter 5.
- Common protocol across all experimental phases: bootstrap CIs, paired
  McNemar test, grouped k-fold CV — Chapter 10.

**V. Experiments and Results**
- A. Benchmark against 6 baselines (Chapter 11) — Table with F1/AUC/CI.
- B. Ablation study, 38 configurations (Chapter 12.1-12.2) — contribution
  ranking table.
- C. Diagnostic investigation of the attention-neutrality finding
  (Chapter 12.3-12.4) — 4 pieces of converging evidence.
- D. Robustness and calibration (Chapter 13) — composite score, drift
  saturation, FGSM/PGD comparison, recalibration recovery result.
- E. Real-data validation on SGCC (Chapter 14) — cross-dataset transfer
  of findings.
- F. Production performance profiling (Chapter 16) — concurrency
  bottleneck root-cause.

**VI. Discussion** *(Chapter 17 condensed)*

**VII. Threats to Validity** *(see dedicated file, `threats_to_validity.md`)*

**VIII. Conclusion**

---

## Contribution summary (for §I)

1. Quantified diagnosis and correction of a data-leakage bias in
   time-series anomaly detection evaluation (measured 0.91→0.64 F1 gap).
2. A 38-configuration ablation study with a component-contribution
   ranking, isolating threshold strategy, normalization, and sequence
   length as the dominant levers — not model architecture.
3. A causal (not merely descriptive) investigation of why self-attention
   is neutral-to-counterproductive on this data, independently confirmed
   on a real-world dataset.
4. Quantified evidence that a robustness failure mode attributed to the
   model is in fact a calibration-staleness problem, recoverable (98.3%)
   without retraining.
5. Cross-dataset (synthetic → real) validation distinguishing findings
   that transfer from those that do not.
6. Precise, profiling-driven localization of a concurrency bottleneck
   (blocking call in an async handler) invisible to static code review.

## Novelty statement

This paper's novelty is **methodological rather than architectural**: no
individual component (Transformer autoencoder, Proof-of-Authority ledger,
Platt calibration, JWT/RBAC) is a novel invention. The contribution is
(a) the rigor of the leak-free evaluation protocol applied consistently
across every experimental phase, (b) the discipline of investigating
rather than discarding a result unfavorable to the initial hypothesis
(attention neutrality), and (c) the end-to-end validation chain from
synthetic data through real-world data to production performance
profiling — a chain rarely reported in full within a single study.
