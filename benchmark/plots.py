"""benchmark/plots.py — publication-quality figures, saved automatically."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve

plt.rcParams.update({
    "figure.dpi": 140, "font.size": 10, "axes.grid": True,
    "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False,
})
_PAL = ["#2C6FA6", "#C4892A", "#2E9E68", "#C1443A", "#7A5BA6", "#4A4A4A", "#1F9E9E"]


def roc_overlay(results: dict, out: Path):
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    for i, (name, r) in enumerate(results.items()):
        fpr, tpr, _ = roc_curve(r["y_true"], r["scores"])
        ax.plot(fpr, tpr, color=_PAL[i % len(_PAL)], lw=1.8,
                label=f"{name} (AUC={r['metrics']['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC — held-out test"); ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def pr_overlay(results: dict, out: Path):
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    for i, (name, r) in enumerate(results.items()):
        prec, rec, _ = precision_recall_curve(r["y_true"], r["scores"])
        ax.plot(rec, prec, color=_PAL[i % len(_PAL)], lw=1.8,
                label=f"{name} (PR-AUC={r['metrics']['pr_auc']:.3f})")
    base = float(np.mean(next(iter(results.values()))["y_true"]))
    ax.axhline(base, color="k", ls="--", lw=1, alpha=0.4, label=f"baseline={base:.3f}")
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title("Precision–Recall — held-out test"); ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def metric_bars(results: dict, out: Path, metric="f1"):
    names = list(results.keys())
    vals = [results[n]["metrics"][metric] for n in names]
    ci = [results[n].get("ci", {}).get(metric) for n in names]
    order = np.argsort(vals)
    names = [names[i] for i in order]; vals = [vals[i] for i in order]; ci = [ci[i] for i in order]
    fig, ax = plt.subplots(figsize=(7, 0.5 * len(names) + 1.5))
    y = np.arange(len(names))
    err = None
    if all(c is not None for c in ci):
        err = np.array([[v - c[1] for v, c in zip(vals, ci)],
                        [c[2] - v for v, c in zip(vals, ci)]])
    ax.barh(y, vals, xerr=err, color=_PAL[0], alpha=0.85, capsize=3)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.3f}", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(names); ax.set_xlim(0, 1.05)
    ax.set_xlabel(metric.upper()); ax.set_title(f"{metric.upper()} with 95% bootstrap CI — test")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def confusion_grid(results: dict, out: Path):
    n = len(results); cols = min(4, n); rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 3 * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, (name, r) in zip(axes, results.items()):
        m = r["metrics"]
        mat = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
        ax.imshow(mat, cmap="Blues")
        for (i, j), v in np.ndenumerate(mat):
            ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=9,
                    color="white" if v > mat.max() / 2 else "black")
        ax.set_title(name, fontsize=8.5)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["N", "A"], fontsize=8)
        ax.set_yticks([0, 1]); ax.set_yticklabels(["N", "A"], fontsize=8)
    for ax in axes[n:]:
        ax.axis("off")
    fig.suptitle("Confusion matrices — held-out test", y=1.0)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def calibration_curves(results: dict, out: Path, bins=10):
    fig, ax = plt.subplots(figsize=(6, 5.4))
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4, label="perfect")
    edges = np.linspace(0, 1, bins + 1)
    for i, (name, r) in enumerate(results.items()):
        s = r["scores"].astype(float)
        rng = s.max() - s.min()
        p = (s - s.min()) / rng if rng > 0 else np.zeros_like(s)  # normalise score->[0,1]
        y = np.asarray(r["y_true"])
        mids, fracs = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (p >= lo) & (p < hi)
            if mask.sum() > 5:
                mids.append((lo + hi) / 2); fracs.append(float(y[mask].mean()))
        if mids:
            ax.plot(mids, fracs, "o-", color=_PAL[i % len(_PAL)], lw=1.4, ms=4, label=name)
    ax.set_xlabel("Normalised score (bin)"); ax.set_ylabel("Observed attack fraction")
    ax.set_title("Calibration — held-out test"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def score_distributions(results: dict, out: Path):
    n = len(results); cols = min(4, n); rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.4 * cols, 2.8 * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, (name, r) in zip(axes, results.items()):
        s = r["scores"]; y = np.asarray(r["y_true"])
        ax.hist(s[y == 0], bins=40, color="#2E9E68", alpha=0.6, label="normal", log=True)
        ax.hist(s[y == 1], bins=40, color="#C1443A", alpha=0.6, label="attack", log=True)
        ax.axvline(r["threshold"], color="#2C6FA6", ls="--", lw=1.3)
        ax.set_title(name, fontsize=8.5); ax.legend(fontsize=7)
    for ax in axes[n:]:
        ax.axis("off")
    fig.suptitle("Score distributions + threshold — test", y=1.0)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def feature_importance(results: dict, cols: list, seq_len: int, out: Path):
    imp_models = {n: r for n, r in results.items() if r.get("importance") is not None}
    if not imp_models:
        return False
    n = len(imp_models)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 5))
    axes = np.atleast_1d(axes).ravel()
    for ax, (name, r) in zip(axes, imp_models.items()):
        imp = np.asarray(r["importance"]).reshape(seq_len, -1).mean(axis=0)  # avg over time
        top = np.argsort(imp)[::-1][:12]
        ax.barh(range(len(top)), imp[top][::-1], color=_PAL[1])
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels([cols[i] for i in top][::-1], fontsize=7.5)
        ax.set_title(f"{name}\ntop features (time-averaged)", fontsize=9)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return True
