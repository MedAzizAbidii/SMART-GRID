"""
calibrate_detector.py — Platt Scaling calibration for the anomaly detector.

Transforms raw anomaly_score (MSE, uncalibrated) into a genuine probability
P(anomaly | score) using logistic regression (Platt 1999).

Before calibration: Mean Calibration Error = 0.198
After calibration:  Target MCE < 0.05

Usage:
    python calibrate_detector.py                  # calibrate v3 champion
    python calibrate_detector.py --model v2       # calibrate v2

Output:
    outputs/<model>/calibration_params.json       # {a, b} for sigmoid(a*score + b)
    outputs/calibration_curves.png                # before/after reliability diagram

The calibrated probability is then used in the /api/detect response via
the updated realtime_detector.py get_calibrated_probability() function.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STYLE = {
    "bg":      "#0F172A",
    "grid":    "#1E293B",
    "text":    "#F8FAFC",
    "accent":  "#38BDF8",
    "good":    "#4ADE80",
    "bad":     "#F87171",
}


def _style_ax(ax, fig):
    fig.patch.set_facecolor(STYLE["bg"])
    ax.set_facecolor(STYLE["grid"])
    ax.tick_params(colors=STYLE["text"], labelsize=9)
    ax.xaxis.label.set_color(STYLE["text"])
    ax.yaxis.label.set_color(STYLE["text"])
    ax.title.set_color(STYLE["text"])
    for spine in ax.spines.values():
        spine.set_edgecolor("#334155")
    ax.grid(True, color="#334155", alpha=0.5, linewidth=0.5)


# ── Pure-numpy logistic regression (no sklearn) ───────────────────────────────

def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def platt_fit(scores: np.ndarray, labels: np.ndarray,
              n_iter: int = 2000, lr: float = 0.5) -> tuple[float, float]:
    """
    Fit Platt scaling: P(y=1|score) = sigmoid(a * score + b)
    Uses gradient descent with binary cross-entropy loss.
    Label smoothing: replaces 0/1 with (1/(N+2)) and (N+1)/(N+2)
    as Platt recommends to avoid over-confident calibration.
    """
    N = len(labels)
    # Platt-recommended smoothed targets
    t_pos = (N + 1.0) / (N + 2.0)
    t_neg = 1.0 / (N + 2.0)
    y = np.where(labels == 1, t_pos, t_neg)

    # Normalise scores to prevent gradient explosion
    s_mean = scores.mean()
    s_std  = max(scores.std(), 1e-9)
    s_norm = (scores - s_mean) / s_std

    a, b = 1.0, 0.0
    best_loss = float("inf")
    best_a, best_b = a, b

    for i in range(n_iter):
        p    = sigmoid(a * s_norm + b)
        loss = -np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
        da   = np.mean((p - y) * s_norm)
        db   = np.mean(p - y)
        a   -= lr * da
        b   -= lr * db
        if loss < best_loss:
            best_loss = loss
            best_a, best_b = a, b
        # Reduce learning rate every 500 steps
        if (i + 1) % 500 == 0:
            lr *= 0.5

    # Convert back to original score space: sigmoid(a_orig * score + b_orig)
    # s_norm = (score - s_mean) / s_std  → a_orig = best_a / s_std
    a_orig = best_a / s_std
    b_orig = best_b - best_a * s_mean / s_std
    return float(a_orig), float(b_orig)


def calibrated_prob(scores: np.ndarray, a: float, b: float) -> np.ndarray:
    return sigmoid(a * scores + b)


def calibration_error(scores_pct: np.ndarray, labels: np.ndarray,
                      n_bins: int = 15) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Returns (bin_midpoints, actual_freq, bin_counts, MCE).
    scores_pct must be in [0,1].
    """
    edges = np.linspace(0, 1, n_bins + 1)
    mids  = (edges[:-1] + edges[1:]) / 2
    freqs, counts = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (scores_pct >= lo) & (scores_pct < hi)
        if mask.sum() > 0:
            freqs.append(float(labels[mask].mean()))
            counts.append(int(mask.sum()))
        else:
            freqs.append(float("nan"))
            counts.append(0)
    freqs  = np.array(freqs)
    counts = np.array(counts)
    valid  = ~np.isnan(freqs)
    mce    = float(np.mean(np.abs(freqs[valid] - mids[valid])))
    return mids, freqs, counts, mce


