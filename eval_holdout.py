"""
eval_holdout.py — cross-distribution generalization test.

Loads a FROZEN trained model (weights + scaler + threshold, all fixed at
training time) and scores a dataset it never saw. Reports metrics on the
held-out set and, for comparison, on the training set — the GAP between them
is the real overfitting signal:

  small gap  -> the model generalizes (learned attack structure)
  large gap  -> the model memorized the training distribution

Usage:
  .\.venv\Scripts\python.exe eval_holdout.py \
      --model outputs/gentest_model \
      --train ../data/generalization_test/train_summer.csv \
      --test  ../data/generalization_test/test_winter.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ml_pipeline.preprocessing import load_dataset, build_feature_frame, make_sequences
from ml_pipeline.realtime_detector import TransformerAutoencoder


def _cm(y, p):
    tp = int(((p == 1) & (y == 1)).sum()); fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum()); tn = int(((p == 0) & (y == 0)).sum())
    return tn, fp, fn, tp


def prf(y, p):
    tn, fp, fn, tp = _cm(y, p)
    prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    acc = (tp + tn) / max(len(y), 1)
    return acc, prec, rec, f1, (tn, fp, fn, tp)


def roc_auc(y, s):
    pos = y == 1; n_pos = int(pos.sum()); n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float); ranks[order] = np.arange(1, len(s) + 1)
    vals, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    tie = np.zeros(len(counts)); np.add.at(tie, inv, ranks); ranks = (tie / counts)[inv]
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def load_frozen(model_dir: Path):
    art = json.loads((model_dir / "preprocessing_artifacts.json").read_text())
    rep = json.loads((model_dir / "training_report.json").read_text())
    ck = torch.load(model_dir / "transformer_autoencoder.pt", map_location="cpu", weights_only=False)
    model = TransformerAutoencoder(
        input_dim=ck["input_dim"], model_dim=ck["model_dim"],
        num_heads=ck["heads"], num_layers=ck["layers"],
    )
    model.load_state_dict(ck["model_state"]); model.eval()
    scaler = StandardScaler()
    scaler.mean_ = np.array(art["scaler_mean"]); scaler.scale_ = np.array(art["scaler_scale"])
    scaler.var_ = scaler.scale_ ** 2; scaler.n_features_in_ = len(scaler.mean_)
    return model, scaler, art["feature_columns"], int(art["sequence_length"]), float(rep["threshold"])


def score_csv(csv_path: Path, model, scaler, feature_columns, seq_len):
    """Return (scores, labels, anomalies_at_end) using the FROZEN scaler."""
    frame = load_dataset(Path(csv_path))
    feats, _ = build_feature_frame(frame)
    for c in feature_columns:
        if c not in feats.columns:
            feats[c] = 0.0
    feats = feats[feature_columns].astype(float)
    values = scaler.transform(feats.values).astype("float32")
    seqs, labels, end_idx = make_sequences(values, frame["is_alert"].values, seq_len, "last")
    scores = np.empty(len(seqs), "float32")
    with torch.no_grad():
        for i in range(0, len(seqs), 256):
            ch = torch.tensor(seqs[i:i+256], dtype=torch.float32)
            recon, _ = model(ch)
            scores[i:i+256] = ((recon - ch) ** 2).mean(dim=(1, 2)).numpy()
    anomalies = frame["anomalies"].fillna("").values[end_idx]
    return scores, labels, anomalies


def report(name, scores, labels, threshold, anomalies=None):
    pred = (scores >= threshold).astype(int)
    acc, prec, rec, f1, (tn, fp, fn, tp) = prf(labels, pred)
    auc = roc_auc(labels, scores)
    print(f"\n  === {name} ===")
    print(f"    AUC={auc:.4f}  Recall={rec:.4f}  Precision={prec:.4f}  F1={f1:.4f}  Acc={acc:.4f}")
    print(f"    confusion: TN={tn:,} FP={fp:,} FN={fn:,} TP={tp:,}   (attacks={int(labels.sum())})")
    if anomalies is not None:
        print(f"    per-attack-type recall:")
        atk_mask = labels == 1
        types = {}
        for a, l, p in zip(anomalies[atk_mask], labels[atk_mask], pred[atk_mask]):
            base = str(a).split(" | ")[0] if a else "?"
            types.setdefault(base, [0, 0]); types[base][0] += 1; types[base][1] += int(p)
        for t, (n, d) in sorted(types.items(), key=lambda x: -x[1][0]):
            print(f"      {t:<30} {d:>4}/{n:<4} = {100*d/max(n,1):5.1f}%")
    return {"auc": auc, "recall": rec, "precision": prec, "f1": f1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--train", required=True, type=Path)
    ap.add_argument("--test", required=True, type=Path)
    args = ap.parse_args()

    model, scaler, cols, seq_len, threshold = load_frozen(args.model)
    print("=" * 68)
    print("  CROSS-DISTRIBUTION GENERALIZATION TEST")
    print("=" * 68)
    print(f"  Model      : {args.model.name}  (frozen)")
    print(f"  Threshold  : {threshold:.6f}  (fixed at training time)")
    print(f"  Train data : {args.train.name}  (summer — model trained on this)")
    print(f"  Test data  : {args.test.name}  (winter, unseen seed — never trained on)")

    s_tr, y_tr, a_tr = score_csv(args.train, model, scaler, cols, seq_len)
    s_te, y_te, a_te = score_csv(args.test, model, scaler, cols, seq_len)

    m_in = report("IN-DISTRIBUTION  (train / summer)", s_tr, y_tr, threshold, a_tr)
    m_out = report("OUT-OF-DISTRIBUTION  (test / winter, unseen)", s_te, y_te, threshold, a_te)

    print("\n" + "=" * 68)
    print("  VERDICT")
    print("=" * 68)
    for k in ["auc", "recall", "precision", "f1"]:
        gap = m_in[k] - m_out[k]
        print(f"    {k.upper():<10} in={m_in[k]:.4f}  out={m_out[k]:.4f}  gap={gap:+.4f}")
    auc_gap = abs(m_in["auc"] - m_out["auc"])
    rec_gap = abs(m_in["recall"] - m_out["recall"])
    print()
    if auc_gap < 0.05 and rec_gap < 0.10:
        print("    => SMALL gap across a real distribution shift: the model GENERALIZES.")
        print("       It is not memorizing the training set.")
    else:
        print("    => LARGE gap: performance drops on unseen data — sign of overfitting/")
        print("       distribution-sensitivity. Reported honestly.")
    print("=" * 68)


if __name__ == "__main__":
    main()
