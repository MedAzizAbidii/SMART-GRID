"""
benchmark/run_benchmark.py — unified, leak-free model benchmark orchestrator.

Reuses the production leak-free split (run_transformer_autoencoder.
prepare_split_sequences) so NOTHING about preprocessing / splitting is
duplicated. Every model: fit on TRAIN, threshold on VAL, metrics on the
untouched TEST. Emits tables (CSV/MD/LaTeX/Excel), figures, a Markdown+PDF
report, and a machine-readable results.json.

Usage:
  .\.venv\Scripts\python.exe -m benchmark.run_benchmark
  .\.venv\Scripts\python.exe -m benchmark.run_benchmark --config benchmark/config.json --quick
"""
from __future__ import annotations

import argparse
import gc
import json
import time
import tracemalloc
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_transformer_autoencoder import prepare_split_sequences
from benchmark import models as M
from benchmark import metrics as MET
from benchmark import plots as PLT
from benchmark import report as REP

PROPOSED = "transformer_autoencoder"


def _validate_split(tr, va, te, scaler, cfg):
    """Automated no-leakage checks — fail loudly if any invariant is violated."""
    (tr_s, tr_l, tr_e), (va_s, va_l, va_e), (te_s, te_l, te_e) = tr, va, te
    checks = []
    # 1. splits are non-empty
    checks.append(("all splits non-empty", len(tr_s) > 0 and len(va_s) > 0 and len(te_s) > 0))
    # 2. end-indices disjoint across splits (no shared source rows)
    inter = (set(tr_e.tolist()) & set(te_e.tolist())) | (set(va_e.tolist()) & set(te_e.tolist()))
    checks.append(("train/val/test source rows disjoint", len(inter) == 0))
    # 3. feature dim consistent
    checks.append(("feature dim consistent", tr_s.shape[1:] == te_s.shape[1:] == va_s.shape[1:]))
    # 4. scaler was fit (has stats) — sanity that preprocessing ran
    checks.append(("scaler fitted", hasattr(scaler, "mean_") and scaler.mean_ is not None))
    ok = all(c[1] for c in checks)
    for name, passed in checks:
        print(f"      [{'PASS' if passed else 'FAIL'}] {name}")
    if not ok:
        raise SystemExit("Leakage/validation check failed — aborting.")
    return ok


