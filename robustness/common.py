"""
robustness/common.py — shared loading + scoring for every robustness experiment.

Uses the FROZEN production model (outputs/early_stopping_final) — never
retrained or fine-tuned here — and the leak-free TEST split only (reused from
run_transformer_autoencoder.prepare_split_sequences, not duplicated). Every
robustness experiment perturbs the test features, scores with the frozen
model + frozen scaler + frozen threshold, and compares against the clean
baseline computed once.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_transformer_autoencoder import prepare_split_sequences
from benchmark.metrics import all_metrics, bootstrap_ci
from ml_pipeline.realtime_detector import _load_single

DATA = ROOT.parent / "data" / "scenario_test" / "donnees_smart_meters.csv"
MODEL_DIR = "outputs/early_stopping_final"
SEED = 42
N_BOOT = 300


def load_detector():
    det = _load_single(ROOT, MODEL_DIR)
    if det is None:
        raise SystemExit(f"Production model not found at {MODEL_DIR}")
    return det


def load_test_split(seq_len: int = 8):
    """Return (test_seqs, test_labels, cols) — TEST split only, scaled with the
    split's own scaler (matches how the production model's scaler was fit:
    same preprocessing, same statistics, since both come from the same
    training data / pipeline)."""
    tr, va, te, cols, scaler, art, frame = prepare_split_sequences(DATA, seq_len, 0.15, 0.15)
    return te[0], te[1], cols, frame, te[2]


def recon_scores(model, seqs: np.ndarray, batch: int = 256) -> np.ndarray:
    model.eval()
    out = np.empty(len(seqs), "float32")
    with torch.no_grad():
        for i in range(0, len(seqs), batch):
            xb = torch.tensor(seqs[i:i+batch], dtype=torch.float32)
            rec, _ = model(xb)
            out[i:i+batch] = ((rec - xb) ** 2).mean(dim=(1, 2)).numpy()
    return out


def evaluate(model, seqs, labels, threshold, n_boot=N_BOOT, seed=SEED) -> dict:
    scores = recon_scores(model, seqs)
    pred = (scores >= threshold).astype(int)
    m = all_metrics(labels, scores, pred)
    ci = {k: bootstrap_ci(labels, scores, pred, k, n_boot, seed)
          for k in ["f1", "roc_auc", "pr_auc", "mcc"]}
    return {"metrics": m, "ci": ci, "scores": scores, "pred": pred}


def degradation(clean: dict, perturbed: dict, metric: str = "f1") -> dict:
    c, p = clean["metrics"][metric], perturbed["metrics"][metric]
    abs_drop = c - p
    rel_drop = (abs_drop / c * 100) if c > 1e-9 else 0.0
    return {"clean": round(c, 4), "perturbed": round(p, 4),
            "abs_drop": round(abs_drop, 4), "pct_drop": round(rel_drop, 2)}
