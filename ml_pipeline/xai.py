from __future__ import annotations

import numpy as np


def attention_timestep_scores(attentions: list[np.ndarray]) -> np.ndarray:
    if not attentions:
        return np.array([])
    stacked = np.stack(attentions)
    return stacked.mean(axis=(0, 1, 2))


def feature_contributions(sequence: np.ndarray, reconstruction: np.ndarray, feature_names: list[str], top_k: int = 5) -> list[dict[str, float | str]]:
    errors = np.mean((sequence - reconstruction) ** 2, axis=0)
    top_indices = np.argsort(errors)[::-1][:top_k]
    return [{"feature": feature_names[index], "contribution": float(errors[index])} for index in top_indices]


def fuse_explanation(
    anomaly_score: float,
    threshold: float,
    attention_scores: np.ndarray,
    contributions: list[dict[str, float | str]],
) -> dict[str, object]:
    critical_step = int(np.argmax(attention_scores)) if attention_scores.size else None
    return {
        "is_anomaly": bool(anomaly_score >= threshold),
        "anomaly_score": float(anomaly_score),
        "threshold": float(threshold),
        "critical_timestep": critical_step,
        "top_causes": contributions,
        "message": "Attention indique où l'anomalie apparaît; contributions indiquent pourquoi.",
    }

