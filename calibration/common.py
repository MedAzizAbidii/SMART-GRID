"""
calibration/common.py — shared loading for the calibration & statistical
validation phase. Reuses the leak-free split and the frozen production model;
nothing here retrains or touches outputs/early_stopping_final.
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
from ml_pipeline.realtime_detector import _load_single
from benchmark.metrics import all_metrics, confusion

DATA = ROOT.parent / "data" / "scenario_test" / "donnees_smart_meters.csv"
MODEL_DIR = "outputs/early_stopping_final"
SEED = 42


def load_detector():
    det = _load_single(ROOT, MODEL_DIR)
    if det is None:
        raise SystemExit(f"Production model not found at {MODEL_DIR}")
    return det


def load_splits(seq_len: int = 8):
    """Full (train, val, test) tuples — val used to FIT calibrators, test used
    ONLY to evaluate them (mirrors the leak-free protocol: nothing about the
    test split is ever used for fitting anything)."""
    tr, va, te, cols, scaler, art, frame = prepare_split_sequences(DATA, seq_len, 0.15, 0.15)
    return tr, va, te, cols, scaler, frame


def recon_scores(model, seqs: np.ndarray, batch: int = 256) -> np.ndarray:
    model.eval()
    out = np.empty(len(seqs), "float32")
    with torch.no_grad():
        for i in range(0, len(seqs), batch):
            xb = torch.tensor(seqs[i:i+batch], dtype=torch.float32)
            rec, _ = model(xb)
            out[i:i+batch] = ((rec - xb) ** 2).mean(dim=(1, 2)).numpy()
    return out


def get_val_test_scores():
    """Convenience: frozen model's raw anomaly scores + labels on VAL and TEST."""
    det = load_detector()
    tr, va, te, cols, scaler, frame = load_splits()
    va_scores = recon_scores(det.model, va[0])
    te_scores = recon_scores(det.model, te[0])
    return {"va_scores": va_scores, "va_labels": va[1], "te_scores": te_scores,
            "te_labels": te[1], "model": det.model, "threshold": det.threshold_tracker._global,
            "cols": cols, "seq_len": 8}