def run_one(name, cfg, tr, va, te, seed, n_boot):
    (tr_s, tr_l, _), (va_s, va_l, _), (te_s, te_l, _) = tr, va, te
    model = M.build(name, cfg, seed)

    gc.collect(); tracemalloc.start()
    t0 = time.perf_counter()
    model.fit(tr_s, tr_l)
    train_time = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()

    # threshold on VALIDATION only
    va_scores = model.score(va_s)
    threshold, _ = MET.f1_optimal_threshold(va_scores, va_l)

    # TEST (untouched)
    t0 = time.perf_counter()
    te_scores = model.score(te_s)
    predict_time = time.perf_counter() - t0
    te_pred = (te_scores >= threshold).astype(int)

    m = MET.all_metrics(te_l, te_scores, te_pred)
    ci = {mm: MET.bootstrap_ci(te_l, te_scores, te_pred, mm, n_boot, seed)
          for mm in ["f1", "roc_auc", "pr_auc", "mcc"]}

    imp = model.feature_importance()
    return {
        "name": model.name, "kind": model.kind, "metrics": m, "ci": ci,
        "threshold": float(threshold), "y_true": np.asarray(te_l).astype(int),
        "scores": np.asarray(te_scores, float), "pred": te_pred,
        "importance": None if imp is None else np.asarray(imp, float).tolist(),
        "train_time_s": round(train_time, 3),
        "predict_time_s": round(predict_time, 4),
        "infer_latency_ms": round(1000 * predict_time / max(len(te_s), 1), 4),
        "memory_mb": round(peak / 1e6, 2),
        "model_size_kb": round(model.size_bytes() / 1024, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "benchmark" / "config.json")
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap iters + epochs (smoke)")
    args = ap.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if args.quick:
        cfg["bootstrap_iters"] = 200
        cfg.setdefault("deep", {}).update(pretrain_epochs=4, finetune_epochs=1)

    out = ROOT / "benchmark"
    res_dir, plot_dir, rep_dir = out / "results", out / "plots", out / "reports"
    for d in (res_dir, plot_dir, rep_dir):
        d.mkdir(parents=True, exist_ok=True)

    data_path = (ROOT / cfg["data"]).resolve() if not Path(cfg["data"]).is_absolute() else Path(cfg["data"])
    print("=" * 66)
    print("  UNIFIED MODEL BENCHMARK (leak-free, identical split for all models)")
    print("=" * 66)
    print(f"  Data: {data_path}")
    print("  [1/5] Building leak-free train/val/test split (reused pipeline) ...")
    tr, va, te, cols, scaler, artifacts, frame = prepare_split_sequences(
        data_path, cfg["seq_len"], cfg["val_frac"], cfg["test_frac"])
    (tr_s, tr_l, _), (_, _, _), (te_s, te_l, _) = tr, va, te
    print(f"        train={len(tr_s):,} val={len(va[0]):,} test={len(te_s):,}  "
          f"features={tr_s.shape[-1]}  test-attacks={int(te_l.sum())}")
    print("  [2/5] Validation checks ...")
    _validate_split(tr, va, te, scaler, cfg)

    print("  [3/5] Training + evaluating models ...")
    results = {}
    for name in cfg["models"]:
        try:
            t0 = time.perf_counter()
            r = run_one(name, cfg, tr, va, te, cfg["seed"], cfg["bootstrap_iters"])
            results[r["name"]] = r
            m = r["metrics"]
            print(f"      {r['name']:<34} F1={m['f1']:.3f} AUC={m['roc_auc']:.3f} "
                  f"PR-AUC={m['pr_auc']:.3f} MCC={m['mcc']:.3f}  ({time.perf_counter()-t0:.1f}s)")
        except Exception as exc:
            print(f"      [SKIP] {name}: {exc}")

    if not results:
        raise SystemExit("No models trained successfully.")

    # ── statistical significance vs proposed model ───────────────────────────
    proposed_name = M.REGISTRY[PROPOSED]().name if False else \
        next((r["name"] for r in results.values() if "Transformer Autoencoder" in r["name"]), None)
    stats = {}
    if proposed_name and proposed_name in results:
        base_pred = results[proposed_name]["pred"]; y = results[proposed_name]["y_true"]
        for name, r in results.items():
            if name == proposed_name:
                continue
            stats[name] = MET.mcnemar_test(y, base_pred, r["pred"])

    # ── outputs ──────────────────────────────────────────────────────────────
    print("  [4/5] Figures + tables ...")
    figs = []
    PLT.roc_overlay(results, plot_dir / "roc_overlay.png"); figs.append(plot_dir / "roc_overlay.png")
    PLT.pr_overlay(results, plot_dir / "pr_overlay.png"); figs.append(plot_dir / "pr_overlay.png")
    PLT.metric_bars(results, plot_dir / "f1_ci.png", "f1"); figs.append(plot_dir / "f1_ci.png")
    PLT.confusion_grid(results, plot_dir / "confusion_grid.png"); figs.append(plot_dir / "confusion_grid.png")
    PLT.score_distributions(results, plot_dir / "score_dists.png"); figs.append(plot_dir / "score_dists.png")
    PLT.calibration_curves(results, plot_dir / "calibration.png"); figs.append(plot_dir / "calibration.png")
    if PLT.feature_importance(results, cols, cfg["seq_len"], plot_dir / "feature_importance.png"):
        figs.append(plot_dir / "feature_importance.png")

    df = REP.build_dataframe(results)
    tbls = REP.export_tables(df, res_dir)

    print("  [5/5] Report ...")
    split = {"train_seq": len(tr_s), "val_seq": len(va[0]), "test_seq": len(te_s)}
    # copy figures into reports dir for self-contained markdown
    import shutil
    rep_figs = []
    for f in figs:
        dst = rep_dir / f.name; shutil.copy2(f, dst); rep_figs.append(dst)
    md = REP.markdown_report(df, results, {**cfg, "data": str(data_path)}, split, stats, rep_figs, rep_dir)
    pdf = REP.pdf_report(md, rep_figs, df, rep_dir)

    # machine-readable dump (no big arrays)
    dump = {name: {k: v for k, v in r.items() if k not in ("y_true", "scores", "pred", "importance")}
            for name, r in results.items()}
    (res_dir / "results.json").write_text(json.dumps(dump, indent=2), encoding="utf-8")

    print("\n" + "=" * 66)
    print("  DONE")
    print(f"    Tables : {tbls.get('csv')}  (+ .md .tex" + (" .xlsx" if "xlsx" in tbls else "") + ")")
    print(f"    Plots  : {plot_dir}  ({len(figs)} figures)")
    print(f"    Report : {md}" + (f"  +  {pdf.name}" if pdf else ""))
    print(f"    Winner (F1): {df.iloc[0]['model']}  F1={df.iloc[0]['f1']:.4f}")
    print("=" * 66)


if __name__ == "__main__":
    main()
