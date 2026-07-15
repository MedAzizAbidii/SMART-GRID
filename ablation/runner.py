"""
ablation/runner.py — automated, resumable ablation experiment runner.

Reuses the leak-free split (prepare_split_sequences) and the Phase-1 metric
kernels (benchmark.metrics) so preprocessing, protocol, metrics and CIs are
IDENTICAL to the benchmark. Each experiment changes exactly one component;
retrain=False experiments reuse the baseline's trained model.

Usage:
  .\.venv\Scripts\python.exe -m ablation.runner                 # run all (resume)
  .\.venv\Scripts\python.exe -m ablation.runner --only E05_no_attention
  .\.venv\Scripts\python.exe -m ablation.runner --fresh         # ignore cached results
"""
from __future__ import annotations

import argparse
import gc
import json
import time
import tracemalloc
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_transformer_autoencoder import prepare_split_sequences
from benchmark.metrics import all_metrics, f1_optimal_threshold, bootstrap_ci
from ablation.model import build_model, make_optimizer, make_loss
from ablation.experiments import all_experiments, BASE

DATA = ROOT.parent / "data" / "scenario_test" / "donnees_smart_meters.csv"
RES = Path(__file__).resolve().parent / "results"
SEED = 42
N_BOOT = 200

_split_cache: dict = {}
_baseline_scores: dict = {}     # {"val":..., "test":..., "va_lab":..., "te_lab":...}


def get_split(seq_len: int, scale: bool):
    key = (seq_len, scale)
    if key not in _split_cache:
        _split_cache[key] = prepare_split_sequences(
            DATA, seq_len, BASE_val_frac(), BASE_test_frac(), scale=scale)
    return _split_cache[key]


def BASE_val_frac(): return 0.15
def BASE_test_frac(): return 0.15


def select_features(tr, va, te, k):
    """Leak-free top-k feature selection by TRAIN variance."""
    tr_s = tr[0]
    var = tr_s.reshape(-1, tr_s.shape[-1]).var(axis=0)
    idx = np.argsort(var)[::-1][:k]
    idx = np.sort(idx)
    sub = lambda t: (t[0][:, :, idx], t[1], t[2])
    return sub(tr), sub(va), sub(te), idx


def pick_threshold(strategy, val_scores, val_labels):
    normal = val_scores[val_labels == 0] if (val_labels == 0).any() else val_scores
    if strategy == "f1":
        return f1_optimal_threshold(val_scores, val_labels)[0]
    if strategy == "p95":
        return float(np.quantile(normal, 0.95))
    if strategy == "p99":
        return float(np.quantile(normal, 0.99))
    if strategy == "mad":
        med = float(np.median(normal))
        mad = float(np.median(np.abs(normal - med)))
        return med + 3 * 1.4826 * mad
    if strategy == "adaptive":
        return float(normal.mean() + 3 * normal.std())
    return f1_optimal_threshold(val_scores, val_labels)[0]


def recon_scores(model, seqs, device):
    model.eval()
    out = np.empty(len(seqs), "float32")
    with torch.no_grad():
        for i in range(0, len(seqs), 256):
            xb = torch.tensor(seqs[i:i+256], dtype=torch.float32, device=device)
            rec = model(xb)
            out[i:i+256] = ((rec - xb) ** 2).mean(dim=(1, 2)).cpu().numpy()
    return out


def train_recon(cfg, tr, va, device):
    (tr_s, tr_l, _), (va_s, va_l, _) = tr, va
    torch.manual_seed(SEED)
    model = build_model(tr_s.shape[-1], cfg).to(device)
    opt = make_optimizer(cfg["optimizer"], model.parameters(), cfg["lr"])
    crit = make_loss(cfg["loss"])
    va_norm = va_s[va_l == 0] if (va_l == 0).any() else va_s

    def epoch(data):
        loader = DataLoader(TensorDataset(torch.tensor(data, dtype=torch.float32)),
                            batch_size=cfg["batch_size"], shuffle=True)
        model.train()
        for (xb,) in loader:
            xb = xb.to(device); opt.zero_grad()
            loss = crit(model(xb), xb); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()

    for _ in range(cfg["pretrain_epochs"]):
        epoch(tr_s)                                   # pretrain on all train
    for _ in range(cfg["finetune_epochs"]):
        epoch(tr_s[tr_l == 0])                        # finetune on train-normal
    return model


