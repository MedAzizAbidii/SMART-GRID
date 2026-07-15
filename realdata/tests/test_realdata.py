"""Unit tests for the SGCC real-data pipeline. Standalone or pytest."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from realdata.data import (impute_series, make_windows, aggregate_features,
                           consumer_level_split, build_daily_features)
from realdata.common import consumer_scores


# ── wide->long melt correctness ──────────────────────────────────────────────

def test_melt_preserves_all_readings_and_labels():
    wide = pd.DataFrame({
        "CONS_NO": ["A", "B"], "FLAG": [1, 0],
        "2014/1/1": [1.0, 2.0], "2014/1/2": [3.0, 4.0], "2014/1/3": [5.0, 6.0],
    })
    date_cols = ["2014/1/1", "2014/1/2", "2014/1/3"]
    long = wide.melt(id_vars=["CONS_NO", "FLAG"], value_vars=date_cols,
                     var_name="date", value_name="kwh")
    assert len(long) == 2 * 3
    assert set(long[long.CONS_NO == "A"]["FLAG"]) == {1}   # label inherited
    assert set(long[long.CONS_NO == "B"]["FLAG"]) == {0}
    assert sorted(long[long.CONS_NO == "A"]["kwh"]) == [1.0, 3.0, 5.0]


def test_date_sort_is_chronological_not_lexicographic():
    cols = ["2014/1/1", "2014/1/10", "2014/1/2"]
    parsed = pd.to_datetime(pd.Series(cols), format="%Y/%m/%d")
    order = np.argsort(parsed.values)
    chrono = [cols[i] for i in order]
    assert chrono == ["2014/1/1", "2014/1/2", "2014/1/10"]   # NOT lexicographic order


# ── imputation ────────────────────────────────────────────────────────────────

def test_impute_fills_nans_and_reports_fraction():
    row = np.array([1.0, np.nan, 3.0, np.nan, np.nan])
    filled, frac = impute_series(row)
    assert not np.isnan(filled).any()
    assert abs(frac - 3 / 5) < 1e-9
    assert abs(filled[1] - 2.0) < 1e-6   # linear interp between 1 and 3


def test_impute_all_missing_returns_zeros():
    row = np.full(5, np.nan)
    filled, frac = impute_series(row)
    assert (filled == 0).all() and frac == 1.0


# ── no consumer overlap across splits (the leak-free guarantee) ───────────────

def test_consumer_split_no_overlap():
    flags = np.array([0, 0, 0, 0, 1, 1, 0, 0, 1, 1] * 20)
    cons = np.array([f"C{i}" for i in range(len(flags))])
    assign = consumer_level_split(cons, flags, seed=1)
    # each consumer assigned exactly one split
    assert set(assign) <= {"train", "val", "test"}
    assert len(assign) == len(cons)
    # stratification: theft present in every split that is non-empty
    for s in ("train", "val", "test"):
        idx = assign == s
        assert idx.sum() > 0


def test_windows_carry_consumer_index_for_aggregation():
    feat = np.random.rand(3, 60, 4).astype("float32")   # 3 consumers, 60 days, 4 feat
    flags = np.array([0, 1, 0])
    wins, widx, wlab = make_windows(feat, flags, seq_len=30, stride=30)
    # 60 days / 30 = 2 windows per consumer
    assert len(wins) == 3 * 2
    assert set(widx) == {0, 1, 2}
    # each window's weak label == its consumer's flag
    for w, c in zip(wlab, widx):
        assert w == flags[c]


def test_consumer_scores_aggregate_correctly():
    # 2 consumers, consumer 0 has windows [1,3], consumer 1 has [10]
    win_scores = np.array([1.0, 3.0, 10.0])
    widx = np.array([0, 0, 1])
    cs = consumer_scores(win_scores, widx, n_consumers=2, agg="mean")
    assert abs(cs[0] - 2.0) < 1e-9 and abs(cs[1] - 10.0) < 1e-9


def test_aggregate_features_no_nan_inf():
    X = np.random.rand(20, 100).astype("float64")
    X[0] = 0.0   # a zero-consumption consumer (cv division edge case)
    feats, names = aggregate_features(X, np.random.rand(20), np.zeros(20, int))
    assert np.isfinite(feats).all()
    assert "missing_frac" in names


def _run_all():
    fns = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS  {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {fn.__name__}: {e}")
    print(f"\n  {ok}/{len(fns)} tests passed")
    return ok == len(fns)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