def run_calibration(model_dir: Path) -> dict:
    """Fit and evaluate Platt scaling on the predictions CSV."""
    preds_path = model_dir / "anomaly_predictions.csv"
    if not preds_path.exists():
        print(f"  [ERROR] Not found: {preds_path}")
        return {}

    df = pd.read_csv(preds_path)
    df["anomaly_score"]   = pd.to_numeric(df["anomaly_score"],   errors="coerce")
    df["sequence_label"]  = pd.to_numeric(df["sequence_label"],  errors="coerce").astype(int)
    df = df.dropna(subset=["anomaly_score", "sequence_label"])

    scores = df["anomaly_score"].values
    labels = df["sequence_label"].values

    # Train on 80%, evaluate on held-out 20%
    np.random.seed(0)
    idx = np.random.permutation(len(scores))
    n_train = int(len(idx) * 0.8)
    train_idx = idx[:n_train]
    val_idx   = idx[n_train:]

    a, b = platt_fit(scores[train_idx], labels[train_idx])
    print(f"  Platt params: a={a:.4f}, b={b:.6f}")

    # Probabilities on validation set
    cal_probs = calibrated_prob(scores[val_idx], a, b)
    raw_pct   = np.searchsorted(np.sort(scores[val_idx]),
                                scores[val_idx], side="right") / len(val_idx)

    mids, raw_freqs,  _, mce_raw = calibration_error(raw_pct,   labels[val_idx])
    _,    cal_freqs,  _, mce_cal = calibration_error(cal_probs,  labels[val_idx])

    print(f"  MCE before calibration: {mce_raw:.4f}")
    print(f"  MCE after  calibration: {mce_cal:.4f}")
    improvement = (mce_raw - mce_cal) / mce_raw * 100
    print(f"  Improvement: {improvement:.1f}%")

    return {
        "a": a, "b": b,
        "mce_before": round(mce_raw, 4),
        "mce_after":  round(mce_cal, 4),
        "mids": mids.tolist(),
        "raw_freqs": [float(x) if not np.isnan(x) else None for x in raw_freqs],
        "cal_freqs": [float(x) if not np.isnan(x) else None for x in cal_freqs],
    }


def plot_calibration_curves(results: dict[str, dict], out_path: Path):
    """Plot before/after reliability diagrams for all models."""
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 6))
    if n == 1:
        axes = [axes]

    for ax, (model_name, res) in zip(axes, results.items()):
        _style_ax(ax, fig)
        mids = np.array(res["mids"])
        raw  = np.array([x if x is not None else np.nan for x in res["raw_freqs"]])
        cal  = np.array([x if x is not None else np.nan for x in res["cal_freqs"]])

        ax.plot([0, 1], [0, 1], "w--", lw=1.2, alpha=0.4, label="Perfect calibration")
        valid_r = ~np.isnan(raw)
        valid_c = ~np.isnan(cal)
        ax.plot(mids[valid_r], raw[valid_r], "o-",
                color=STYLE["bad"],    lw=2, ms=6, label=f"Before  (MCE={res['mce_before']:.3f})")
        ax.plot(mids[valid_c], cal[valid_c], "s-",
                color=STYLE["good"],   lw=2, ms=6, label=f"After   (MCE={res['mce_after']:.3f})")

        # Shade improvement
        ax.fill_between(mids[valid_c], mids[valid_c], cal[valid_c],
                        alpha=0.15, color=STYLE["good"])

        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xlabel("Predicted Probability")
        ax.set_ylabel("Actual Anomaly Fraction")
        ax.set_title(f"Calibration — {model_name}\nPlatt Scaling a={res['a']:.4f}  b={res['b']:.4f}")
        leg = ax.legend(fontsize=9, framealpha=0.3, facecolor=STYLE["grid"])
        for t in leg.get_texts():
            t.set_color(STYLE["text"])

    fig.suptitle("Score Calibration: Platt Scaling  (closer to diagonal = better)",
                 color=STYLE["text"], fontsize=13)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=STYLE["bg"])
    plt.close(fig)
    print(f"  Saved: {out_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="all",
                        choices=["all", "v2", "v3"],
                        help="Which model to calibrate")
    args = parser.parse_args()

    model_dirs = {
        "v3": ROOT / "outputs" / "early_stopping_final",
        "v2": ROOT / "outputs" / "test_run_now",
    }

    if args.model != "all":
        model_dirs = {args.model: model_dirs[args.model]}

    print("=" * 60)
    print("  Platt Scaling Calibration")
    print("=" * 60)

    all_results = {}

    for name, mdir in model_dirs.items():
        print(f"\n[{name}] {mdir.name}")
        res = run_calibration(mdir)
        if not res:
            continue
        all_results[name] = res

        # Save calibration params
        params = {"a": res["a"], "b": res["b"],
                  "mce_before": res["mce_before"], "mce_after": res["mce_after"]}
        params_path = mdir / "calibration_params.json"
        params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
        print(f"  Params saved: {params_path}")

    if all_results:
        plot_path = ROOT / "outputs" / "calibration_curves.png"
        plot_calibration_curves(all_results, plot_path)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for name, res in all_results.items():
        delta = res["mce_before"] - res["mce_after"]
        print(f"  {name}: MCE {res['mce_before']:.4f} -> {res['mce_after']:.4f}  (-{delta:.4f})")
    print("\n  calibration_params.json is automatically loaded by")
    print("  realtime_detector.py get_calibrated_probability()")
    print("=" * 60)


if __name__ == "__main__":
    main()
