"""
realdata/data.py — SGCC reconciliation + leak-free consumer-level preparation.

STEP 0 decisions (see reconcile.py for the written report; encoded here):

LABEL SEMANTICS — CONFRONTED, NOT GLOSSED.
  SGCC FLAG is CONSUMER-LEVEL: "this consumer was EVER caught stealing over
  2014-2016", NOT event-level ("this specific day was anomalous"). Our
  synthetic labels are per-reading EVENT labels. These are NOT equivalent.
  DECISION: evaluate at the CONSUMER (whole-series) level — one prediction per
  consumer — which is (a) the only level at which SGCC ground truth actually
  exists, and (b) the framing used by the published SGCC literature (Zheng
  et al. 2018 and successors report consumer-level AUC). We do NOT fabricate
  per-day labels. For unsupervised sequence models we train on non-theft
  consumers' windows and aggregate each consumer's window reconstruction
  errors into ONE consumer score; for supervised models we build ONE
  aggregate feature vector per consumer with the consumer FLAG.

FEATURE MAPPING — transferable only.
  SGCC has ONLY daily consumption (kWh) + real calendar dates. Transferable to
  our pipeline's feature philosophy: day-of-week, month/season (REAL yearly
  seasonality exists, 2+ years), rolling mean/std, consumption diff/rate, and
  consumer-vs-population-mean (the direct analogue of meter_vs_zone_consumption).
  NOT TRANSFERABLE (SGCC has none of these): tension_v, courant_a,
  power_factor, frequency_hz and every derived electrical-signature feature.
  These are NEVER zero-filled into the SGCC models — the SGCC models are built
  on an SGCC-native feature set, so no electrical feature silently biases them.

DATA QUALITY.
  Date columns arrive in LEXICOGRAPHIC order (2014/1/1, 2014/1/10, ...) — we
  sort chronologically before any windowing. Missingness is ~25.6% overall
  (measured) — imputed per consumer by linear time interpolation then edge
  fill, with a `was_missing` fraction retained as an aggregate feature so the
  models can use missingness itself (a known theft signal in this dataset).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SGCC_CSV = ROOT.parent / "data" / "external" / "sgcc" / "data.csv"
CACHE = Path(__file__).resolve().parent / "results" / "_cache"
SEED = 42


def load_sgcc_sorted(sample_consumers: int | None = None, seed: int = SEED):
    """Load SGCC, return (df, ordered_date_cols, parsed_dates).
    Date columns are returned in CHRONOLOGICAL order (the file's are not)."""
    df = pd.read_csv(SGCC_CSV)
    date_cols = [c for c in df.columns if c not in ("CONS_NO", "FLAG")]
    parsed = pd.to_datetime(pd.Series(date_cols), format="%Y/%m/%d", errors="coerce")
    order = np.argsort(parsed.values)
    ordered = [date_cols[i] for i in order]
    parsed_sorted = parsed.values[order]
    if sample_consumers is not None and sample_consumers < len(df):
        # stratified subsample preserving the theft rate (for tractable
        # sequence-model training; supervised models could use all rows)
        rng = np.random.default_rng(seed)
        theft = df.index[df["FLAG"] == 1].to_numpy()
        normal = df.index[df["FLAG"] == 0].to_numpy()
        rate = len(theft) / len(df)
        n_theft = min(len(theft), int(round(sample_consumers * rate)))
        n_normal = sample_consumers - n_theft
        pick = np.concatenate([rng.choice(theft, n_theft, replace=False),
                               rng.choice(normal, min(n_normal, len(normal)), replace=False)])
        df = df.loc[pick].reset_index(drop=True)
    return df, ordered, pd.Series(parsed_sorted)


def consumer_matrix(df, ordered_cols):
    """Return (X, flags, cons_no) where X is (n_consumers, n_days) chronological
    consumption, NaNs preserved."""
    X = df[ordered_cols].to_numpy(dtype="float64")
    return X, df["FLAG"].to_numpy(dtype=int), df["CONS_NO"].to_numpy()


def impute_series(row: np.ndarray) -> tuple[np.ndarray, float]:
    """Linear interpolation over time + edge fill. Returns (filled, missing_frac)."""
    miss = np.isnan(row)
    frac = float(miss.mean())
    if miss.all():
        return np.zeros_like(row), 1.0
    idx = np.arange(len(row))
    filled = row.copy()
    good = ~miss
    filled[miss] = np.interp(idx[miss], idx[good], row[good])
    return filled, frac


def build_daily_features(X_filled, parsed_dates, pop_mean_by_day):
    """Per (consumer, day) engineered features — ONLY transferable ones.
    Returns array (n_consumers, n_days, n_feat) and the feature-name list."""
    n, T = X_filled.shape
    dow = np.array([d.dayofweek for d in pd.to_datetime(parsed_dates)])   # 0-6
    month = np.array([d.month for d in pd.to_datetime(parsed_dates)])     # 1-12
    dow_sin = np.sin(2 * np.pi * dow / 7.0); dow_cos = np.cos(2 * np.pi * dow / 7.0)
    mon_sin = np.sin(2 * np.pi * (month - 1) / 12.0); mon_cos = np.cos(2 * np.pi * (month - 1) / 12.0)

    feats = {}
    feats["consumption"] = X_filled
    # rolling stats (7-day) along time
    df = pd.DataFrame(X_filled.T)  # (T, n)
    feats["roll_mean_7"] = df.rolling(7, min_periods=1).mean().to_numpy().T
    feats["roll_std_7"] = df.rolling(7, min_periods=1).std().fillna(0).to_numpy().T
    feats["diff"] = np.diff(X_filled, axis=1, prepend=X_filled[:, :1])
    feats["vs_population"] = X_filled - pop_mean_by_day.reshape(1, -1)   # analogue of meter_vs_zone
    # broadcast calendar features across consumers
    feats["dow_sin"] = np.broadcast_to(dow_sin, (n, T))
    feats["dow_cos"] = np.broadcast_to(dow_cos, (n, T))
    feats["mon_sin"] = np.broadcast_to(mon_sin, (n, T))
    feats["mon_cos"] = np.broadcast_to(mon_cos, (n, T))

    names = list(feats.keys())
    arr = np.stack([feats[k] for k in names], axis=-1).astype("float32")  # (n, T, f)
    return arr, names


def make_windows(feat_arr, flags, seq_len=30, stride=30):
    """Non-overlapping windows per consumer. Returns windows (W, seq_len, f),
    window_consumer_idx (W,), and per-window weak label (consumer FLAG)."""
    n, T, f = feat_arr.shape
    wins, widx, wlab = [], [], []
    for c in range(n):
        for start in range(0, T - seq_len + 1, stride):
            wins.append(feat_arr[c, start:start + seq_len])
            widx.append(c); wlab.append(flags[c])
    return (np.asarray(wins, dtype="float32"), np.asarray(widx), np.asarray(wlab, dtype=int))


def aggregate_features(X_filled, miss_frac, flags):
    """Consumer-level aggregate feature vector for tree/classical models.
    Transferable statistics only."""
    def z(a):
        return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    mean = X_filled.mean(axis=1); std = X_filled.std(axis=1)
    cv = z(std / (mean + 1e-9))
    mx = X_filled.max(axis=1); mn = X_filled.min(axis=1)
    zeros_frac = (X_filled <= 1e-6).mean(axis=1)
    # lag-1 autocorrelation per consumer
    Xc = X_filled - mean.reshape(-1, 1)
    denom = (Xc * Xc).sum(axis=1) + 1e-9
    acf1 = z((Xc[:, :-1] * Xc[:, 1:]).sum(axis=1) / denom)
    q10 = np.quantile(X_filled, 0.10, axis=1); q90 = np.quantile(X_filled, 0.90, axis=1)
    feats = np.column_stack([mean, std, cv, mx, mn, zeros_frac, acf1, q10, q90, miss_frac])
    names = ["mean", "std", "cv", "max", "min", "zeros_frac", "acf1", "q10", "q90", "missing_frac"]
    return feats.astype("float32"), names


def consumer_level_split(cons_no, flags, seed=SEED, val_frac=0.15, test_frac=0.15):
    """Split by CONSUMER — no CONS_NO in more than one split. Stratified by FLAG.
    Returns dict consumer_idx -> 'train'|'val'|'test'."""
    rng = np.random.default_rng(seed)
    assign = np.empty(len(cons_no), dtype=object)
    for label in (0, 1):
        idx = np.where(flags == label)[0]
        rng.shuffle(idx)
        n_test = int(len(idx) * test_frac); n_val = int(len(idx) * val_frac)
        assign[idx[:n_test]] = "test"
        assign[idx[n_test:n_test + n_val]] = "val"
        assign[idx[n_test + n_val:]] = "train"
    return assign
