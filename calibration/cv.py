"""
calibration/cv.py — Part B.6-7: k-fold + repeated CV with the leak-free
protocol enforced INSIDE each fold.

Protocol per fold (GROUPED by meter_id, so a meter's data never straddles
folds — enforced by a unit test in tests/test_calibration.py):
  - Assign each of the ~50 meters to one of k groups (fixed seed).
  - For fold i: TEST = all rows of meters in group i.
  - For the remaining meters: last 15% of EACH meter's own timeline -> VAL,
    rest -> TRAIN (mirrors run_transformer_autoencoder.prepare_split_sequences'
    per-meter temporal logic, just restricted to the non-test meters).
  - Scaler fit on fold-TRAIN only. Threshold fit on fold-VAL only. Metrics
    computed on fold-TEST only.

Reuses ablation.model (fast fixed-budget architecture — same one used for the
Phase-2 ablation study) so no training code is duplicated; a temporary model
is trained per fold and discarded (outputs/early_stopping_final is never
touched).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml_pipeline.preprocessing import load_dataset, build_feature_frame
from benchmark.metrics import all_metrics, f1_optimal_threshold
from ablation.model import build_model, make_optimizer, make_loss
from ablation.experiments import BASE as ABLATION_BASE

DATA = ROOT.parent / "data" / "scenario_test" / "donnees_smart_meters.csv"
HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def _windows(values, labels, meters, meter_list, seq_len):
    seqs, labs = [], []
    for mid in meter_list:
        rows = np.where(meters == mid)[0]
        if len(rows) < seq_len:
            continue
        v, lab = values[rows], labels[rows]
        for end in range(seq_len, len(v) + 1):
            seqs.append(v[end - seq_len:end])
            labs.append(int(lab[end - 1]))
    if not seqs:
        return np.empty((0, seq_len, values.shape[1]), "float32"), np.array([], int)
    return np.stack(seqs).astype("float32"), np.asarray(labs)


def make_fold(frame, features_all, meters, fold_meters, other_meters, seq_len, val_frac=0.15):
    from sklearn.preprocessing import StandardScaler
    train_meters, val_rows_by_meter = [], []
    # per-meter temporal split among the non-test meters
    train_mask = np.zeros(len(frame), dtype=bool)
    val_mask = np.zeros(len(frame), dtype=bool)
    for mid in other_meters:
        idx = np.where(meters == mid)[0]
        n_val = max(1, int(len(idx) * val_frac))
        train_mask[idx[:-n_val]] = True
        val_mask[idx[-n_val:]] = True
    test_mask = np.isin(meters, fold_meters)

    scaler = StandardScaler().fit(features_all.values[train_mask])
    values = scaler.transform(features_all.values).astype("float32")
    labels = frame["is_alert"].values.astype(int)

    tr_s, tr_l = _windows(values[train_mask], labels[train_mask], meters[train_mask],
                          np.unique(meters[train_mask]), seq_len)
    va_s, va_l = _windows(values[val_mask], labels[val_mask], meters[val_mask],
                          np.unique(meters[val_mask]), seq_len)
    te_s, te_l = _windows(values[test_mask], labels[test_mask], meters[test_mask],
                          np.unique(meters[test_mask]), seq_len)
    return (tr_s, tr_l), (va_s, va_l), (te_s, te_l)


def train_fast(tr_s, tr_l, va_s, va_l, seed):
    cfg = dict(ABLATION_BASE)
    torch.manual_seed(seed)
    model = build_model(tr_s.shape[-1], cfg)
    opt = make_optimizer(cfg["optimizer"], model.parameters(), cfg["lr"])
    crit = make_loss(cfg["loss"])

    def epoch(data):
        if len(data) == 0:
            return
        loader = DataLoader(TensorDataset(torch.tensor(data, dtype=torch.float32)),
                            batch_size=cfg["batch_size"], shuffle=True)
        model.train()
        for (xb,) in loader:
            opt.zero_grad(); loss = crit(model(xb), xb); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()

    for _ in range(cfg["pretrain_epochs"]):
        epoch(tr_s)
    normal = tr_s[tr_l == 0] if (tr_l == 0).any() else tr_s
    for _ in range(cfg["finetune_epochs"]):
        epoch(normal)
    return model


def score(model, seqs):
    model.eval()
    out = np.empty(len(seqs), "float32")
    with torch.no_grad():
        for i in range(0, len(seqs), 256):
            xb = torch.tensor(seqs[i:i+256], dtype=torch.float32)
            rec = model(xb)
            out[i:i+256] = ((rec - xb) ** 2).mean(dim=(1, 2)).numpy()
    return out


def run_cv(k: int, seed: int = 42, seq_len: int = 8, verbose=True):
    frame = load_dataset(DATA)
    features_all, cols = build_feature_frame(frame)
    meters = frame["meter_id"].astype(str).values
    unique_meters = np.unique(meters)
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(unique_meters)
    groups = np.array_split(shuffled, k)

    # sanity: verify NO meter appears in >1 group (the "no straddling" guarantee)
    seen = set()
    for g in groups:
        for m in g:
            assert m not in seen, f"meter {m} assigned to multiple CV folds"
            seen.add(m)

    fold_metrics = []
    for i, fold_meters in enumerate(groups):
        other_meters = np.setdiff1d(unique_meters, fold_meters)
        (tr_s, tr_l), (va_s, va_l), (te_s, te_l) = make_fold(
            frame, features_all, meters, fold_meters, other_meters, seq_len)
        if len(te_s) == 0 or len(tr_s) == 0:
            continue
        model = train_fast(tr_s, tr_l, va_s, va_l, seed=seed + i)
        va_scores = score(model, va_s)
        threshold, _ = f1_optimal_threshold(va_scores, va_l) if (va_l == 1).any() else \
            (float(va_scores.mean() + 3 * va_scores.std()), 0.0)
        te_scores = score(model, te_s)
        pred = (te_scores >= threshold).astype(int)
        m = all_metrics(te_l, te_scores, pred)
        m["threshold"] = threshold
        m["fold"] = i
        m["n_test_meters"] = len(fold_meters)
        m["n_test_seq"] = len(te_s)
        fold_metrics.append(m)
        if verbose:
            print(f"    fold {i+1}/{k}: F1={m['f1']:.3f} AUC={m['roc_auc']:.3f} "
                  f"n_test={len(te_s)} (meters={list(fold_meters)})")
    return fold_metrics


def summarize(fold_metrics, keys=("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "mcc")):
    out = {}
    for k in keys:
        vals = [m[k] for m in fold_metrics]
        out[k] = {"mean": float(np.mean(vals)), "std": float(np.std(vals)), "values": vals}
    return out


def main():
    RES.mkdir(parents=True, exist_ok=True)
    print("=" * 64)
    print("  K-FOLD CROSS-VALIDATION (grouped by meter, leak-free per fold)")
    print("=" * 64)

    results = {}
    for k in (5, 10):
        print(f"\n  --- k={k} ---")
        fm = run_cv(k, seed=42)
        summ = summarize(fm)
        results[f"k{k}"] = {"folds": fm, "summary": summ}
        print(f"  k={k} F1 = {summ['f1']['mean']:.4f} +/- {summ['f1']['std']:.4f}")

    print("\n  --- Repeated 5-fold CV (3 seeds, quantifies seed/split variance) ---")
    repeated = []
    for seed in (1, 2, 3):
        fm = run_cv(5, seed=seed, verbose=False)
        f1s = [m["f1"] for m in fm]
        repeated.append({"seed": seed, "f1_mean": float(np.mean(f1s)), "f1_values": f1s})
        print(f"    seed={seed}: F1={np.mean(f1s):.4f} (per-fold: {[round(x,3) for x in f1s]})")
    all_f1 = [x for r in repeated for x in r["f1_values"]]
    results["repeated_5fold"] = {
        "per_seed": repeated,
        "overall_f1_mean": float(np.mean(all_f1)), "overall_f1_std": float(np.std(all_f1)),
    }
    print(f"  Overall (3 seeds x 5 folds = {len(all_f1)} runs): "
          f"F1 = {results['repeated_5fold']['overall_f1_mean']:.4f} +/- "
          f"{results['repeated_5fold']['overall_f1_std']:.4f}")

    (RES / "cv_results.json").write_text(json.dumps(results, indent=2))
    print(f"\n  Saved: {RES / 'cv_results.json'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
