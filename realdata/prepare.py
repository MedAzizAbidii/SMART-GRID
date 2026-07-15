"""
realdata/prepare.py — build + cache the leak-free consumer-level SGCC dataset
used by the benchmark, ablation and calibration. Two representations, both
split identically by CONSUMER (no CONS_NO in >1 split):

  * SEQUENCE view  — per-consumer 30-day windows (feat) for reconstruction
    models. Unsupervised training uses TRAIN-split NON-THEFT windows only.
  * AGGREGATE view — one feature vector per consumer for tree/classical
    models, with the consumer FLAG.

Scaler is fit on TRAIN only (windows: on train non-theft window features;
aggregates: on train consumers). Cached to results/_cache/prepared.npz so
every downstream module reuses the exact same split.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler

from realdata.data import (
    load_sgcc_sorted, consumer_matrix, impute_series, build_daily_features,
    make_windows, aggregate_features, consumer_level_split, SEED,
)

CACHE = Path(__file__).resolve().parent / "results" / "_cache"
N_CONSUMERS = 8000        # stratified subsample (tractable seq-model training)
SEQ_LEN = 30
STRIDE = 30
TRAIN_WINDOW_CAP = 60000  # cap normal training windows for CPU tractability


def build(force=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "prepared.npz"
    if out.exists() and not force:
        return dict(np.load(out, allow_pickle=True))

    df, ordered, parsed = load_sgcc_sorted(sample_consumers=N_CONSUMERS, seed=SEED)
    X, flags, cons = consumer_matrix(df, ordered)

    # impute per consumer + collect missingness fraction
    filled = np.empty_like(X, dtype="float64")
    miss_frac = np.empty(len(X))
    for i in range(len(X)):
        filled[i], miss_frac[i] = impute_series(X[i])

    pop_mean_by_day = np.nanmean(np.where(np.isnan(X), np.nan, filled), axis=0)
    pop_mean_by_day = np.nan_to_num(pop_mean_by_day, nan=float(np.nanmean(filled)))

    feat_arr, feat_names = build_daily_features(filled.astype("float32"),
                                                parsed.to_numpy(), pop_mean_by_day.astype("float32"))
    agg_X, agg_names = aggregate_features(filled, miss_frac, flags)

    split = consumer_level_split(cons, flags, seed=SEED)   # per-consumer 'train/val/test'

    # windows (keep consumer idx to aggregate later)
    wins, widx, wlab = make_windows(feat_arr, flags, SEQ_LEN, STRIDE)
    win_split = np.array([split[c] for c in widx])

    # scaler for sequence features: fit on TRAIN non-theft windows only
    tr_norm_mask = (win_split == "train") & (wlab == 0)
    flat = wins[tr_norm_mask].reshape(-1, wins.shape[-1])
    seq_scaler = StandardScaler().fit(flat)
    wins_scaled = ((wins.reshape(-1, wins.shape[-1]) - seq_scaler.mean_) /
                   np.maximum(seq_scaler.scale_, 1e-8)).reshape(wins.shape).astype("float32")

    # cap training windows for tractability (random subsample of train-normal)
    rng = np.random.default_rng(SEED)
    tr_norm_idx = np.where(tr_norm_mask)[0]
    if len(tr_norm_idx) > TRAIN_WINDOW_CAP:
        tr_norm_idx = rng.choice(tr_norm_idx, TRAIN_WINDOW_CAP, replace=False)

    # scaler for aggregate features: fit on TRAIN consumers only
    agg_split = split
    tr_cons_mask = agg_split == "train"
    agg_scaler = StandardScaler().fit(agg_X[tr_cons_mask])
    agg_scaled = ((agg_X - agg_scaler.mean_) / np.maximum(agg_scaler.scale_, 1e-8)).astype("float32")

    data = {
        "wins_scaled": wins_scaled, "widx": widx, "wlab": wlab, "win_split": win_split,
        "train_norm_win_idx": tr_norm_idx,
        "agg_scaled": agg_scaled, "agg_names": np.array(agg_names),
        "feat_names": np.array(feat_names),
        "cons_flags": flags, "cons_split": split, "cons_no": cons,
        "seq_len": SEQ_LEN, "n_consumers": len(flags),
    }
    np.savez_compressed(out, **data)
    return dict(np.load(out, allow_pickle=True))


def consumer_split_masks(cons_split):
    return {s: (cons_split == s) for s in ("train", "val", "test")}


if __name__ == "__main__":
    d = build(force=True)
    print("prepared:",
          "windows", d["wins_scaled"].shape,
          "| consumers", int(d["n_consumers"]),
          "| agg", d["agg_scaled"].shape,
          "| train_norm_windows", len(d["train_norm_win_idx"]))
    for s in ("train", "val", "test"):
        m = d["cons_split"] == s
        print(f"  {s}: {m.sum()} consumers, theft={int(d['cons_flags'][m].sum())}")
