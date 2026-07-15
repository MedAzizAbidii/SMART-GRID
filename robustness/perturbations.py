"""
robustness/perturbations.py — one function per environmental condition.

All functions operate on the ALREADY-SCALED test sequences (n, seq_len, feat)
that the production model consumes, so results reflect what the deployed
detector actually sees. Each function changes exactly one condition and
returns a new array (never mutates the input) so experiments compose cleanly
and are independently reproducible from a fixed seed.
"""
from __future__ import annotations

import numpy as np

RAW_COLS = ["consommation_kw", "tension_v", "courant_a", "power_factor", "frequency_hz"]


def _idx(cols, names):
    return [cols.index(n) for n in names if n in cols]


# ── 1. Gaussian noise ─────────────────────────────────────────────────────────

def gaussian_noise(seqs, sigma, seed=0):
    rng = np.random.default_rng(seed)
    return (seqs + rng.normal(0, sigma, seqs.shape)).astype("float32")


# ── 2. Realistic sensor noise ─────────────────────────────────────────────────

def sensor_noise(seqs, cols, kind, magnitude, seed=0):
    """kind: 'offset' | 'drift' | 'quantization' | 'spike'"""
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    idx = _idx(cols, RAW_COLS)
    if kind == "offset":
        bias = rng.normal(0, magnitude, (len(seqs), 1, len(idx)))
        out[:, :, idx] += bias
    elif kind == "drift":
        ramp = np.linspace(0, magnitude, seqs.shape[1]).reshape(1, -1, 1)
        out[:, :, idx] += ramp
    elif kind == "quantization":
        step = max(magnitude, 1e-6)
        out[:, :, idx] = np.round(out[:, :, idx] / step) * step
    elif kind == "spike":
        mask = rng.random((len(seqs), seqs.shape[1])) < 0.02
        spike = rng.normal(0, magnitude * 5, seqs.shape[:2])
        for j in idx:
            out[:, :, j] += mask * spike
    return out.astype("float32")


# ── 3. Missing values + imputation ────────────────────────────────────────────

def missing_values(seqs, frac, impute="zero", seed=0):
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    mask = rng.random(seqs.shape) < frac
    if impute == "zero":
        out[mask] = 0.0
    elif impute == "mean":
        col_mean = seqs.mean(axis=(0, 1), keepdims=True)
        out = np.where(mask, np.broadcast_to(col_mean, seqs.shape), out)
    elif impute == "ffill":
        out2 = out.copy()
        for t in range(1, seqs.shape[1]):
            carry = mask[:, t, :]
            out2[:, t, :] = np.where(carry, out2[:, t - 1, :], out2[:, t, :])
        out = out2
    elif impute == "interpolate":
        # linear interpolation along the time axis per sequence/feature
        T = seqs.shape[1]
        for t in range(T):
            if t == 0 or t == T - 1:
                continue
        # simple two-sided average fallback for interior missing timesteps
        out2 = out.copy()
        for t in range(1, T - 1):
            carry = mask[:, t, :]
            avg = (out2[:, t - 1, :] + out2[:, t + 1, :]) / 2.0
            out2[:, t, :] = np.where(carry, avg, out2[:, t, :])
        out = out2
    return out.astype("float32")


# ── 4. Sensor failure (complete outage) ───────────────────────────────────────

def sensor_failure(seqs, cols, mode, seed=0):
    """mode: 'random_single' | 'critical' | 'multiple'"""
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    if mode == "critical":
        targets = _idx(cols, ["consommation_kw"])
    elif mode == "multiple":
        targets = _idx(cols, RAW_COLS)[:3]
    else:
        j = int(rng.integers(0, len(cols)))
        targets = [j]
    out[:, :, targets] = 0.0
    return out.astype("float32")


# ── 5. Feature corruption (per-feature sensitivity) ───────────────────────────

def corrupt_feature(seqs, feature_idx, seed=0):
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    out[:, :, feature_idx] = rng.normal(0, 1, seqs.shape[:2])
    return out.astype("float32")


# ── 6. Communication packet loss ──────────────────────────────────────────────

