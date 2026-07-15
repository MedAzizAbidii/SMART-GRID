"""
realdata/ablation.py — the focused 5-experiment ablation on SGCC. This is the
DIRECT re-test of the Phase-2.5 finding ("attention doesn't help on the
synthetic data because it has no real temporal structure"). SGCC has genuine
weekly + 2-year seasonal structure, so this is where that conclusion either
survives contact with real data or doesn't.

Variants (all consumer-level, identical windows, same leak-free split):
  E1 full          — Transformer + attention + positional + bottleneck (baseline)
  E2 dense_encoder — Transformer replaced by token-wise MLP (no cross-time mixing)
  E3 no_attention  — attention removed (token-wise FFN)
  E4 no_positional — positional encoding removed
  E5 lstm_ae       — LSTM autoencoder (a different temporal inductive bias)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from realdata.prepare import build, consumer_split_masks
from realdata.common import (train_recon, window_scores, consumer_scores,
                             evaluate_consumer, SEED)

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

BASE = {"encoder": "transformer", "use_bottleneck": True, "use_positional": True,
        "use_attention": True, "model_dim": 64, "latent_dim": 16, "heads": 4,
        "layers": 2, "dropout": 0.1, "activation": "gelu", "ff_dim": 256,
        "loss": "mse", "optimizer": "adamw", "lr": 5e-4, "batch_size": 256, "epochs": 6}

EXPERIMENTS = [
    ("E1_full", "Full (Transformer+attention)", {}),
    ("E2_dense_encoder", "Dense encoder (no Transformer)", {"encoder": "dense"}),
    ("E3_no_attention", "No attention (token-wise FFN)", {"use_attention": False}),
    ("E4_no_positional", "No positional encoding", {"use_positional": False}),
    ("E5_lstm_ae", "LSTM autoencoder", {"_lstm": True}),
]


def run_variant(changes, d, masks):
    wins = d["wins_scaled"]; widx = d["widx"]; win_split = d["win_split"]; tr_idx = d["train_norm_win_idx"]
    scored_mask = np.isin(win_split, ["val", "test"])
    t0 = time.perf_counter()
    if changes.get("_lstm"):
        from benchmark.models import LSTMAutoencoderModel
        m = LSTMAutoencoderModel({"pretrain_epochs": BASE["epochs"], "batch_size": BASE["batch_size"],
                                  "lr": BASE["lr"], "model_dim": BASE["model_dim"]}, seed=SEED)
        m.fit(wins[tr_idx], np.zeros(len(tr_idx), int))
        ws = m.score(wins[scored_mask])
    else:
        cfg = dict(BASE); cfg.update(changes)
        model = train_recon(wins[tr_idx], cfg, seed=SEED)
        ws = window_scores(model, wins[scored_mask])
    train_time = time.perf_counter() - t0
    full = np.full(len(widx), np.nan); full[scored_mask] = ws
    cons_sc = consumer_scores(full, widx, int(d["n_consumers"]), agg="mean")
    res = evaluate_consumer(cons_sc, d["cons_flags"], masks)
    res["train_time_s"] = round(train_time, 2)
    return res


def main():
    RES.mkdir(parents=True, exist_ok=True)
    d = build()
    masks = consumer_split_masks(d["cons_split"])
    print("=" * 66)
    print("  SGCC ABLATION — does attention/Transformer help on REAL data?")
    print("=" * 66)
    results = {}
    for eid, label, changes in EXPERIMENTS:
        cache = RES / f"abl_{eid}.json"
        if cache.exists():
            r = json.loads(cache.read_text())
            print(f"  [cached] {label:<34} AUC={r['metrics']['roc_auc']:.3f} F1={r['metrics']['f1']:.3f}")
            results[eid] = r; continue
        t0 = time.perf_counter()
        r = run_variant(changes, d, masks)
        r["id"] = eid; r["label"] = label
        dump = {k: v for k, v in r.items() if k not in ("test_scores", "test_labels", "test_pred")}
        cache.write_text(json.dumps(dump, indent=2, default=float))
        results[eid] = dump
        m = r["metrics"]
        print(f"  {label:<34} AUC={m['roc_auc']:.3f} PR-AUC={m['pr_auc']:.3f} "
              f"F1={m['f1']:.3f} MCC={m['mcc']:.3f}  ({time.perf_counter()-t0:.1f}s)")

    base = results["E1_full"]["metrics"]
    print("\n  --- Contribution vs full model (delta AUC / delta F1 when ablated) ---")
    rows = []
    for eid, label, _ in EXPERIMENTS:
        m = results[eid]["metrics"]
        d_auc = base["roc_auc"] - m["roc_auc"]; d_f1 = base["f1"] - m["f1"]
        rows.append({"id": eid, "label": label, "roc_auc": m["roc_auc"], "pr_auc": m["pr_auc"],
                     "f1": m["f1"], "mcc": m["mcc"], "delta_auc_vs_full": d_auc, "delta_f1_vs_full": d_f1})
        if eid != "E1_full":
            verdict = "HELPS" if d_auc > 0.005 else ("HURTS" if d_auc < -0.005 else "no effect")
            print(f"    {label:<34} dAUC={d_auc:+.4f} dF1={d_f1:+.4f}  -> component {verdict}")
    pd.DataFrame(rows).to_csv(RES / "ablation_comparison.csv", index=False)
    (RES / "ablation_summary.json").write_text(json.dumps(rows, indent=2, default=float))
    print(f"\n  Saved: {RES / 'ablation_comparison.csv'}")
    print("=" * 66)


if __name__ == "__main__":
    main()
