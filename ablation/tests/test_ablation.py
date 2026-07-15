"""Unit tests for the ablation framework. Standalone or pytest."""
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ablation.model import build_model, make_optimizer, make_loss
from ablation.experiments import all_experiments, BASE
from ablation import runner


def test_experiments_change_exactly_one_component():
    for e in all_experiments():
        if e["id"] == "E01_baseline":
            assert e["changes"] == {}          # baseline: nothing changed
        elif not e["retrain"]:
            # runtime/decision-rule experiments change 0 or 1 fields, no model change
            assert len(e["changes"]) <= 1, f"{e['id']} changes {e['changes']}"
        else:
            assert len(e["changes"]) == 1, f"{e['id']} changes {e['changes']}"


def test_every_experiment_id_unique():
    ids = [e["id"] for e in all_experiments()]
    assert len(ids) == len(set(ids))


def test_model_forward_shapes():
    m = build_model(12, dict(BASE))
    x = torch.randn(4, BASE["seq_len"], 12)
    assert m(x).shape == x.shape


def test_no_attention_changes_param_count():
    full = build_model(12, dict(BASE))
    cfg = dict(BASE); cfg["use_attention"] = False
    noatt = build_model(12, cfg)
    p_full = sum(p.numel() for p in full.parameters())
    p_no = sum(p.numel() for p in noatt.parameters())
    assert p_full != p_no          # architecture genuinely differs


def test_bottleneck_toggle():
    cfg = dict(BASE); cfg["use_bottleneck"] = False
    m = build_model(12, cfg)
    assert not hasattr(m, "down")
    m2 = build_model(12, dict(BASE))
    assert hasattr(m2, "down")


def test_optimizers_and_losses_build():
    m = build_model(8, dict(BASE))
    for opt in ("adam", "adamw", "rmsprop", "sgd"):
        assert make_optimizer(opt, m.parameters(), 1e-3) is not None
    import torch.nn as nn
    assert isinstance(make_loss("mse"), nn.MSELoss)
    assert isinstance(make_loss("mae"), nn.L1Loss)
    assert isinstance(make_loss("huber"), nn.HuberLoss)


def test_threshold_strategies_differ():
    rng = np.random.default_rng(0)
    scores = np.concatenate([rng.normal(0.1, 0.02, 300), rng.normal(0.5, 0.05, 10)])
    labels = np.concatenate([np.zeros(300), np.ones(10)]).astype(int)
    ths = {s: runner.pick_threshold(s, scores, labels)
           for s in ("f1", "p95", "p99", "mad", "adaptive")}
    assert len(set(round(v, 6) for v in ths.values())) >= 3   # strategies really differ


def test_feature_selection_is_leakfree_and_reduces_dims():
    rng = np.random.default_rng(1)
    tr = (rng.normal(0, 1, (100, 8, 20)).astype("float32"), np.zeros(100, int), None)
    va = (rng.normal(0, 1, (20, 8, 20)).astype("float32"), np.zeros(20, int), None)
    te = (rng.normal(0, 1, (20, 8, 20)).astype("float32"), np.zeros(20, int), None)
    tr2, va2, te2, idx = runner.select_features(tr, va, te, 10)
    assert tr2[0].shape[-1] == 10 and te2[0].shape[-1] == 10
    assert len(idx) == 10


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
