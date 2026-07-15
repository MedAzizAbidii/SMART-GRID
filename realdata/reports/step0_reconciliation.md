# Phase 5b · STEP 0 — SGCC Reconciliation & Label-Semantics Decision

## Dataset card (measured)

- Source: SGCC electricity-theft dataset (Zheng et al. 2018 mirror).
- Shape: **42,372 consumers × 1,034 daily columns**.
- Label: **3,615 theft / 38,757 normal = 8.53% theft**.
- Date span: 2014-01-01 → 2016-10-31 (~34 months → REAL yearly seasonality).
- **Missingness: 25.64% of all cells** (per-consumer median 10.64%, 11,184 consumers >50% missing).

## Data-quality gotcha caught

- Date columns in the raw file are **lexicographically** ordered (`2014/1/1, 2014/1/10, 2014/1/11, ...`), NOT chronological (`date_cols_chronological_as_given = False`). A naive melt that trusts column order would **scramble every time series**. We parse the dates and sort chronologically before any windowing. Verified.

## Wide → long melt

- Verified on a 5-consumer sample: melt produced 5,170 rows (= 5 × 1,034), FLAG inherited per consumer, dates parsed & sorted. (`melt_wide_to_long_verified = True`.)

## LABEL SEMANTICS — the decision (confronted, not glossed)

**SGCC's FLAG is CONSUMER-LEVEL**: it marks a consumer who was *ever* caught stealing across the whole 2014-2016 span. It does NOT say which days were fraudulent. Our synthetic labels are the opposite: per-reading **EVENT** labels (this specific timestep is an injected attack).

**These are not equivalent, and we do not treat them as such.** Decision:

1. **Evaluation is CONSUMER-LEVEL** — one theft/normal prediction per consumer over their whole series. This is the only level at which SGCC ground truth exists, and it matches the published SGCC literature (consumer-level AUC).
2. **Unsupervised sequence models** (Transformer-AE, LSTM-AE, ablations) train on **non-theft consumers' windows only**, score every window by reconstruction error, then **aggregate each consumer's window errors into one consumer score** (mean and high-percentile) before thresholding.
3. **Supervised models** (RF/XGB/LightGBM) get **one aggregate feature vector per consumer** + the consumer FLAG.
4. We explicitly do **NOT** fabricate per-day labels or treat every day of a flagged consumer as a confirmed fraud event in the metrics.

## Feature mapping

**Transferable (used):**

- consumption (daily kWh)
- day-of-week (real calendar)
- month / yearly seasonality (2014-2016, REAL — unlike simulator)
- rolling mean/std (7-day)
- consumption diff / rate
- consumer-vs-population-mean (analogue of meter_vs_zone_consumption)
- missingness fraction (known theft signal in SGCC)

**NOT transferable (SGCC has no electrical signals — and these are NOT zero-filled into the SGCC models; the SGCC models use an SGCC-native feature set so no missing electrical feature can bias results):**

- tension_v (voltage)
- courant_a (current)
- power_factor
- frequency_hz
- voltage_deviation_230
- voltage_nominal_ratio
- current_voltage_ratio
- zone_consumption_mean / meter_vs_zone (no zones in SGCC)
- one-hot meter_id / zone / type (no such metadata in SGCC)

## Missingness handling

- Measured 25.64% missing — substantial, not assumed-clean. Imputation: **per-consumer linear time-interpolation** then edge-fill; a fully-empty series → zeros. The **missingness fraction is retained as an aggregate feature**, because sparse/zero reporting is itself a documented theft signal in SGCC — discarding it would throw away signal.

## Figures
![missingness](sgcc_missingness.png)
![profiles](sgcc_consumption_profiles.png)
