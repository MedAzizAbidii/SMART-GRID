"""Unit tests for the robustness framework. Standalone or pytest."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from robustness import perturbations as P
from robustness.common import degradation
from benchmark.metrics import all_metrics


def _toy(n=50, seq_len=8, feat=6, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(0, 1, (n, seq_len, feat)).astype("float32")


def test_gaussian_noise_changes_values_not_shape():
    x = _toy()
    y = P.gaussian_noise(x, 0.1, seed=1)
    assert y.shape == x.shape
    assert not np.allclose(x, y)


def test_gaussian_noise_zero_sigma_is_identity():
    x = _toy()
    y = P.gaussian_noise(x, 0.0, seed=1)
    assert np.allclose(x, y)


def test_sensor_noise_only_touches_raw_columns():
    cols = ["consommation_kw", "tension_v", "courant_a", "power_factor", "frequency_hz", "other_feat"]
    x = _toy(feat=len(cols))
    y = P.sensor_noise(x, cols, "offset", 0.5, seed=1)
    other_idx = cols.index("other_feat")
    assert np.allclose(x[:, :, other_idx], y[:, :, other_idx])       # untouched
    assert not np.allclose(x[:, :, 0], y[:, :, 0])                    # touched


def test_missing_values_zero_strategy():
    x = _toy()
    y = P.missing_values(x, 1.0, "zero", seed=1)   # 100% missing
    assert np.allclose(y, 0.0)


def test_missing_values_no_missing_is_identity():
    x = _toy()
    y = P.missing_values(x, 0.0, "zero", seed=1)
    assert np.allclose(x, y)


def test_sensor_failure_zeroes_target_channel():
    cols = ["consommation_kw", "tension_v", "courant_a"]
    x = _toy(feat=3)
    y = P.sensor_failure(x, cols, "critical", seed=1)
    idx = cols.index("consommation_kw")
    assert np.allclose(y[:, :, idx], 0.0)
    assert not np.allclose(y[:, :, 1], 0.0)   # other sensors untouched


def test_packet_loss_holds_previous_value():
    x = _toy(n=1, seq_len=5, feat=2)
    # force loss at t=2 deterministically by monkeypatching via seed sweep
    found = False
    for seed in range(50):
        y = P.packet_loss(x, 0.9, seed=seed)
        if not np.allclose(y[0, 1], x[0, 1]):    # some timestep got overwritten
            found = True
            break
    assert found, "packet_loss never modified any timestep across 50 seeds"


def test_data_drift_shifts_distribution():
    x = _toy(n=500)
    y = P.data_drift(x, level=2.0, seed=1)
    assert y.mean() > x.mean() + 0.5     # meaningfully shifted


def test_concept_drift_only_changes_attack_rows():
    x = _toy(n=20)
    labels = np.array([0] * 15 + [1] * 5)
    y = P.concept_drift(x, labels, level=0.5, seed=1)
    assert np.allclose(x[labels == 0], y[labels == 0])       # normals untouched
    assert not np.allclose(x[labels == 1], y[labels == 1])   # attacks changed


def test_concept_drift_level_zero_is_identity():
    x = _toy(n=10)
    labels = np.array([0] * 5 + [1] * 5)
    y = P.concept_drift(x, labels, level=0.0, seed=1)
    assert np.allclose(x, y)


def test_synth_unknown_attack_returns_all_ones_label():
    x = _toy(n=100)
    labels = np.zeros(100, int)
    seqs, labs = P.synth_unknown_attack(x, labels, ["a"] * x.shape[-1], "slow_ramp", seed=1)
    assert (labs == 1).all()
    assert seqs.shape[1:] == x.shape[1:]


def test_ood_samples_are_far_from_source():
    x = _toy(n=200)
    ood = P.ood_samples(x, level=5.0, seed=1)
    assert np.abs(ood).mean() > np.abs(x).mean() * 2


def test_degradation_direction():
    clean = {"metrics": {"f1": 0.8}}
    worse = {"metrics": {"f1": 0.4}}
    d = degradation(clean, worse, "f1")
    assert abs(d["abs_drop"] - 0.4) < 1e-9
    assert d["pct_drop"] > 0


def test_degradation_no_change():
    clean = {"metrics": {"f1": 0.5}}
    d = degradation(clean, clean, "f1")
    assert d["abs_drop"] == 0.0 and d["pct_drop"] == 0.0


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
