"""
realdata/common.py — consumer-level scoring + evaluation shared by the SGCC
benchmark, ablation and calibration. Reuses benchmark.metrics (Phase 1); the
only new logic is aggregating per-WINDOW reconstruction errors up to a
per-CONSUMER score, which is the crux of the label-semantics decision.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.metrics import all_metrics, bootstrap_ci, f1_optimal_threshold
from ablation.model import build_model, make_optimizer, make_loss

SEED = 42
N_BOOT = 500


# ── reconstruction training / scoring on windows ─────────────────────────────

def train_recon(train_windows, cfg, seed=SEED):
    torch.manual_seed(seed)
    model = build_model(train_windows.shape[-1], cfg)
    opt = make_optimizer(cfg.get("optimizer", "adamw"), model.parameters(), cfg.get("lr", 5e-4))
    crit = make_loss(cfg.get("loss", "mse"))
    loader = DataLoader(TensorDataset(torch.tensor(train_windows, dtype=torch.float32)),
                        batch_size=cfg.get("batch_size", 256), shuffle=True)
    for _ in range(cfg.get("epochs", 6)):
        model.train()
        for (xb,) in loader:
            opt.zero_grad(); loss = crit(model(xb), xb); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
    return model


def window_scores(model, windows, batch=512):
    model.eval()
    out = np.empty(len(windows), "float32")
    with torch.no_grad():
        for i in range(0, len(windows), batch):
            xb = torch.tensor(windows[i:i+batch], dtype=torch.float32)
            rec = model(xb)
            out[i:i+batch] = ((rec - xb) ** 2).mean(dim=(1, 2)).numpy()
    return out


# ── window -> consumer aggregation (the label-semantics bridge) ───────────────

def consumer_scores(win_scores, widx, n_consumers, agg="mean"):
    """Aggregate per-window scores into ONE score per consumer.
    agg: 'mean' (typical behaviour) or 'p95' (worst-window / burst sensitivity)."""
    sums = np.zeros(n_consumers); counts = np.zeros(n_consumers)
    per = [[] for _ in range(n_consumers)] if agg == "p95" else None
    for s, c in zip(win_scores, widx):
        if agg == "mean":
            sums[c] += s; counts[c] += 1
        else:
            per[c].append(s)
    if agg == "mean":
        return np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    return np.array([np.percentile(p, 95) if p else np.nan for p in per])


# ── consumer-level evaluation ────────────────────────────────────────────────

def evaluate_consumer(scores, flags, split_masks, agg_higher_is_anomalous=True,
                      n_boot=N_BOOT, seed=SEED):
    """Choose threshold on VAL consumers, report metrics on TEST consumers.
    `scores`: per-consumer anomaly score (higher = more likely theft)."""
    if not agg_higher_is_anomalous:
        scores = -scores
    val_m, test_m = split_masks["val"], split_masks["test"]
    val_s, val_y = scores[val_m], flags[val_m]
    te_s, te_y = scores[test_m], flags[test_m]
    # drop any nan-scored consumers (e.g. fully-empty series) from both
    vgood = ~np.isnan(val_s); tgood = ~np.isnan(te_s)
    val_s, val_y = val_s[vgood], val_y[vgood]
    te_s, te_y = te_s[tgood], te_y[tgood]

    thr, _ = f1_optimal_threshold(val_s, val_y) if val_y.sum() > 0 else \
        (float(val_s.mean() + 3 * val_s.std()), 0.0)
    pred = (te_s >= thr).astype(int)
    m = all_metrics(te_y, te_s, pred)
    ci = {k: bootstrap_ci(te_y, te_s, pred, k, n_boot, seed) for k in ["f1", "roc_auc", "pr_auc", "mcc"]}
    return {"metrics": m, "ci": ci, "threshold": float(thr),
            "test_scores": te_s, "test_labels": te_y, "test_pred": pred}
