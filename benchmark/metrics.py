"""
benchmark/metrics.py — uniform metric computation for every model.

Every model in the benchmark produces a per-test-sequence anomaly score
(higher = more anomalous) plus a binary threshold chosen on validation. This
module turns (scores, labels, predictions) into the full metric set the audit /
IEEE reviewer expects, with bootstrap confidence intervals and paired
significance tests between models. sklearn is used for the well-tested metric
kernels; nothing here fits or sees training data.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    roc_auc_score, average_precision_score, matthews_corrcoef,
    balanced_accuracy_score, confusion_matrix,
)


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    """Return (tn, fp, fn, tp), robust to single-class edge cases."""
    labels = [0, 1]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=labels).ravel()
    return int(tn), int(fp), int(fn), int(tp)


def all_metrics(y_true: np.ndarray, scores: np.ndarray, y_pred: np.ndarray) -> dict:
    """Full metric dictionary for one model on one split."""
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion(y_true, y_pred)
    n = len(y_true)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0            # = detection rate = TPR
    specificity = tn / (tn + fp) if (tn + fp) else 0.0        # TNR
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / n if n else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    has_both = len(np.unique(y_true)) == 2
    auc = float(roc_auc_score(y_true, scores)) if has_both else 0.5
    pr_auc = float(average_precision_score(y_true, scores)) if has_both else float(y_true.mean())
    mcc = float(matthews_corrcoef(y_true, y_pred)) if has_both else 0.0
    bal_acc = float(balanced_accuracy_score(y_true, y_pred)) if has_both else accuracy

    return {
        "accuracy": accuracy, "precision": precision, "recall": recall,
        "f1": f1, "roc_auc": auc, "pr_auc": pr_auc, "mcc": mcc,
        "balanced_accuracy": bal_acc, "specificity": specificity,
        "fpr": fpr, "fnr": fnr, "detection_rate": recall,
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
    }


def f1_optimal_threshold(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Pick the score threshold maximising F1 — evaluated ON VALIDATION ONLY."""
    labels = np.asarray(labels).astype(int)
    if labels.sum() == 0:                      # no attacks in val -> conservative
        return float(scores.mean() + 3 * scores.std()), 0.0
    cand = np.unique(np.quantile(scores, np.linspace(0.50, 0.999, 300)))
    best_t, best_f = float(cand[len(cand) // 2]), -1.0
    for t in cand:
        pred = (scores >= t).astype(int)
        tp = int(((pred == 1) & (labels == 1)).sum())
        fp = int(((pred == 1) & (labels == 0)).sum())
        fn = int(((pred == 0) & (labels == 1)).sum())
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        if f > best_f:
            best_f, best_t = f, float(t)
    return best_t, best_f


def bootstrap_ci(y_true: np.ndarray, scores: np.ndarray, y_pred: np.ndarray,
                 metric: str = "f1", n_boot: int = 1000, seed: int = 0,
                 alpha: float = 0.05) -> tuple[float, float, float]:
    """95% bootstrap CI for a metric on the test set. Returns (point, lo, hi).
    n_boot=0 skips resampling and returns (point, point, point) — used when a
    fast point estimate is needed (e.g. a per-feature sensitivity scan)."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true).astype(int)
    n = len(y_true)
    point = all_metrics(y_true, scores, y_pred)[metric]
    if n_boot <= 0:
        return float(point), float(point), float(point)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        vals[b] = all_metrics(y_true[idx], scores[idx], y_pred[idx])[metric]
    lo = float(np.quantile(vals, alpha / 2))
    hi = float(np.quantile(vals, 1 - alpha / 2))
    return float(point), lo, hi


def mcnemar_test(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict:
    """Paired McNemar test comparing two models' correctness on the SAME test
    samples. Returns discordant counts, statistic, p-value, and effect size
    (odds ratio). This is the right test for comparing two classifiers on one
    held-out set (they see identical samples)."""
    from scipy.stats import chi2
    y_true = np.asarray(y_true).astype(int)
    a_correct = (np.asarray(pred_a).astype(int) == y_true)
    b_correct = (np.asarray(pred_b).astype(int) == y_true)
    b01 = int((a_correct & ~b_correct).sum())    # A right, B wrong
    b10 = int((~a_correct & b_correct).sum())    # A wrong, B right
    if b01 + b10 == 0:
        return {"b01": 0, "b10": 0, "statistic": 0.0, "p_value": 1.0, "odds_ratio": 1.0}
    # continuity-corrected McNemar
    stat = (abs(b01 - b10) - 1) ** 2 / (b01 + b10)
    p = float(chi2.sf(stat, df=1))
    odds = (b01 + 0.5) / (b10 + 0.5)
    return {"b01": b01, "b10": b10, "statistic": float(stat), "p_value": p, "odds_ratio": float(odds)}
