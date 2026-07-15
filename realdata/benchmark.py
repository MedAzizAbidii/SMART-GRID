"""
realdata/benchmark.py — Phase-1 benchmark re-run on reconciled SGCC, at the
CONSUMER level. Same 7 models, same leak-free protocol, same metric kernels.

Two model families, each on its natural representation (documented in Step 0):
  * reconstruction (Transformer-AE, LSTM-AE): trained unsupervised on
    train-NORMAL windows; consumer score = mean window reconstruction error.
  * classical/tree (IsolationForest, OneClassSVM, RandomForest, XGBoost,
    LightGBM): consumer-level AGGREGATE feature vector.

The within-family reconstruction comparison (Transformer vs LSTM) is
apples-to-apples (identical windows); cross-family numbers are reported with
that caveat, exactly as the SGCC literature compares heterogeneous models on
consumer-level AUC.
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
from benchmark.metrics import all_metrics, bootstrap_ci, f1_optimal_threshold

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

RECON_CFG = {"encoder": "transformer", "use_bottleneck": True, "use_positional": True,
             "use_attention": True, "model_dim": 64, "latent_dim": 16, "heads": 4,
             "layers": 2, "dropout": 0.1, "activation": "gelu", "ff_dim": 256,
             "loss": "mse", "optimizer": "adamw", "lr": 5e-4, "batch_size": 256, "epochs": 6}


def _recon_model(name, d, masks, cfg):
    wins = d["wins_scaled"]; widx = d["widx"]; win_split = d["win_split"]
    tr_idx = d["train_norm_win_idx"]
    t0 = time.perf_counter()
    model = train_recon(wins[tr_idx], cfg, seed=SEED)
    train_time = time.perf_counter() - t0
    # score val+test windows, aggregate to consumer
    scored_mask = np.isin(win_split, ["val", "test"])
    ws = window_scores(model, wins[scored_mask])
    full = np.full(len(widx), np.nan); full[scored_mask] = ws
    cons_sc = consumer_scores(full, widx, int(d["n_consumers"]), agg="mean")
    res = evaluate_consumer(cons_sc, d["cons_flags"], masks)
    res["train_time_s"] = round(train_time, 2)
    return res


def _classical(name, d, masks):
    from benchmark.models import (IsolationForestModel, OneClassSVMModel,
                                  RandomForestModel, XGBoostModel, LightGBMModel)
    agg = d["agg_scaled"]; flags = d["cons_flags"]; split = d["cons_split"]
    tr = split == "train"; va = split == "val"; te = split == "test"

    t0 = time.perf_counter()
    if name in ("isolation_forest", "one_class_svm"):
        # unsupervised: fit on TRAIN NON-THEFT consumers
        fitmask = tr & (flags == 0)
        if name == "isolation_forest":
            from sklearn.ensemble import IsolationForest
            m = IsolationForest(n_estimators=200, random_state=SEED, n_jobs=-1)
            m.fit(agg[fitmask]); sc = lambda A: -m.decision_function(A)
        else:
            from sklearn.linear_model import SGDOneClassSVM
            m = SGDOneClassSVM(nu=0.05, random_state=SEED)
            m.fit(agg[fitmask]); sc = lambda A: -m.decision_function(A)
        val_s, te_s = sc(agg[va]), sc(agg[te])
    else:
        # supervised: fit on TRAIN consumers with FLAG
        y = flags[tr]
        if name == "random_forest":
            from sklearn.ensemble import RandomForestClassifier
            m = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                       random_state=SEED, n_jobs=-1)
            m.fit(agg[tr], y); sc = lambda A: m.predict_proba(A)[:, 1]
        elif name == "xgboost":
            import xgboost as xgb
            pos = max(int(y.sum()), 1)
            m = xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.1,
                                  eval_metric="logloss", random_state=SEED, n_jobs=-1,
                                  tree_method="hist", scale_pos_weight=(len(y) - pos) / pos)
            m.fit(agg[tr], y); sc = lambda A: m.predict_proba(A)[:, 1]
        else:
            import lightgbm as lgb
            m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05,
                                   class_weight="balanced", random_state=SEED, n_jobs=-1, verbose=-1)
            m.fit(agg[tr], y); sc = lambda A: m.predict_proba(A)[:, 1]
        val_s, te_s = sc(agg[va]), sc(agg[te])
    train_time = time.perf_counter() - t0

    val_y, te_y = flags[va], flags[te]
    thr, _ = f1_optimal_threshold(val_s, val_y) if val_y.sum() > 0 else \
        (float(val_s.mean() + 3 * val_s.std()), 0.0)
    pred = (te_s >= thr).astype(int)
    m2 = all_metrics(te_y, te_s, pred)
    ci = {k: bootstrap_ci(te_y, te_s, pred, k, 500, SEED) for k in ["f1", "roc_auc", "pr_auc", "mcc"]}
    return {"metrics": m2, "ci": ci, "threshold": float(thr),
            "test_scores": te_s, "test_labels": te_y, "test_pred": pred,
            "train_time_s": round(train_time, 2)}


MODELS = {
    "isolation_forest": ("classical", "Isolation Forest"),
    "one_class_svm": ("classical", "One-Class SVM"),
    "random_forest": ("classical", "Random Forest"),
    "xgboost": ("classical", "XGBoost"),
    "lightgbm": ("classical", "LightGBM"),
    "lstm_autoencoder": ("recon", "LSTM Autoencoder"),
    "transformer_autoencoder": ("recon", "Transformer Autoencoder (proposed)"),
}


def main():
    RES.mkdir(parents=True, exist_ok=True)
    d = build()
    masks = consumer_split_masks(d["cons_split"])
    print("=" * 66)
    print("  SGCC CONSUMER-LEVEL BENCHMARK (leak-free, split by consumer)")
    print("=" * 66)
    print(f"  consumers: train {masks['train'].sum()}, val {masks['val'].sum()}, "
          f"test {masks['test'].sum()} | test theft={int(d['cons_flags'][masks['test']].sum())}")

    results = {}
    for key, (fam, name) in MODELS.items():
        t0 = time.perf_counter()
        try:
            if fam == "recon":
                cfg = dict(RECON_CFG)
                if key == "lstm_autoencoder":
                    cfg["encoder"] = "lstm"   # handled below via LSTM path
                    r = _recon_lstm(d, masks, cfg)
                else:
                    r = _recon_model(key, d, masks, cfg)
            else:
                r = _classical(key, d, masks)
            r["name"] = name; r["family"] = fam
            results[name] = r
            m = r["metrics"]
            print(f"  {name:<36} AUC={m['roc_auc']:.3f} PR-AUC={m['pr_auc']:.3f} "
                  f"F1={m['f1']:.3f} MCC={m['mcc']:.3f}  ({time.perf_counter()-t0:.1f}s)")
        except Exception as exc:
            print(f"  [SKIP] {name}: {exc}")

    # save (no big arrays)
    dump = {n: {k: v for k, v in r.items() if k not in ("test_scores", "test_labels", "test_pred")}
            for n, r in results.items()}
    (RES / "benchmark_results.json").write_text(json.dumps(dump, indent=2, default=float))
    # comparison table sorted by ROC-AUC (consumer-level standard for SGCC)
    rows = [{"model": n, **{k: r["metrics"][k] for k in
             ["roc_auc", "pr_auc", "f1", "precision", "recall", "mcc", "accuracy"]},
             "train_s": r.get("train_time_s")} for n, r in results.items()]
    df = pd.DataFrame(rows).sort_values("roc_auc", ascending=False)
    df.to_csv(RES / "benchmark_comparison.csv", index=False)
    try:
        df.to_excel(RES / "benchmark_comparison.xlsx", index=False)
    except Exception:
        pass
    df.round(4).to_latex(RES / "benchmark_comparison.tex", index=False,
                         caption="SGCC consumer-level benchmark.", label="tab:sgcc_bench")
    print(f"\n  Winner (ROC-AUC): {df.iloc[0]['model']}  AUC={df.iloc[0]['roc_auc']:.4f}")
    print(f"  Saved: {RES / 'benchmark_comparison.csv'}")
    print("=" * 66)


def _recon_lstm(d, masks, cfg):
    """LSTM-AE via benchmark.models.LSTMAutoencoderModel on the same windows."""
    from benchmark.models import LSTMAutoencoderModel
    wins = d["wins_scaled"]; widx = d["widx"]; win_split = d["win_split"]; tr_idx = d["train_norm_win_idx"]
    t0 = time.perf_counter()
    m = LSTMAutoencoderModel({"pretrain_epochs": cfg["epochs"], "batch_size": cfg["batch_size"],
                              "lr": cfg["lr"], "model_dim": cfg["model_dim"]}, seed=SEED)
    m.fit(wins[tr_idx], np.zeros(len(tr_idx), int))
    train_time = time.perf_counter() - t0
    scored_mask = np.isin(win_split, ["val", "test"])
    ws = m.score(wins[scored_mask])
    full = np.full(len(widx), np.nan); full[scored_mask] = ws
    cons_sc = consumer_scores(full, widx, int(d["n_consumers"]), agg="mean")
    res = evaluate_consumer(cons_sc, d["cons_flags"], masks)
    res["train_time_s"] = round(train_time, 2)
    return res


if __name__ == "__main__":
    main()
