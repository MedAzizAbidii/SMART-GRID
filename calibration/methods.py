"""
calibration/methods.py — calibration methods + calibration-quality metrics.

Four methods compared, all FIT ON VALIDATION ONLY, evaluated on TEST:
  1. platt_raw  — reproduces the ORIGINAL (broken) approach: standard 2-param
                  logistic regression directly on raw reconstruction scores.
                  Kept only to reproduce and diagnose the historical failure.
  2. platt_log  — the FIX: logistic regression on log1p(score) instead of the
                  raw score, which is heavily right-skewed (see diagnose.py).
  3. isotonic   — non-parametric, monotonic regression (sklearn), robust to
                  any skew by construction.
  4. temperature— single-parameter scaling: standardize the score (z-score on
                  VAL statistics) then fit one scalar T minimising NLL of
                  sigmoid(z / T). The simplest possible baseline.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def _platt_gd(x: np.ndarray, labels: np.ndarray, n_iter=2000, lr=0.5):
    """Gradient-descent logistic regression on a 1-D input x -> sigmoid(a*x+b)."""
    N = len(labels)
    t_pos = (N + 1.0) / (N + 2.0)
    t_neg = 1.0 / (N + 2.0)
    y = np.where(labels == 1, t_pos, t_neg)
    x_mean, x_std = x.mean(), max(x.std(), 1e-9)
    xn = (x - x_mean) / x_std
    a, b = 1.0, 0.0
    best = (float("inf"), a, b)
    for i in range(n_iter):
        p = sigmoid(a * xn + b)
        loss = -np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
        da = np.mean((p - y) * xn); db = np.mean(p - y)
        a -= lr * da; b -= lr * db
        if loss < best[0]:
            best = (loss, a, b)
        if (i + 1) % 500 == 0:
            lr *= 0.5
    _, a, b = best
    # fold the normalisation back in: sigmoid(a*(x-mean)/std + b)
    a_orig = a / x_std
    b_orig = b - a * x_mean / x_std
    return a_orig, b_orig


class PlattRaw:
    """Standard 2-parameter Platt scaling directly on the raw reconstruction
    score. Historically this diverged badly on an old (leaky) pipeline/model
    (a≈300-700, MCE got worse — see diagnose.py); measured on THIS frozen
    model + leak-free split it does NOT reproduce that failure (a≈25) and is
    a legitimate candidate in the Part-A comparison, not assumed broken."""
    name = "Platt (raw score)"

    def fit(self, scores, labels):
        self.a, self.b = _platt_gd(scores, labels)
        return self

    def predict_proba(self, scores):
        return sigmoid(self.a * scores + self.b)


class PlattLog:
    """Platt on log(score+eps) — NOT log1p. Measured evidence (diagnose.py)
    shows every reconstruction score is < 1 (range ~2.5e-4 to 0.35), so
    log1p(x) = log(1+x) ≈ x in this range — it is numerically almost a no-op
    (VAL skew 19.94 -> 18.91, barely moved). A raw log(score+eps) is the
    correct transform for sub-1, multiplicative-scale data: it reduces skew
    to ~2.0 and yields a well-scaled Platt slope, fixing the average
    calibration error (ECE). It still has a measured weakness — see
    diagnose.py and compare.py: overconfidence in the sparse high-score tail
    — which is why Part A compares it against isotonic/temperature rather
    than assuming it is sufficient on its own."""
    name = "Platt (log(score+eps))"

    def fit(self, scores, labels, eps=1e-6):
        self.eps = eps
        self.a, self.b = _platt_gd(np.log(scores + eps), labels)
        return self

    def predict_proba(self, scores):
        return sigmoid(self.a * np.log(scores + self.eps) + self.b)


class Isotonic:
    name = "Isotonic regression"

    def fit(self, scores, labels):
        self.ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.ir.fit(scores, labels)
        return self

    def predict_proba(self, scores):
        return self.ir.predict(scores)


class Temperature:
    name = "Temperature scaling"

    def fit(self, scores, labels):
        self.mean, self.std = scores.mean(), max(scores.std(), 1e-9)
        z = (scores - self.mean) / self.std
        best_T, best_nll = 1.0, float("inf")
        for T in np.linspace(0.05, 5.0, 200):
            p = sigmoid(z / T)
            nll = -np.mean(labels * np.log(p + 1e-12) + (1 - labels) * np.log(1 - p + 1e-12))
            if nll < best_nll:
                best_nll, best_T = nll, T
        self.T = best_T
        return self

    def predict_proba(self, scores):
        z = (scores - self.mean) / self.std
        return sigmoid(z / self.T)


METHODS = {"platt_raw": PlattRaw, "platt_log": PlattLog,
           "isotonic": Isotonic, "temperature": Temperature}


# ── calibration-quality metrics ───────────────────────────────────────────────

def reliability_bins(probs, labels, n_bins=15):
    edges = np.linspace(0, 1, n_bins + 1)
    mids = (edges[:-1] + edges[1:]) / 2
    conf, acc, count = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (probs >= lo) & (probs < hi if hi < 1 else probs <= hi)
        if m.sum() > 0:
            conf.append(float(probs[m].mean())); acc.append(float(labels[m].mean())); count.append(int(m.sum()))
        else:
            conf.append(float("nan")); acc.append(float("nan")); count.append(0)
    return mids, np.array(conf), np.array(acc), np.array(count)


def expected_calibration_error(probs, labels, n_bins=15) -> float:
    mids, conf, acc, count = reliability_bins(probs, labels, n_bins)
    valid = count > 0
    n = count[valid].sum()
    if n == 0:
        return float("nan")
    return float(np.sum(count[valid] / n * np.abs(acc[valid] - conf[valid])))


def max_calibration_error(probs, labels, n_bins=15) -> float:
    mids, conf, acc, count = reliability_bins(probs, labels, n_bins)
    valid = count > 0
    if not valid.any():
        return float("nan")
    return float(np.max(np.abs(acc[valid] - conf[valid])))


def max_calibration_error_robust(probs, labels, n_bins=15, min_count=10) -> float:
    """MCE restricted to bins with >= min_count samples. Raw MCE is a single
    worst-bin statistic and is dominated by noise when a bin has only 1-3
    samples (a real, measured issue here: with only ~73 positive test
    sequences, several reliability bins are near-empty). This robust variant
    is used as the primary tie-break for method selection; raw MCE is still
    reported for completeness/comparability with the standard definition."""
    mids, conf, acc, count = reliability_bins(probs, labels, n_bins)
    valid = count >= min_count
    if not valid.any():
        return float("nan")
    return float(np.max(np.abs(acc[valid] - conf[valid])))


def brier_score(probs, labels) -> float:
    return float(np.mean((probs - labels) ** 2))
