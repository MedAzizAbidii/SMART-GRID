"""
run_transformer_autoencoder.py
==============================
Training driver for the Smart Grid Transformer Autoencoder anomaly detector.

This is the script `realtime_detector.py` expects to exist. It closes the loop:

    smart_meters_simulator.py  ->  CSV  ->  THIS SCRIPT  ->  deployable model

Pipeline:
  1. preprocessing.prepare_sequences()  — engineer features, scale, window
  2. Pre-train the autoencoder on ALL sequences (reconstruction)
  3. Fine-tune on NORMAL-only sequences  (so normal reconstructs well,
     attacks reconstruct badly = high anomaly score)
  4. Choose a threshold (F1-optimal + conservative mean+3sigma)
  5. Evaluate: AUC / precision / recall / F1 / confusion matrix
  6. Save drop-in artifacts consumed by realtime_detector.get_detector():
       transformer_autoencoder.pt        (checkpoint dict)
       preprocessing_artifacts.json      (scaler + feature columns)
       training_report.json              (threshold + metrics)
       anomaly_predictions.csv           (per-sequence scores/labels)
       pretraining_loss.csv / finetuning_loss.csv
       plots/  (loss curves, ROC, confusion matrix, score distribution)

Usage (from smartgrid_simulation/, using the ML venv):
    .\.venv\Scripts\python.exe run_transformer_autoencoder.py \
        --data ..\data\raw\donnees_smart_meters_20260701.csv \
        --output outputs\champion_v4

    # Train the v2 high-recall companion for the ensemble:
    .\.venv\Scripts\python.exe run_transformer_autoencoder.py \
        --data <csv> --output outputs\test_run_now --threshold-strategy f1 \
        --finetune-epochs 15

Arguments:
    --data PATH             Training CSV (from smart_meters_simulator.py)   [required]
    --output DIR            Output directory                    (default: outputs/champion_v4)
    --seq-len INT           Sequence window length              (default: 8)
    --model-dim INT         Transformer hidden dim              (default: 128)
    --heads INT             Attention heads                     (default: 4)
    --layers INT            Encoder layers                      (default: 3)
    --ff-dim INT            Feedforward dim                     (default: 256)
    --pretrain-epochs INT   Reconstruction pretraining epochs   (default: 40)
    --finetune-epochs INT   Normal-only finetune epochs         (default: 40)
    --batch-size INT        Batch size                          (default: 128)
    --lr FLOAT              Learning rate                       (default: 1e-3)
    --patience INT          Early-stopping patience             (default: 8)
    --threshold-strategy    'conservative' (mean+3sigma) | 'f1' (default: conservative)
    --val-frac FLOAT        Fraction of normal seqs for val     (default: 0.2)
    --device                cpu | cuda                          (default: cpu)
    --seed INT              RNG seed                            (default: 42)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_pipeline.preprocessing import (
    prepare_sequences, load_dataset, build_feature_frame, PreprocessArtifacts,
)
from sklearn.preprocessing import StandardScaler
# Reuse the EXACT architecture the detector loads — guarantees compatibility.
from ml_pipeline.realtime_detector import TransformerAutoencoder

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ─────────────────────────────────────────────────────────────────────────────
# Pure-numpy metrics (kept dependency-free so it also runs on the 32-bit venv)
# ─────────────────────────────────────────────────────────────────────────────

def _cm(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    return tn, fp, fn, tp


def prec_rec_f1(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    tn, fp, fn, tp = _cm(y_true, y_pred)
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    f = 2 * p * r / max(p + r, 1e-9)
    return p, r, f


def roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    # Rank-based AUC (Mann-Whitney U) — robust to ties, O(n log n)
    pos = y_true == 1
    neg = ~pos
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(y_score, kind="mergesort")
    ranks = np.empty(len(y_score), dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(y_score, return_inverse=True, return_counts=True)
    tie_sum = np.zeros(len(counts))
    np.add.at(tie_sum, inv, ranks)
    avg = tie_sum / counts
    ranks = avg[inv]
    auc = (ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


def f1_optimal_threshold(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Return (threshold, f1) maximising F1 over candidate thresholds."""
    cand = np.unique(np.quantile(scores, np.linspace(0.50, 0.999, 200)))
    best_t, best_f = float(cand[len(cand) // 2]), -1.0
    for t in cand:
        _, _, f = prec_rec_f1(labels, (scores >= t).astype(int))
        if f > best_f:
            best_f, best_t = f, float(t)
    return best_t, best_f


# ─────────────────────────────────────────────────────────────────────────────
# Training helpers
# ─────────────────────────────────────────────────────────────────────────────

def reconstruction_scores(model: nn.Module, seqs: np.ndarray,
                          device: torch.device, batch: int = 256) -> np.ndarray:
    """Per-sequence mean-squared reconstruction error (= anomaly score)."""
    model.eval()
    out = np.empty(len(seqs), dtype="float32")
    with torch.no_grad():
        for i in range(0, len(seqs), batch):
            chunk = torch.tensor(seqs[i:i + batch], dtype=torch.float32, device=device)
            recon, _ = model(chunk)
            err = ((recon - chunk) ** 2).mean(dim=(1, 2))
            out[i:i + batch] = err.cpu().numpy()
    return out


def train_phase(model, seqs, device, epochs, lr, batch, patience,
                val_seqs=None, label="train"):
    """Generic reconstruction training loop with early stopping."""
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", factor=0.5, patience=3)
    crit = nn.MSELoss()

    loader = DataLoader(
        TensorDataset(torch.tensor(seqs, dtype=torch.float32)),
        batch_size=batch, shuffle=True,
    )
    history: list[dict] = []
    best_loss, best_state, bad = float("inf"), None, 0

    for ep in range(1, epochs + 1):
        model.train()
        tot = 0.0
        for (xb,) in loader:
            xb = xb.to(device)
            opt.zero_grad()
            recon, _ = model(xb)
            loss = crit(recon, xb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += loss.item() * len(xb)
        train_loss = tot / len(seqs)

        if val_seqs is not None:
            val_loss = float(np.mean(reconstruction_scores(model, val_seqs, device)))
        else:
            val_loss = train_loss
        sched.step(val_loss)
        history.append({"epoch": ep, "train_loss": train_loss, "val_loss": val_loss})
        print(f"    [{label}] epoch {ep:>3}/{epochs}  train={train_loss:.6f}  val={val_loss:.6f}")

        if val_loss < best_loss - 1e-7:
            best_loss, bad = val_loss, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                print(f"    [{label}] early stop at epoch {ep}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return history


# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────

BG, FG, ACC, GOOD, BAD = "#0F172A", "#F8FAFC", "#38BDF8", "#4ADE80", "#F87171"


def _dark(ax, fig):
    fig.patch.set_facecolor(BG); ax.set_facecolor("#1E293B")
    ax.tick_params(colors=FG); ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG); ax.title.set_color(FG)
    for s in ax.spines.values():
        s.set_edgecolor("#334155")
    ax.grid(True, color="#334155", alpha=0.4, lw=0.5)


def save_plots(plots_dir: Path, pre_hist, ft_hist, scores, labels, threshold, auc):
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Loss curves
    fig, ax = plt.subplots(figsize=(9, 5)); _dark(ax, fig)
    if pre_hist:
        ax.plot([h["epoch"] for h in pre_hist], [h["val_loss"] for h in pre_hist],
                color=ACC, label="pretrain val")
    if ft_hist:
        off = pre_hist[-1]["epoch"] if pre_hist else 0
        ax.plot([h["epoch"] + off for h in ft_hist], [h["val_loss"] for h in ft_hist],
                color=GOOD, label="finetune val")
    ax.set_xlabel("epoch"); ax.set_ylabel("reconstruction loss")
    ax.set_title("Training loss"); ax.legend(labelcolor=FG)
    fig.savefig(plots_dir / "training_loss.png", dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    # Score distribution
    fig, ax = plt.subplots(figsize=(9, 5)); _dark(ax, fig)
    ax.hist(scores[labels == 0], bins=60, color=GOOD, alpha=0.6, label="normal", log=True)
    ax.hist(scores[labels == 1], bins=60, color=BAD, alpha=0.6, label="attack", log=True)
    ax.axvline(threshold, color=ACC, ls="--", lw=2, label=f"threshold={threshold:.6f}")
    ax.set_xlabel("anomaly score (MSE)"); ax.set_ylabel("count (log)")
    ax.set_title("Score distribution"); ax.legend(labelcolor=FG)
    fig.savefig(plots_dir / "anomaly_score_distribution.png", dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    # ROC
    fig, ax = plt.subplots(figsize=(6, 6)); _dark(ax, fig)
    ts = np.linspace(scores.min(), scores.max(), 200)
    tpr, fpr = [], []
    P, N = max((labels == 1).sum(), 1), max((labels == 0).sum(), 1)
    for t in ts:
        pred = (scores >= t).astype(int)
        _, fp, fn, tp = _cm(labels, pred)
        tpr.append(tp / P); fpr.append(fp / N)
    ax.plot(fpr, tpr, color=ACC, lw=2, label=f"AUC={auc:.4f}")
    ax.plot([0, 1], [0, 1], color=FG, ls="--", alpha=0.4)
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC"); ax.legend(labelcolor=FG)
    fig.savefig(plots_dir / "roc_curve.png", dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    # Confusion matrix
    pred = (scores >= threshold).astype(int)
    tn, fp, fn, tp = _cm(labels, pred)
    fig, ax = plt.subplots(figsize=(5.5, 5)); _dark(ax, fig)
    mat = np.array([[tn, fp], [fn, tp]])
    ax.imshow(mat, cmap="Blues")
    for (i, j), v in np.ndenumerate(mat):
        ax.text(j, i, f"{v:,}", ha="center", va="center",
                color="white" if v > mat.max() / 2 else "black", fontsize=13, fontweight="bold")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["pred normal", "pred attack"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["true normal", "true attack"])
    ax.set_title("Confusion matrix")
    fig.savefig(plots_dir / "confusion_matrix.png", dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Leak-free train / validation / test preparation
# ─────────────────────────────────────────────────────────────────────────────

def prepare_split_sequences(csv_path, seq_len, val_frac=0.15, test_frac=0.15,
                            label_strategy="last", scale=True):
    """Build train/val/test sequences with NO information leakage.

    Fixes two methodological leaks in prepare_sequences():
      1. The StandardScaler is fit on the TRAIN split only, then applied to
         val/test (previously fit on the whole dataset -> stats leak).
      2. Data is split per-meter TEMPORALLY (first rows -> train, then val,
         then test) so the test set is strictly in the future of training and
         no sliding window ever straddles a split boundary or a meter boundary.

    Feature engineering (rolling/diff) is label-free, so computing it over each
    meter's full series before splitting introduces no label leakage; only the
    scaler statistics could leak, which is why the scaler is fit on train rows
    alone.

    Returns: (train, val, test) each a (sequences, labels, end_index) tuple,
             feature_columns, fitted StandardScaler, PreprocessArtifacts, frame.
    """
    frame = load_dataset(Path(csv_path))            # sorted by meter_id, timestamp
    frame = frame.reset_index(drop=True)
    features, cols = build_feature_frame(frame)
    features = features.reset_index(drop=True)

    meters = frame["meter_id"].astype(str).values if "meter_id" in frame.columns \
        else np.zeros(len(frame), dtype=str)
    labels_all = frame["is_alert"].values.astype(int)

    # Per-meter temporal split tag
    split_tag = np.empty(len(frame), dtype=object)
    for mid in np.unique(meters):
        idx = np.where(meters == mid)[0]            # already time-ordered
        n = len(idx)
        n_test = int(n * test_frac)
        n_val = int(n * val_frac)
        n_train = n - n_val - n_test
        split_tag[idx[:n_train]] = "train"
        split_tag[idx[n_train:n_train + n_val]] = "val"
        split_tag[idx[n_train + n_val:]] = "test"

    # Fit the scaler on TRAIN rows only, then transform everything.
    # scale=False (used only by the normalization ablation) keeps raw features
    # and records identity scaler stats; default True is unchanged behaviour.
    train_mask = split_tag == "train"
    if scale:
        scaler = StandardScaler().fit(features.values[train_mask])
        values = scaler.transform(features.values).astype("float32")
    else:
        scaler = StandardScaler()
        scaler.mean_ = np.zeros(features.shape[1])
        scaler.scale_ = np.ones(features.shape[1])
        scaler.var_ = np.ones(features.shape[1])
        scaler.n_features_in_ = features.shape[1]
        values = features.values.astype("float32")

    def window(tag):
        seqs, labs, ends = [], [], []
        for mid in np.unique(meters):
            m = (meters == mid) & (split_tag == tag)
            rows = np.where(m)[0]
            if len(rows) < seq_len:
                continue
            v = values[rows]
            lab = labels_all[rows]
            for end in range(seq_len, len(v) + 1):
                seqs.append(v[end - seq_len:end])
                labs.append(int(lab[end - 1]) if label_strategy == "last"
                            else int(lab[end - seq_len:end].max()))
                ends.append(int(rows[end - 1]))
        if not seqs:
            empty = np.empty((0, seq_len, values.shape[1]), "float32")
            return empty, np.array([], int), np.array([], int)
        return np.stack(seqs), np.asarray(labs), np.asarray(ends)

    tr, va, te = window("train"), window("val"), window("test")

    artifacts = PreprocessArtifacts(
        numeric_columns=[c for c in cols if c in frame.columns],
        categorical_columns=[c for c in frame.select_dtypes(exclude=[np.number]).columns
                             if c not in {"statut", "stabf"}],
        feature_columns=cols,
        sequence_length=seq_len,
        scaler_mean=scaler.mean_.tolist(),
        scaler_scale=scaler.scale_.tolist(),
    )
    return tr, va, te, cols, scaler, artifacts, frame


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Train the Smart Grid Transformer Autoencoder")
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--output", type=Path, default=ROOT / "outputs" / "champion_v4")
    ap.add_argument("--seq-len", type=int, default=8)
    ap.add_argument("--model-dim", type=int, default=128)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--ff-dim", type=int, default=256)
    ap.add_argument("--pretrain-epochs", type=int, default=40)
    ap.add_argument("--finetune-epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--threshold-strategy", choices=["conservative", "f1"], default="conservative")
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--legacy", action="store_true",
                    help="Use the old leaky no-held-out flow (NOT recommended; "
                         "kept only for reproducing pre-2026-07 results).")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    return _main_legacy(args) if args.legacy else _main_split(args)


def _main_legacy(args):
    """Original no-held-out flow (scaler + threshold + metrics on all data).
    Leaky; retained only to reproduce pre-2026-07 champion numbers."""
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  Transformer Autoencoder — Training Driver [LEGACY / leaky]")
    print("=" * 64)
    print(f"  Data   : {args.data}")
    print(f"  Output : {out}")
    print(f"  Device : {device}")
    print()

    # ── 1. Preprocess ────────────────────────────────────────────────────────
    print("  [1/5] Preprocessing + windowing ...")
    t0 = time.perf_counter()
    seqs, labels, end_idx, frame, artifacts = prepare_sequences(
        args.data, sequence_length=args.seq_len, label_strategy="last"
    )
    n_feat = seqs.shape[-1]
    n_norm = int((labels == 0).sum())
    n_alert = int((labels == 1).sum())
    print(f"        sequences={len(seqs):,}  features={n_feat}  "
          f"normal={n_norm:,}  attack={n_alert:,}  ({time.perf_counter()-t0:.1f}s)")
    if n_alert == 0:
        print("  [WARN] No attack labels found — threshold falls back to conservative.")

    # Save preprocessing artifacts immediately (needed by detector)
    artifacts.save(out / "preprocessing_artifacts.json")

    # ── 2. Split normal sequences temporally (train / val) ───────────────────
    normal_seqs = seqs[labels == 0]
    cut = int(len(normal_seqs) * (1 - args.val_frac))
    train_norm, val_norm = normal_seqs[:cut], normal_seqs[cut:]

    # ── 3. Build model ───────────────────────────────────────────────────────
    model = TransformerAutoencoder(
        input_dim=n_feat, model_dim=args.model_dim, num_heads=args.heads,
        num_layers=args.layers, feedforward_dim=args.ff_dim,
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  [2/5] Model: dim={args.model_dim} heads={args.heads} "
          f"layers={args.layers}  params={n_params:,}")

    # ── 4a. Pretrain on ALL sequences (learn grid dynamics) ──────────────────
    print("  [3/5] Pretraining (all sequences) ...")
    pre_hist = train_phase(model, seqs, device, args.pretrain_epochs, args.lr,
                           args.batch_size, args.patience, val_seqs=val_norm, label="pretrain")

    # ── 4b. Fine-tune on NORMAL only (sharpen normal manifold) ───────────────
    print("  [4/5] Fine-tuning (normal only) ...")
    ft_hist = train_phase(model, train_norm, device, args.finetune_epochs, args.lr * 0.5,
                          args.batch_size, args.patience, val_seqs=val_norm, label="finetune")

    # ── 5. Score + threshold + evaluate ──────────────────────────────────────
    print("  [5/5] Scoring + threshold selection ...")
    scores = reconstruction_scores(model, seqs, device)
    normal_scores = scores[labels == 0]
    thr_conservative = float(normal_scores.mean() + 3.0 * normal_scores.std())
    thr_percentile = float(np.quantile(normal_scores, 0.995))

    if n_alert > 0:
        thr_f1, f1_at_opt = f1_optimal_threshold(scores, labels)
        auc = roc_auc(labels, scores)
    else:
        thr_f1, f1_at_opt, auc = thr_conservative, 0.0, 0.5

    threshold = thr_f1 if args.threshold_strategy == "f1" else thr_conservative
    pred = (scores >= threshold).astype(int)
    prec, rec, f1 = prec_rec_f1(labels, pred)
    tn, fp, fn, tp = _cm(labels, pred)

    print()
    print(f"        AUC={auc:.4f}  P={prec:.4f}  R={rec:.4f}  F1={f1:.4f}")
    print(f"        threshold({args.threshold_strategy})={threshold:.6f}")
    print(f"        confusion: TN={tn:,} FP={fp:,} FN={fn:,} TP={tp:,}")

    # ── Save checkpoint (drop-in for realtime_detector._load_model) ──────────
    checkpoint = {
        "model_state": model.state_dict(),
        "input_dim": n_feat,
        "model_dim": args.model_dim,
        "heads": args.heads,
        "layers": args.layers,
        "sequence_length": args.seq_len,
    }
    torch.save(checkpoint, out / "transformer_autoencoder.pt")

    # ── training_report.json (detector reads 'threshold') ────────────────────
    report = {
        "architecture": f"TransformerAutoencoder dim={args.model_dim} heads={args.heads} layers={args.layers}",
        "data_file": str(args.data),
        "rows": int(len(frame)),
        "sequences": int(len(seqs)),
        "normal_sequences": n_norm,
        "alert_sequences": n_alert,
        "label_strategy": "last",
        "pretrain_epochs_run": len(pre_hist),
        "finetune_epochs_run": len(ft_hist),
        "threshold": threshold,
        "threshold_strategy": args.threshold_strategy,
        "threshold_f1_optimal": thr_f1,
        "threshold_f1_optimal_score": f1_at_opt,
        "threshold_conservative_mean_3std": thr_conservative,
        "threshold_conservative_percentile": thr_percentile,
        "metrics": {
            "auc": auc, "precision": prec, "recall": rec, "f1": f1,
            "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        },
        "training_history": {"pretrain": pre_hist, "finetune": ft_hist},
    }
    (out / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # ── per-sequence predictions CSV ─────────────────────────────────────────
    with (out / "anomaly_predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["end_index", "anomaly_score", "sequence_label", "predicted"])
        for e, s, l, p in zip(end_idx, scores, labels, pred):
            w.writerow([int(e), f"{s:.8f}", int(l), int(p)])

    # ── loss CSVs ────────────────────────────────────────────────────────────
    for name, hist in (("pretraining_loss.csv", pre_hist), ("finetuning_loss.csv", ft_hist)):
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["epoch", "train_loss", "val_loss"])
            for h in hist:
                w.writerow([h["epoch"], f"{h['train_loss']:.8f}", f"{h['val_loss']:.8f}"])

    # ── plots ────────────────────────────────────────────────────────────────
    save_plots(out / "plots", pre_hist, ft_hist, scores, labels, threshold, auc)

    print()
    print("=" * 64)
    print("  DONE — deployable artifacts written to:")
    print(f"    {out / 'transformer_autoencoder.pt'}")
    print(f"    {out / 'preprocessing_artifacts.json'}")
    print(f"    {out / 'training_report.json'}")
    print(f"    {out / 'plots'}/  (4 charts)")
    print()
    print("  Deploy: realtime_detector.get_detector() auto-loads")
    print("  outputs/early_stopping_final (v3) + outputs/test_run_now (v2).")
    print("  Point --output at one of those to slot into the ensemble.")
    print("=" * 64)


def _main_split(args):
    """Leak-free flow: scaler fit on TRAIN, threshold tuned on VAL, final
    metrics reported on an untouched TEST split."""
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  Transformer Autoencoder — Training Driver [leak-free]")
    print("=" * 64)
    print(f"  Data   : {args.data}")
    print(f"  Output : {out}")
    print(f"  Split  : train / val {args.val_frac:.0%} / test {args.test_frac:.0%}  (per-meter, temporal)")
    print()

    # ── 1. Leak-free split + scaling ─────────────────────────────────────────
    print("  [1/6] Preprocessing + per-meter temporal split (scaler on train only) ...")
    t0 = time.perf_counter()
    (tr_seqs, tr_lab, _), (va_seqs, va_lab, _), (te_seqs, te_lab, te_end), \
        cols, scaler, artifacts, frame = prepare_split_sequences(
            args.data, args.seq_len, args.val_frac, args.test_frac)
    n_feat = tr_seqs.shape[-1]
    print(f"        train={len(tr_seqs):,} (atk {int(tr_lab.sum())})  "
          f"val={len(va_seqs):,} (atk {int(va_lab.sum())})  "
          f"test={len(te_seqs):,} (atk {int(te_lab.sum())})  "
          f"features={n_feat}  ({time.perf_counter()-t0:.1f}s)")
    artifacts.save(out / "preprocessing_artifacts.json")

    tr_norm = tr_seqs[tr_lab == 0]
    va_norm = va_seqs[va_lab == 0]
    cut = int(len(tr_norm) * (1 - 0.15))
    ft_train, ft_val = tr_norm[:cut], (va_norm if len(va_norm) else tr_norm[cut:])

    # ── 2. Model ─────────────────────────────────────────────────────────────
    model = TransformerAutoencoder(
        input_dim=n_feat, model_dim=args.model_dim, num_heads=args.heads,
        num_layers=args.layers, feedforward_dim=args.ff_dim).to(device)
    print(f"  [2/6] Model dim={args.model_dim} heads={args.heads} layers={args.layers}  "
          f"params={sum(p.numel() for p in model.parameters()):,}")

    # ── 3. Pretrain on TRAIN sequences only (test never seen) ────────────────
    print("  [3/6] Pretraining (train split only) ...")
    pre_hist = train_phase(model, tr_seqs, device, args.pretrain_epochs, args.lr,
                           args.batch_size, args.patience, val_seqs=ft_val, label="pretrain")
    # ── 4. Fine-tune on TRAIN-normal ─────────────────────────────────────────
    print("  [4/6] Fine-tuning (train-normal) ...")
    ft_hist = train_phase(model, ft_train, device, args.finetune_epochs, args.lr * 0.5,
                          args.batch_size, args.patience, val_seqs=ft_val, label="finetune")

    # ── 5. Threshold selection on VALIDATION only ────────────────────────────
    print("  [5/6] Threshold selection on VALIDATION (test stays untouched) ...")
    va_scores = reconstruction_scores(model, va_seqs, device)
    va_norm_scores = va_scores[va_lab == 0] if len(va_norm) else va_scores
    thr_conservative = float(va_norm_scores.mean() + 3.0 * va_norm_scores.std())
    if int(va_lab.sum()) > 0:
        thr_f1, f1_val = f1_optimal_threshold(va_scores, va_lab)
    else:
        thr_f1, f1_val = thr_conservative, 0.0
    threshold = thr_f1 if args.threshold_strategy == "f1" else thr_conservative
    print(f"        val F1-opt threshold={thr_f1:.6f} (F1={f1_val:.3f}) | "
          f"conservative={thr_conservative:.6f} | using '{args.threshold_strategy}'={threshold:.6f}")

    # ── 6. FINAL evaluation on TEST (never used for anything above) ───────────
    print("  [6/6] Final evaluation on held-out TEST ...")
    te_scores = reconstruction_scores(model, te_seqs, device)
    te_auc = roc_auc(te_lab, te_scores) if int(te_lab.sum()) > 0 else 0.5
    te_pred = (te_scores >= threshold).astype(int)
    te_p, te_r, te_f1 = prec_rec_f1(te_lab, te_pred)
    tn, fp, fn, tp = _cm(te_lab, te_pred)
    # val metrics for reference
    va_pred = (va_scores >= threshold).astype(int)
    va_p, va_r, va_f1 = prec_rec_f1(va_lab, va_pred)
    va_auc = roc_auc(va_lab, va_scores) if int(va_lab.sum()) > 0 else 0.5

    print()
    print(f"     VALIDATION : AUC={va_auc:.4f} P={va_p:.4f} R={va_r:.4f} F1={va_f1:.4f}")
    print(f"  >> TEST (held-out): AUC={te_auc:.4f} P={te_p:.4f} R={te_r:.4f} F1={te_f1:.4f}")
    print(f"     TEST confusion: TN={tn:,} FP={fp:,} FN={fn:,} TP={tp:,}")

    # ── Save artifacts (drop-in compatible) ──────────────────────────────────
    torch.save({"model_state": model.state_dict(), "input_dim": n_feat,
                "model_dim": args.model_dim, "heads": args.heads,
                "layers": args.layers, "sequence_length": args.seq_len},
               out / "transformer_autoencoder.pt")

    report = {
        "architecture": f"TransformerAutoencoder dim={args.model_dim} heads={args.heads} layers={args.layers}",
        "protocol": "leak-free: scaler fit on train; threshold tuned on val; metrics on held-out test",
        "data_file": str(args.data),
        "split": {"val_frac": args.val_frac, "test_frac": args.test_frac,
                  "train_seq": len(tr_seqs), "val_seq": len(va_seqs), "test_seq": len(te_seqs)},
        "threshold": threshold,
        "threshold_strategy": args.threshold_strategy,
        "threshold_f1_optimal_val": thr_f1,
        "threshold_conservative_val": thr_conservative,
        # 'metrics' = held-out TEST (the honest headline numbers)
        "metrics": {"split": "test", "auc": te_auc, "precision": te_p, "recall": te_r,
                    "f1": te_f1, "tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "validation_metrics": {"auc": va_auc, "precision": va_p, "recall": va_r, "f1": va_f1},
        "training_history": {"pretrain": pre_hist, "finetune": ft_hist},
    }
    (out / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    with (out / "anomaly_predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["end_index", "anomaly_score", "sequence_label", "predicted", "split"])
        for e, s, l, p in zip(te_end, te_scores, te_lab, te_pred):
            w.writerow([int(e), f"{s:.8f}", int(l), int(p), "test"])
    for name, hist in (("pretraining_loss.csv", pre_hist), ("finetuning_loss.csv", ft_hist)):
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["epoch", "train_loss", "val_loss"])
            for h in hist:
                w.writerow([h["epoch"], f"{h['train_loss']:.8f}", f"{h['val_loss']:.8f}"])
    save_plots(out / "plots", pre_hist, ft_hist, te_scores, te_lab, threshold, te_auc)

    print()
    print("=" * 64)
    print("  DONE (leak-free). Headline metrics in training_report.json are the")
    print("  HELD-OUT TEST split — safe to quote. Artifacts are deploy-compatible.")
    print("=" * 64)


if __name__ == "__main__":
    main()
