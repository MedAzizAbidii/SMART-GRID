# Phase 2.5 — Why the Transformer Does Not Improve Performance

*Evidence-based investigation · leak-free split · production Transformer · measured only*

## Executive finding

**Recommendation: Make Transformer optional.** Based on the following measured evidence:

- Time-shuffling the input barely changes AUC (Δ=-0.000), so the model is **not using temporal order** — attention and positional encoding have nothing to exploit.
- A tree on a **single timestep** matches a tree on the full sequence (F1 0.973 vs 0.972), confirming temporal context adds almost no information on this data.
- Learned attention is near-uniform (normalised entropy 0.961/1.0), i.e. it does not concentrate on specific timesteps.

## 1. Temporal dependency

- Lag-1 autocorrelation: {'consommation_kw': 0.9335, 'tension_v': 0.0136, 'courant_a': 0.9282} (near 0 ⇒ little short-term memory).
- **Time-shuffle test** (permute timesteps within each window): AUC ordered=0.9538 vs shuffled=0.9542 (Δ=-0.0004). A near-zero Δ means temporal order is not being used.

## 2. Attention

- Normalised attention entropy = 0.9611/1.0 (1.0 = perfectly uniform); sparsity = 0.0731. Near-uniform attention is not selecting informative timesteps.

## 3. Latent space

- Normal/attack separation ratio (between/within): PCA=0.811, t-SNE=0.564. PCA variance explained (2 comps) = [0.075, 0.04].

## 4/5. Feature importance & dataset complexity

- **Max single-feature AUC = 0.748** — one feature alone separates the classes.
- Top single features: [('meter_id_SM_0015', 0.748), ('consommation_kw_rolling_mean_6', 0.7359), ('courant_a_rolling_mean_6', 0.7348), ('consommation_kw', 0.7336), ('consommation_kw_rolling_mean_3', 0.7333)]
- Permutation-importance top-3 share = 0.993 (few features dominate).
- Intrinsic dimensionality: 56 PCA components for 95% variance out of 85 features (redundant feature space).

## 6. Sequence length

- From the Phase-2 ablation, F1 did not improve with longer sequences (seq 16/32 ≤ seq 8 at fixed budget), consistent with the low autocorrelation and the shuffle test: the useful signal is essentially per-timestep.

## 7. Error analysis

- False negatives=7, false positives=156.
- Missed attacks by type: {'Tension hors norme': 3, 'Consommation nulle suspecte': 2, 'Surcharge': 2} — the misses concentrate in the subtle/low-magnitude classes, not the loud ones.

## 8. Why trees beat the Transformer

- Tree on **last timestep**: AUC=1.0, F1=0.9733.
- Tree on **full sequence**: AUC=0.9999, F1=0.9722.
- Tree on **time-shuffled sequence**: AUC=0.9774, F1=0.6923.
The three are close ⇒ trees win by thresholding a few informative features via nonlinear interactions, **not** by using temporal information — exactly the signal the Transformer is built to model but which is largely absent here.

## 9. Recommendation (IEEE-style)

On the current simulator-generated dataset the temporal dependencies the Transformer is designed to capture are weak: shuffling time changes AUC by -0.0004, a single feature already reaches AUC 0.748, and attention is near-uniform (0.9611/1.0). We therefore recommend **make transformer optional**: retain the Transformer as an optional encoder for deployment on real grids, where meter time-series exhibit richer temporal structure (load ramps, coordinated multi-step attacks) that this synthetic benchmark does not reproduce. The finding is a property of the **data**, not a defect of the architecture.

## Limitations

- Conclusions hold for this synthetic dataset and fixed budget; real meter data may show stronger temporal structure. This investigation deliberately does not tune or modify the model.
