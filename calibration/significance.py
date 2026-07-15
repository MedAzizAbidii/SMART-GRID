"""
calibration/significance.py — Part B.8: bootstrap CIs + paired significance
tests (McNemar + paired t-test/Wilcoxon across folds) vs label-free baselines,
with effect sizes.

Rebuilds the SAME 5-fold grouped-by-meter split as cv.py (identical seed) so
the proposed model and each label-free baseline (Isolation Forest, LSTM
Autoencoder, One-Class SVM — reused from benchmark/models.py, Phase 1, no
duplication) are compared on IDENTICAL held-out folds. Predictions from all
5 folds are pooled into one combined "cross-validated predictions covering
the whole dataset" vector for the pooled McNemar test and pooled bootstrap
CI; per-fold F1 vectors are used for the paired t-test/Wilcoxon/effect size
(the correct unit of comparison for a paired test across folds).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import ttest_rel, wilcoxon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml_pipeline.preprocessing import load_dataset, build_feature_frame
from benchmark.metrics import all_metrics, bootstrap_ci, mcnemar_test, f1_optimal_threshold
from benchmark.models import IsolationForestModel, OneClassSVMModel, LSTMAutoencoderModel
from calibration.cv import DATA, make_fold, train_fast, score as recon_score

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
K = 5
SEED = 42


def run_pooled_cv(seq_len=8):
    frame = load_dataset(DATA)
    features_all, cols = build_feature_frame(frame)
    meters = frame["meter_id"].astype(str).values
    unique_meters = np.unique(meters)
    rng = np.random.default_rng(SEED)
    groups = np.array_split(rng.permutation(unique_meters), K)

    pooled = {"proposed": {"y": [], "pred": [], "fold_f1": []},
              "isolation_forest": {"y": [], "pred": [], "fold_f1": []},
              "lstm_autoencoder": {"y": [], "pred": [], "fold_f1": []},
              "one_class_svm": {"y": [], "pred": [], "fold_f1": []}}

    for i, fold_meters in enumerate(groups):
        other = np.setdiff1d(unique_meters, fold_meters)
        (tr_s, tr_l), (va_s, va_l), (te_s, te_l) = make_fold(
            frame, features_all, meters, fold_meters, other, seq_len)
        if len(te_s) == 0 or len(tr_s) == 0:
            continue

        # proposed model (reuses cv.py's fast fixed-budget trainer)
        model = train_fast(tr_s, tr_l, va_s, va_l, seed=SEED + i)
        va_sc = recon_score(model, va_s)
        thr, _ = f1_optimal_threshold(va_sc, va_l) if (va_l == 1).any() else \
            (float(va_sc.mean() + 3 * va_sc.std()), 0.0)
        te_sc = recon_score(model, te_s)
        pred = (te_sc >= thr).astype(int)
        pooled["proposed"]["y"].extend(te_l.tolist()); pooled["proposed"]["pred"].extend(pred.tolist())
        pooled["proposed"]["fold_f1"].append(all_metrics(te_l, te_sc, pred)["f1"])

        for key, cls in (("isolation_forest", IsolationForestModel),
                         ("lstm_autoencoder", LSTMAutoencoderModel),
                         ("one_class_svm", OneClassSVMModel)):
            try:
                if cls is LSTMAutoencoderModel:
                    m = cls({"pretrain_epochs": 5, "batch_size": 128, "lr": 5e-4, "model_dim": 64}, seed=SEED + i)
                else:
                    m = cls(seed=SEED + i)
                m.fit(tr_s, tr_l)
                va_sc_b = m.score(va_s)
                thr_b, _ = f1_optimal_threshold(va_sc_b, va_l) if (va_l == 1).any() else \
                    (float(va_sc_b.mean() + 3 * va_sc_b.std()), 0.0)
                te_sc_b = m.score(te_s)
                pred_b = (te_sc_b >= thr_b).astype(int)
                pooled[key]["y"].extend(te_l.tolist()); pooled[key]["pred"].extend(pred_b.tolist())
                pooled[key]["fold_f1"].append(all_metrics(te_l, te_sc_b, pred_b)["f1"])
            except Exception as exc:
                print(f"    [skip {key} fold {i}] {exc}")
        print(f"  fold {i+1}/{K} done "
              f"(proposed F1={pooled['proposed']['fold_f1'][-1]:.3f})")

    for k in pooled:
        pooled[k]["y"] = np.array(pooled[k]["y"])
        pooled[k]["pred"] = np.array(pooled[k]["pred"])
    return pooled


def effect_size_paired(a, b):
    diff = np.array(a) - np.array(b)
    sd = diff.std(ddof=1)
    return float(diff.mean() / sd) if sd > 1e-12 else 0.0


def main():
    RES.mkdir(parents=True, exist_ok=True)
    print("=" * 64)
    print(f"  STATISTICAL SIGNIFICANCE — proposed vs label-free baselines ({K}-fold, pooled)")
    print("=" * 64)
    pooled = run_pooled_cv()

    prop = pooled["proposed"]
    y_full = prop["y"]

    # pooled bootstrap CI (proposed model's pooled cross-validated predictions)
    scores_proxy = prop["pred"].astype(float)   # binary preds as a degenerate "score" for CI on F1 itself
    ci_f1 = bootstrap_ci(y_full, scores_proxy, prop["pred"], "f1", n_boot=1000, seed=SEED)
    print(f"\n  Proposed pooled F1 = {ci_f1[0]:.4f}  95% CI [{ci_f1[1]:.4f}, {ci_f1[2]:.4f}]")

    results = {"pooled_f1_ci": {"point": ci_f1[0], "lo": ci_f1[1], "hi": ci_f1[2]},
              "fold_f1": {"proposed": prop["fold_f1"]}, "comparisons": {}}

    for key in ("isolation_forest", "lstm_autoencoder", "one_class_svm"):
        base = pooled[key]
        if len(base["fold_f1"]) != len(prop["fold_f1"]) or len(base["fold_f1"]) < 2:
            print(f"  [skip {key}] insufficient paired folds")
            continue
        mc = mcnemar_test(y_full, prop["pred"], base["pred"])
        t_stat, t_p = ttest_rel(prop["fold_f1"], base["fold_f1"])
        try:
            w_stat, w_p = wilcoxon(prop["fold_f1"], base["fold_f1"])
        except ValueError:
            w_stat, w_p = float("nan"), 1.0   # identical values -> not testable
        d = effect_size_paired(prop["fold_f1"], base["fold_f1"])
        print(f"\n  vs {key}: fold F1 mean={np.mean(base['fold_f1']):.4f} "
              f"(proposed={np.mean(prop['fold_f1']):.4f})")
        print(f"    McNemar (pooled)     : chi2={mc['statistic']:.3f} p={mc['p_value']:.4g}")
        print(f"    Paired t-test (folds): t={t_stat:.3f} p={t_p:.4g}")
        print(f"    Wilcoxon (folds)     : W={w_stat} p={w_p:.4g}")
        print(f"    Cohen's d (paired)   : {d:.3f}")
        results["fold_f1"][key] = base["fold_f1"]
        results["comparisons"][key] = {
            "mcnemar": mc, "paired_ttest": {"t": t_stat, "p": t_p},
            "wilcoxon": {"stat": None if np.isnan(w_stat) else float(w_stat), "p": float(w_p)},
            "cohens_d": d,
        }

    (RES / "significance_results.json").write_text(json.dumps(results, indent=2, default=float))
    print(f"\n  Saved: {RES / 'significance_results.json'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