def run_experiment(exp, device):
    cfg = exp["cfg"]
    tr, va, te, cols, scaler, art, frame = get_split(cfg["seq_len"], cfg["scale"])
    tr3, va3, te3 = (tr[0], tr[1], tr[2]), (va[0], va[1], va[2]), (te[0], te[1], te[2])
    sel_idx = None
    if cfg.get("feature_k"):
        tr3, va3, te3, sel_idx = select_features(tr3, va3, te3, cfg["feature_k"])

    gc.collect(); tracemalloc.start(); t0 = time.perf_counter()
    if exp["retrain"]:
        model = train_recon(cfg, (tr3[0], tr3[1], None), (va3[0], va3[1], None), device)
        va_scores = recon_scores(model, va3[0], device)
        n_params = sum(p.numel() for p in model.parameters())
        size_kb = sum(p.numel() * p.element_size() for p in model.parameters()) / 1024
        t_pred0 = time.perf_counter()
        te_scores = recon_scores(model, te3[0], device)
        latency_ms = 1000 * (time.perf_counter() - t_pred0) / max(len(te3[0]), 1)
    else:
        # reuse baseline model outputs (threshold / XAI experiments)
        va_scores = _baseline_scores["val"]; te_scores = _baseline_scores["test"]
        va3 = (None, _baseline_scores["va_lab"], None)
        te3 = (None, _baseline_scores["te_lab"], None)
        n_params = _baseline_scores["n_params"]; size_kb = _baseline_scores["size_kb"]
        latency_ms = _baseline_scores["latency_ms"]
        if exp["id"] == "E20_no_xai":
            latency_ms = _baseline_scores["latency_ms"]      # detection latency only; IG adds ~100ms/alert
    train_time = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()

    va_lab, te_lab = va3[1], te3[1]
    threshold = pick_threshold(cfg["threshold"], va_scores, va_lab)
    te_pred = (te_scores >= threshold).astype(int)
    m = all_metrics(te_lab, te_scores, te_pred)
    ci = {mm: bootstrap_ci(te_lab, te_scores, te_pred, mm, N_BOOT, SEED)
          for mm in ["f1", "roc_auc", "pr_auc", "mcc"]}

    if exp["id"] == "E01_baseline":
        _baseline_scores.update(val=va_scores, test=te_scores, va_lab=va_lab,
                                te_lab=te_lab, n_params=n_params, size_kb=size_kb,
                                latency_ms=latency_ms, pred=te_pred)

    return {
        "id": exp["id"], "group": exp["group"], "component": exp["component"],
        "label": exp["label"], "changes": exp["changes"], "retrain": exp["retrain"],
        "metrics": m, "ci": ci, "threshold": float(threshold),
        "n_params": int(n_params), "model_size_kb": round(size_kb, 1),
        "train_time_s": round(train_time, 2), "infer_latency_ms": round(float(latency_ms), 4),
        "memory_mb": round(peak / 1e6, 2),
        "selected_features": None if sel_idx is None else [cols[i] for i in sel_idx],
        "pred": te_pred.tolist(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default=None, help="run a single experiment id")
    ap.add_argument("--fresh", action="store_true", help="ignore cached results")
    args = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    exps = all_experiments()
    # baseline must run first so retrain=False experiments can reuse it
    exps.sort(key=lambda e: (e["id"] != "E01_baseline", e["id"]))
    if args.only:
        exps = [e for e in exps if e["id"] == args.only]
        if not any(e["id"] == "E01_baseline" for e in exps):
            exps = [next(e for e in all_experiments() if e["id"] == "E01_baseline")] + exps

    print("=" * 68)
    print("  ABLATION STUDY — one component changed per experiment (leak-free)")
    print("=" * 68)
    done = 0
    for exp in exps:
        rp = RES / f"{exp['id']}.json"
        if rp.exists() and not args.fresh:
            r = json.loads(rp.read_text())
            if exp["id"] == "E01_baseline" and not _baseline_scores:
                # need to re-derive baseline scores for reuse -> force rerun once
                pass
            else:
                print(f"  [cached] {exp['id']:<20} F1={r['metrics']['f1']:.3f}")
                done += 1
                continue
        t0 = time.perf_counter()
        try:
            r = run_experiment(exp, device)
            rp.write_text(json.dumps({k: v for k, v in r.items() if k != "pred"}, indent=2))
            (RES / f"{exp['id']}_pred.json").write_text(json.dumps(r["pred"]))
            print(f"  [ok]     {exp['id']:<20} F1={r['metrics']['f1']:.3f} "
                  f"AUC={r['metrics']['roc_auc']:.3f} MCC={r['metrics']['mcc']:.3f} "
                  f"({time.perf_counter()-t0:.1f}s)")
            done += 1
        except Exception as exc:
            print(f"  [FAIL]   {exp['id']}: {exc}")
    print("=" * 68)
    print(f"  {done}/{len(exps)} experiments complete. Results in {RES}")
    print("  Next: python -m ablation.report")
    print("=" * 68)


if __name__ == "__main__":
    main()
