"""
Unit tests for benchmark utilities. Runs standalone (python test_benchmark.py)
or under pytest. Covers the metric kernels, threshold selection, bootstrap CI,
McNemar test, and the no-leakage split invariants.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmark import metrics as MET


def test_all_metrics_perfect():
    y = np.array([0, 0, 1, 1]); s = np.array([0.1, 0.2, 0.9, 0.8]); p = np.array([0, 0, 1, 1])
    m = MET.all_metrics(y, s, p)
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0
    assert m["roc_auc"] == 1.0 and m["mcc"] == 1.0
    assert m["fpr"] == 0.0 and m["fnr"] == 0.0


def test_all_metrics_worst():
    y = np.array([0, 0, 1, 1]); s = np.array([0.9, 0.8, 0.1, 0.2]); p = np.array([1, 1, 0, 0])
    m = MET.all_metrics(y, s, p)
    assert m["recall"] == 0.0 and m["fnr"] == 1.0 and m["fpr"] == 1.0


def test_confusion_counts():
    y = np.array([0, 1, 0, 1, 1]); p = np.array([0, 1, 1, 0, 1])
    tn, fp, fn, tp = MET.confusion(y, p)
    assert (tn, fp, fn, tp) == (1, 1, 1, 2)


def test_f1_threshold_separable():
    # cleanly separable -> threshold between the clusters, F1 = 1
    scores = np.concatenate([np.zeros(50), np.ones(50) * 5])
    labels = np.concatenate([np.zeros(50), np.ones(50)]).astype(int)
    t, f1 = MET.f1_optimal_threshold(scores, labels)
    assert f1 == 1.0 and 0 < t <= 5


def test_f1_threshold_no_attacks_falls_back():
    scores = np.random.rand(100); labels = np.zeros(100, int)
    t, f1 = MET.f1_optimal_threshold(scores, labels)
    assert f1 == 0.0 and t > scores.mean()   # conservative fallback


def test_bootstrap_ci_brackets_point():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400); s = rng.random(400); p = (s > 0.5).astype(int)
    point, lo, hi = MET.bootstrap_ci(y, s, p, "f1", n_boot=200, seed=1)
    assert lo <= point <= hi and 0 <= lo <= hi <= 1


def test_mcnemar_identical_predictions():
    y = np.array([0, 1, 0, 1]); a = np.array([0, 1, 0, 1])
    r = MET.mcnemar_test(y, a, a)
    assert r["b01"] == 0 and r["b10"] == 0 and r["p_value"] == 1.0


def test_mcnemar_detects_difference():
    y = np.ones(100, int)
    a = np.ones(100, int)          # A perfect
    b = np.zeros(100, int)         # B all wrong
    r = MET.mcnemar_test(y, a, b)
    assert r["b01"] == 100 and r["p_value"] < 0.05


def test_split_no_leakage_invariants():
    """The real leak-free split must produce disjoint source rows across splits."""
    from run_transformer_autoencoder import prepare_split_sequences
    csv = ROOT / "data" / "scenario_test" / "donnees_smart_meters.csv"
    if not csv.exists():
        print("  [skip] no scenario dataset present"); return
    (tr_s, tr_l, tr_e), (va_s, va_l, va_e), (te_s, te_l, te_e), cols, scaler, art, frame = \
        prepare_split_sequences(csv, 8, 0.15, 0.15)
    assert len(set(tr_e) & set(te_e)) == 0, "train/test source rows overlap!"
    assert len(set(va_e) & set(te_e)) == 0, "val/test source rows overlap!"
    assert tr_s.shape[1:] == te_s.shape[1:]
    assert hasattr(scaler, "mean_")


def _run_all():
    fns = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS  {fn.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {fn.__name__}: {e}")
    print(f"\n  {passed}/{len(fns)} tests passed")
    return passed == len(fns)


if __name__ == "__main__":
    ok = _run_all()
    sys.exit(0 if ok else 1)
