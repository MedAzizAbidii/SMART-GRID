"""
ablation/report.py — tables, figures, contribution ranking, auto-conclusions.

Consumes ablation/results/*.json (written by runner.py) and produces a full,
IEEE-style ablation report. Contribution = baseline_F1 - variant_F1 (positive =
the removed/changed component helped). Auto-conclusions are generated ONLY from
measured deltas — no invented explanations.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RES, PLOTS, REPORTS = HERE / "results", HERE / "plots", HERE / "reports"
_PAL = ["#2C6FA6", "#C4892A", "#2E9E68", "#C1443A", "#7A5BA6", "#1F9E9E"]
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})

METRICS = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc",
           "mcc", "balanced_accuracy"]


def load_results() -> list[dict]:
    rows = []
    for f in sorted(RES.glob("*.json")):
        if f.name.endswith("_pred.json"):
            continue
        rows.append(json.loads(f.read_text()))
    return rows


def _df(results):
    recs = []
    for r in results:
        m = r["metrics"]
        recs.append({"id": r["id"], "group": r["group"], "component": r["component"],
                     "label": r["label"], **{k: m[k] for k in METRICS},
                     "f1_ci_lo": r["ci"]["f1"][1], "f1_ci_hi": r["ci"]["f1"][2],
                     "params": r["n_params"], "size_kb": r["model_size_kb"],
                     "train_s": r["train_time_s"], "latency_ms": r["infer_latency_ms"]})
    return pd.DataFrame(recs)


def export_tables(df, base_f1):
    RES.mkdir(exist_ok=True)
    d = df.copy()
    d["delta_f1"] = base_f1 - d["f1"]      # +ve => removing/changing hurt
    d = d.sort_values("f1", ascending=False)
    d.to_csv(RES / "ablation_comparison.csv", index=False)
    # markdown
    cols = ["label", "component", "f1", "roc_auc", "pr_auc", "mcc", "delta_f1", "params", "latency_ms"]
    md = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in d.iterrows():
        md.append("| " + " | ".join([str(r["label"]), str(r["component"])] +
                  [f"{r[c]:.4f}" if c in ("f1","roc_auc","pr_auc","mcc","delta_f1") else str(r[c])
                   for c in cols[2:]]) + " |")
    (RES / "ablation_comparison.md").write_text("\n".join(md), encoding="utf-8")
    # latex + excel
    d.round(4).to_latex(RES / "ablation_comparison.tex", index=False,
                        caption="Ablation study — held-out test (fixed budget).",
                        label="tab:ablation")
    try:
        d.to_excel(RES / "ablation_comparison.xlsx", index=False)
    except Exception:
        pass
    return d


# ── figures ───────────────────────────────────────────────────────────────────

def fig_contribution(df, base_f1, out):
    variants = df[df["id"] != "E01_baseline"].copy()
    variants["delta"] = base_f1 - variants["f1"]
    variants = variants.sort_values("delta")
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(variants) + 1.2))
    colors = ["#2E9E68" if v < 0 else "#C1443A" for v in variants["delta"]]
    ax.barh(range(len(variants)), variants["delta"], color=colors, alpha=0.85)
    ax.axvline(0, color="k", lw=1)
    ax.set_yticks(range(len(variants))); ax.set_yticklabels(variants["label"], fontsize=7.5)
    ax.set_xlabel("F1 drop vs baseline  (right = component HELPS, left = it HURTS)")
    ax.set_title("Component contribution (ΔF1 from baseline)")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_heatmap(df, out):
    variants = df.set_index("label")[METRICS]
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(variants) + 1.5))
    im = ax.imshow(variants.values, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(METRICS))); ax.set_xticklabels(METRICS, rotation=40, ha="right", fontsize=7.5)
    ax.set_yticks(range(len(variants))); ax.set_yticklabels(variants.index, fontsize=7)
    for i in range(variants.shape[0]):
        for j in range(variants.shape[1]):
            ax.text(j, i, f"{variants.values[i,j]:.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, fraction=0.025); ax.set_title("Ablation metric heatmap — test")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_sensitivity(results, out):
    """Parameter sensitivity: metric vs value for numeric hyperparameter sweeps."""
    groups = {}
    for r in results:
        ch = r["changes"]
        if len(ch) == 1:
            k, v = next(iter(ch.items()))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                groups.setdefault(k, []).append((v, r["metrics"]["f1"]))
    groups = {k: sorted(v) for k, v in groups.items() if len(v) >= 2}
    if not groups:
        return False
    n = len(groups); cols = min(3, n); rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, (k, vals) in zip(axes, groups.items()):
        xs, ys = zip(*vals)
        ax.plot(xs, ys, "o-", color=_PAL[0])
        ax.set_title(k, fontsize=9); ax.set_xlabel(k); ax.set_ylabel("F1")
    for ax in axes[n:]:
        ax.axis("off")
    fig.suptitle("Hyperparameter sensitivity (F1 vs value)", y=1.0)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return True


def fig_radar(df, out, top=6):
    keys = ["f1", "roc_auc", "pr_auc", "mcc", "recall", "precision"]
    sel = df.sort_values("f1", ascending=False).head(top)
    ang = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist(); ang += ang[:1]
    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw=dict(polar=True))
    for i, (_, r) in enumerate(sel.iterrows()):
        vals = [r[k] for k in keys]; vals += vals[:1]
        ax.plot(ang, vals, color=_PAL[i % len(_PAL)], lw=1.6, label=r["label"][:24])
        ax.fill(ang, vals, color=_PAL[i % len(_PAL)], alpha=0.06)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(keys, fontsize=8); ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=7)
    ax.set_title("Configuration comparison (radar)")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_train_time(df, out):
    d = df.sort_values("train_s")
    fig, ax = plt.subplots(figsize=(7, 0.3 * len(d) + 1.2))
    ax.barh(range(len(d)), d["train_s"], color=_PAL[4], alpha=0.85)
    ax.set_yticks(range(len(d))); ax.set_yticklabels(d["label"], fontsize=7)
    ax.set_xlabel("training time (s, fixed budget)"); ax.set_title("Training cost per configuration")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


# ── contribution ranking + auto conclusions ──────────────────────────────────

def contribution_ranking(results, base_f1):
    """Rank components by the LARGEST F1 change caused by ablating them."""
    by_comp = {}
    for r in results:
        if r["id"] == "E01_baseline":
            continue
        comp = r["component"]
        delta = base_f1 - r["metrics"]["f1"]      # +ve = removal hurt = component helps
        by_comp.setdefault(comp, []).append((r["label"], delta, r["ci"]["f1"]))
    rank = []
    for comp, entries in by_comp.items():
        worst = max(entries, key=lambda e: e[1])   # biggest drop when ablated
        rank.append({"component": comp, "max_delta_f1": worst[1],
                     "worst_variant": worst[0], "ci": worst[2]})
    rank.sort(key=lambda x: -x["max_delta_f1"])
    return rank


def auto_conclusions(rank, base_f1, results):
    L = []
    base_pct = f"{base_f1:.3f}"
    L.append(f"The full proposed configuration reached F1 = {base_pct} on the "
             "held-out test split under the fixed ablation budget. Measured "
             "component contributions (ΔF1 when ablated):")
    for r in rank:
        d = r["max_delta_f1"]
        if d > 0.01:
            verb = f"REDUCED F1 by {d:.3f}"
            keep = "necessary — keep"
        elif d < -0.01:
            verb = f"IMPROVED F1 by {abs(d):.3f} when changed"
            keep = "candidate to revisit"
        else:
            verb = f"changed F1 by only {d:+.3f}"
            keep = "not decisive at this budget"
        L.append(f"- **{r['component']}**: ablating it ({r['worst_variant']}) {verb} "
                 f"→ {keep}.")
    # single strongest driver
    if rank:
        top = rank[0]
        if top["max_delta_f1"] > 0.01:
            L.append(f"\nThe single most important component is **{top['component']}** "
                     f"(largest F1 loss, {top['max_delta_f1']:.3f}, when ablated as "
                     f"'{top['worst_variant']}').")
        else:
            L.append("\nNo single component dominates at this budget; the architecture "
                     "is robust to individual ablations, and gains are distributed.")
    return "\n".join(L)


def markdown_report(df, results, rank, base_f1, figs):
    REPORTS.mkdir(exist_ok=True, parents=True)
    import shutil
    rep_figs = []
    for f in figs:
        dst = REPORTS / f.name; shutil.copy2(f, dst); rep_figs.append(dst)
    L = []; A = L.append
    A("# Ablation & Contribution Study — Transformer Autoencoder\n")
    A(f"*Generated {datetime.now():%Y-%m-%d %H:%M} · leak-free protocol · "
      f"held-out test · fixed ablation budget*\n")
    A("## 1. Methodology\n")
    A("Every experiment changes **exactly one** component of the proposed model "
      "and is evaluated on the **same** leak-free train/val/test split, the same "
      "preprocessing, the same metrics, and the same fixed random seed as the "
      "Phase-1 benchmark. A deliberately small, fixed training budget is used so "
      "that **relative** effects (ΔF1) are comparable across experiments; absolute "
      "numbers are lower than a fully-trained model by design. Threshold-strategy "
      "and XAI experiments reuse the baseline's trained weights (no component of "
      "the model changes).\n")
    A("## 2. Full results (held-out test, sorted by F1)\n")
    cols = ["label", "component", "f1", "roc_auc", "pr_auc", "mcc", "params", "latency_ms"]
    A("| " + " | ".join(cols) + " |"); A("|" + "|".join(["---"] * len(cols)) + "|")
    for _, r in df.sort_values("f1", ascending=False).iterrows():
        A("| " + " | ".join([str(r["label"]), str(r["component"])] +
          [f"{r[c]:.4f}" if c in ("f1","roc_auc","pr_auc","mcc") else str(r[c]) for c in cols[2:]]) + " |")
    A("")
    A("## 3. Contribution ranking\n")
    A("| Rank | Component | Max ΔF1 when ablated | Worst variant | F1 95% CI |")
    A("|---|---|---|---|---|")
    for i, r in enumerate(rank, 1):
        A(f"| {i} | {r['component']} | {r['max_delta_f1']:+.4f} | {r['worst_variant']} | "
          f"[{r['ci'][1]:.3f}, {r['ci'][2]:.3f}] |")
    A("")
    A("## 4. Automatic conclusions (measured only)\n")
    A(auto_conclusions(rank, base_f1, results)); A("")
    A("## 5. Figures\n")
    for f in rep_figs:
        A(f"![{f.stem}]({f.name})")
    A("")
    A("## 6. Limitations\n")
    A("- Fixed reduced budget: absolute F1 is lower than a fully-trained model; "
      "only relative deltas are interpreted.\n"
      "- Single synthetic dataset: contribution magnitudes may differ on real data.\n"
      "- Supervised paradigms are excluded here (this study ablates the proposed "
      "unsupervised architecture only).\n")
    path = REPORTS / "ablation_report.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path, rep_figs


def pdf_report(df, rep_figs, rank):
    try:
        from matplotlib.backends.backend_pdf import PdfPages
    except Exception:
        return None
    pdf = REPORTS / "ablation_report.pdf"
    with PdfPages(pdf) as pp:
        fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis("off")
        ax.text(0.5, 0.93, "Ablation & Contribution Study", ha="center", fontsize=16, weight="bold")
        ax.text(0.5, 0.89, "Transformer Autoencoder · leak-free · held-out test", ha="center", fontsize=10, color="#555")
        rk = pd.DataFrame(rank)[["component", "max_delta_f1", "worst_variant"]].round(4)
        t = ax.table(cellText=rk.values, colLabels=["Component", "MaxΔF1", "Worst variant"],
                     loc="center", cellLoc="center")
        t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.4)
        pp.savefig(fig); plt.close(fig)
        for f in rep_figs:
            try:
                img = plt.imread(str(f)); fig, ax = plt.subplots(figsize=(11, 8.5))
                ax.axis("off"); ax.imshow(img); ax.set_title(f.stem, fontsize=10)
                pp.savefig(fig); plt.close(fig)
            except Exception:
                pass
    return pdf


def main():
    results = load_results()
    if not results:
        raise SystemExit("No ablation results found — run: python -m ablation.runner")
    base = next((r for r in results if r["id"] == "E01_baseline"), None)
    if base is None:
        raise SystemExit("Baseline (E01) missing.")
    base_f1 = base["metrics"]["f1"]
    df = _df(results)
    PLOTS.mkdir(exist_ok=True, parents=True)

    export_tables(df, base_f1)
    figs = []
    fig_contribution(df, base_f1, PLOTS / "contribution.png"); figs.append(PLOTS / "contribution.png")
    fig_heatmap(df, PLOTS / "heatmap.png"); figs.append(PLOTS / "heatmap.png")
    if fig_sensitivity(results, PLOTS / "sensitivity.png"):
        figs.append(PLOTS / "sensitivity.png")
    fig_radar(df, PLOTS / "radar.png"); figs.append(PLOTS / "radar.png")
    fig_train_time(df, PLOTS / "train_time.png"); figs.append(PLOTS / "train_time.png")

    rank = contribution_ranking(results, base_f1)
    md, rep_figs = markdown_report(df, results, rank, base_f1, figs)
    pdf = pdf_report(df, rep_figs, rank)

    print("=" * 60)
    print(f"  Ablation report: {md}" + (f"  +  {pdf.name}" if pdf else ""))
    print(f"  Tables: {RES}/ablation_comparison.(csv,md,tex,xlsx)")
    print(f"  Plots : {PLOTS}  ({len(figs)} figures)")
    print(f"  Baseline F1={base_f1:.4f}. Top component: {rank[0]['component']} "
          f"(dF1={rank[0]['max_delta_f1']:+.4f})")
    print("=" * 60)


if __name__ == "__main__":
    main()
