"""robustness/experiments/matrix.py — the robustness experiment matrix (1-11).
Experiment 12 (adversarial) and the reliability/stress phases are separate
modules (robustness/adversarial.py, robustness/reliability.py,
robustness/stress.py) since they don't fit the "perturb + evaluate on full
test set" shape.
"""
from __future__ import annotations

GAUSSIAN_SIGMAS = [0.01, 0.02, 0.05, 0.10, 0.20]
MISSING_FRACS = [0.01, 0.05, 0.10, 0.20, 0.40]
IMPUTATIONS = ["zero", "mean", "ffill", "interpolate"]
PACKET_LOSS_FRACS = [0.01, 0.05, 0.10, 0.20]
DRIFT_LEVELS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
CONCEPT_DRIFT_LEVELS = [0.0, 0.25, 0.5, 0.75, 1.0]
JITTER_PROBS = [0.05, 0.15, 0.30]
UNKNOWN_ATTACK_KINDS = ["slow_ramp", "combined_inverse", "oscillation"]
OOD_LEVELS = [2.0, 4.0, 8.0]


def all_experiment_ids():
    ids = ["E00_clean"]
    ids += [f"E01_gauss_{s}" for s in GAUSSIAN_SIGMAS]
    ids += [f"E02_sensor_{k}" for k in ("offset", "drift", "quantization", "spike")]
    ids += [f"E03_missing_{f}_{imp}" for f in MISSING_FRACS for imp in IMPUTATIONS]
    ids += [f"E04_failure_{m}" for m in ("random_single", "critical", "multiple")]
    ids += ["E05_feature_scan"]
    ids += [f"E06_packetloss_{f}" for f in PACKET_LOSS_FRACS]
    ids += [f"E07_jitter_{p}" for p in JITTER_PROBS]
    ids += [f"E08_drift_{d}" for d in DRIFT_LEVELS]
    ids += [f"E09_conceptdrift_{c}" for c in CONCEPT_DRIFT_LEVELS]
    ids += [f"E10_unknown_{k}" for k in UNKNOWN_ATTACK_KINDS]
    ids += [f"E11_ood_{lv}" for lv in OOD_LEVELS]
    return ids