def packet_loss(seqs, frac, seed=0):
    """Whole timesteps ('packets') lost -> replaced by the previous timestep
    (typical real-world handling: hold last value) or zero at t=0."""
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    lost = rng.random(seqs.shape[:2]) < frac
    for t in range(seqs.shape[1]):
        if t == 0:
            out[:, 0, :] = np.where(lost[:, 0:1], 0.0, out[:, 0, :])
        else:
            out[:, t, :] = np.where(lost[:, t:t+1], out[:, t - 1, :], out[:, t, :])
    return out.astype("float32")


# ── 7. Timestamp jitter ───────────────────────────────────────────────────────

def timestamp_jitter(seqs, prob, seed=0):
    """Randomly swap each timestep with an adjacent one with probability
    `prob` — a bounded temporal perturbation, weaker than a full shuffle."""
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    T = seqs.shape[1]
    for i in range(len(out)):
        for t in range(T - 1):
            if rng.random() < prob:
                out[i, [t, t + 1]] = out[i, [t + 1, t]]
    return out


# ── 8. Data drift ──────────────────────────────────────────────────────────────

def data_drift(seqs, level, seed=0):
    """Global additive distribution shift of magnitude `level` (in std units,
    since features are pre-scaled) applied uniformly — simulates the input
    distribution drifting away from what the model was calibrated on."""
    rng = np.random.default_rng(seed)
    shift = rng.normal(level, 0.05, seqs.shape[-1])
    return (seqs + shift.reshape(1, 1, -1)).astype("float32")


# ── 9. Concept drift ───────────────────────────────────────────────────────────

def concept_drift(seqs, labels, level, seed=0):
    """Dampen attack signatures toward the normal mean by `level` (0=original
    attack, 1=fully disguised as normal) while keeping the ground-truth label
    'attack' — simulates an adversary who evolves attack characteristics
    while the semantic ground truth is unchanged."""
    rng = np.random.default_rng(seed)
    out = seqs.copy()
    normal_mean = seqs[labels == 0].mean(axis=0, keepdims=True) if (labels == 0).any() \
        else seqs.mean(axis=0, keepdims=True)
    atk = labels == 1
    out[atk] = out[atk] * (1 - level) + normal_mean * level
    return out.astype("float32")


# ── 10. Unknown / zero-day-proxy attacks ──────────────────────────────────────

def synth_unknown_attack(seqs, labels, cols, kind, seed=0):
    """Craft an attack SHAPE not present in the training attack vocabulary,
    applied to originally-NORMAL sequences, with a new label=1. Returns
    (new_seqs, new_labels) restricted to the synthesized subset only, so
    detection rate on these is a genuine unseen-pattern / zero-day proxy."""
    rng = np.random.default_rng(seed)
    normal = seqs[labels == 0].copy()
    n = min(300, len(normal))
    idx = rng.choice(len(normal), n, replace=False)
    S = normal[idx].copy()
    if kind == "slow_ramp":
        ramp = np.linspace(0, 2.0, S.shape[1]).reshape(1, -1, 1)
        S = S + ramp
    elif kind == "combined_inverse":
        v = cols.index("tension_v") if "tension_v" in cols else 0
        c = cols.index("courant_a") if "courant_a" in cols else 1
        S[:, :, v] += 1.5
        S[:, :, c] -= 1.5
    elif kind == "oscillation":
        t = np.arange(S.shape[1])
        wave = (0.8 * np.sin(2 * np.pi * t / 3)).reshape(1, -1, 1)
        S = S + wave
    return S.astype("float32"), np.ones(len(S), dtype=int)


# ── 11. Out-of-distribution samples ───────────────────────────────────────────

def ood_samples(seqs, level, seed=0):
    """Extreme-valued synthetic sequences (level x std beyond the training
    range) — physically implausible operating points, distinct from a
    'normal attack'. Returns synthetic sequences only."""
    rng = np.random.default_rng(seed)
    n = min(300, len(seqs))
    base = seqs[rng.choice(len(seqs), n, replace=False)].copy()
    extreme = base + rng.choice([-1, 1], base.shape) * level
    return extreme.astype("float32")
