#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import auc, f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score


FEATURE_COLUMNS = [
    "consommation_kw",
    "tension_v",
    "courant_a",
    "consommation_kw_diff",
    "consommation_kw_rolling_mean_3",
    "consommation_kw_rolling_std_3",
    "tension_v_diff",
    "tension_v_rolling_mean_3",
    "tension_v_rolling_std_3",
    "courant_a_diff",
    "courant_a_rolling_mean_3",
    "courant_a_rolling_std_3",
    "voltage_deviation_230",
    "current_voltage_ratio",
    "zone_consumption_mean",
    "meter_vs_zone_consumption",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze missed anomalies and improve Transformer AE thresholds.")
    parser.add_argument("--predictions", default="outputs/enhanced_generated_model/anomaly_predictions.csv")
    parser.add_argument("--output-dir", default="outputs/model_improvement_analysis")
    parser.add_argument("--min-precision", type=float, default=0.95)
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    return parser


def load_predictions(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    label_source = "sequence_label" if "sequence_label" in frame.columns else "is_alert"
    frame["y_true"] = frame[label_source].astype(int)
    frame["y_pred"] = (frame["model_prediction"].astype(str).str.upper() == "ANOMALY").astype(int)
    if "anomalies" in frame.columns:
        frame["anomaly_type"] = frame["anomalies"].fillna("").replace("", "normal")
    else:
        frame["anomaly_type"] = np.where(frame["y_true"].eq(1), "anomaly", "normal")
    return frame


def safe_metric_summary(y_true: np.ndarray, y_pred: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    summary = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    try:
        summary["roc_auc"] = float(roc_auc_score(y_true, scores))
    except ValueError:
        summary["roc_auc"] = 0.0
    return summary


def false_negative_analysis(frame: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    false_negatives = frame[(frame["y_true"] == 1) & (frame["y_pred"] == 0)]
    true_positives = frame[(frame["y_true"] == 1) & (frame["y_pred"] == 1)]
    false_negatives.to_csv(output_dir / "false_negatives.csv", index=False)

    by_meter = false_negatives["meter_id"].value_counts().head(15)
    by_hour = false_negatives["hour"].value_counts().sort_index()
    by_type = false_negatives["anomaly_type"].value_counts().head(15)

    by_meter.to_csv(output_dir / "false_negatives_by_meter.csv")
    by_hour.to_csv(output_dir / "false_negatives_by_hour.csv")
    by_type.to_csv(output_dir / "false_negatives_by_type.csv")

    plt.figure(figsize=(8, 5))
    plt.hist(true_positives["anomaly_score"], bins=50, alpha=0.7, label="True positives", color="#2ca02c")
    plt.hist(false_negatives["anomaly_score"], bins=50, alpha=0.7, label="False negatives", color="#d62728")
    plt.title("Missed Anomalies vs Detected Anomalies")
    plt.xlabel("Transformer reconstruction error")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "false_negative_score_distribution.png", dpi=160)
    plt.close()

    plt.figure(figsize=(9, 5))
    by_meter.sort_values().plot(kind="barh", color="#d62728")
    plt.title("Top Meters with Missed Anomalies")
    plt.xlabel("False negative count")
    plt.tight_layout()
    plt.savefig(output_dir / "false_negatives_by_meter.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 4))
    by_hour.plot(kind="bar", color="#9467bd")
    plt.title("Missed Anomalies by Hour")
    plt.xlabel("Hour")
    plt.ylabel("False negative count")
    plt.tight_layout()
    plt.savefig(output_dir / "false_negatives_by_hour.png", dpi=160)
    plt.close()

    return {
        "false_negative_count": int(len(false_negatives)),
        "top_false_negative_meters": by_meter.to_dict(),
        "top_false_negative_hours": by_hour.to_dict(),
        "top_false_negative_types": by_type.to_dict(),
    }


def threshold_optimization(frame: pd.DataFrame, output_dir: Path, min_precision: float) -> dict[str, object]:
    y_true = frame["y_true"].to_numpy()
    scores = frame["anomaly_score"].to_numpy()
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    pr_auc = float(auc(recall, precision))

    rows = []
    sweep_thresholds = np.unique(np.quantile(scores, np.linspace(0.001, 0.999, 250)))
    for threshold in sweep_thresholds:
        predictions = (scores >= threshold).astype(int)
        metric = safe_metric_summary(y_true, predictions, scores)
        rows.append({"threshold": float(threshold), **metric})
    threshold_frame = pd.DataFrame(rows)
    threshold_frame.to_csv(output_dir / "threshold_sweep.csv", index=False)

    best_f1_row = threshold_frame.iloc[threshold_frame["f1_score"].idxmax()]
    precision_guard = threshold_frame[threshold_frame["precision"] >= min_precision]
    best_recall_row = precision_guard.loc[precision_guard["recall"].idxmax()] if not precision_guard.empty else best_f1_row

    plt.figure(figsize=(7, 5))
    plt.plot(recall, precision)
    plt.title(f"Precision-Recall Curve (AUC={pr_auc:.4f})")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.tight_layout()
    plt.savefig(output_dir / "precision_recall_curve.png", dpi=160)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(threshold_frame["threshold"], threshold_frame["precision"], label="Precision")
    plt.plot(threshold_frame["threshold"], threshold_frame["recall"], label="Recall")
    plt.plot(threshold_frame["threshold"], threshold_frame["f1_score"], label="F1-score")
    plt.axvline(float(best_f1_row["threshold"]), color="black", linestyle="--", label="Best F1 threshold")
    plt.title("Metrics vs Threshold")
    plt.xlabel("Threshold")
    plt.ylabel("Metric")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "threshold_metrics.png", dpi=160)
    plt.close()

    return {
        "pr_auc": pr_auc,
        "best_f1_threshold": float(best_f1_row["threshold"]),
        "best_f1_metrics": best_f1_row.to_dict(),
        "best_recall_threshold_at_min_precision": float(best_recall_row["threshold"]),
        "best_recall_at_min_precision_metrics": best_recall_row.to_dict(),
    }


def per_meter_thresholds(frame: pd.DataFrame, output_dir: Path, min_precision: float) -> dict[str, object]:
    thresholds = {}
    predictions = np.zeros(len(frame), dtype=int)
    global_threshold = float(frame["dynamic_threshold"].iloc[0])

    for meter_id, group in frame.groupby("meter_id"):
        if group["y_true"].nunique() < 2 or len(group) < 20:
            threshold = global_threshold
        else:
            candidate_rows = []
            for threshold in np.quantile(group["anomaly_score"], np.linspace(0.50, 0.99, 60)):
                pred = (group["anomaly_score"].to_numpy() >= threshold).astype(int)
                candidate_rows.append(
                    {
                        "threshold": float(threshold),
                        **safe_metric_summary(group["y_true"].to_numpy(), pred, group["anomaly_score"].to_numpy()),
                    }
                )
            candidates = pd.DataFrame(candidate_rows)
            guarded = candidates[candidates["precision"] >= min_precision]
            selected = guarded.loc[guarded["recall"].idxmax()] if not guarded.empty else candidates.loc[candidates["f1_score"].idxmax()]
            threshold = float(selected["threshold"])
        thresholds[meter_id] = threshold
        predictions[group.index.to_numpy()] = (group["anomaly_score"].to_numpy() >= threshold).astype(int)

    threshold_table = pd.DataFrame({"meter_id": list(thresholds), "adaptive_threshold": list(thresholds.values())})
    threshold_table.to_csv(output_dir / "per_meter_thresholds.csv", index=False)
    metrics = safe_metric_summary(frame["y_true"].to_numpy(), predictions, frame["anomaly_score"].to_numpy())

    plt.figure(figsize=(9, 5))
    plt.hist(threshold_table["adaptive_threshold"], bins=30, color="#1f77b4")
    plt.title("Per-Meter Adaptive Threshold Distribution")
    plt.xlabel("Threshold")
    plt.ylabel("Meter count")
    plt.tight_layout()
    plt.savefig(output_dir / "per_meter_threshold_distribution.png", dpi=160)
    plt.close()

    return {"metrics": metrics, "threshold_count": int(len(threshold_table))}


def isolation_forest_ensemble(frame: pd.DataFrame, output_dir: Path, min_precision: float) -> dict[str, object]:
    available_features = [column for column in FEATURE_COLUMNS if column in frame.columns]
    features = frame[available_features].fillna(0.0).to_numpy()
    normal_features = frame.loc[frame["y_true"] == 0, available_features].fillna(0.0).to_numpy()

    contamination = max(0.01, min(0.20, float(frame["y_true"].mean())))
    forest = IsolationForest(n_estimators=60, contamination=contamination, random_state=42, n_jobs=-1)
    forest.fit(normal_features)
    forest_scores = -forest.decision_function(features)
    transformer_scores = frame["anomaly_score"].to_numpy()
    normalized_transformer = (transformer_scores - transformer_scores.min()) / (np.ptp(transformer_scores) + 1e-12)
    normalized_forest = (forest_scores - forest_scores.min()) / (np.ptp(forest_scores) + 1e-12)
    ensemble_score = 0.70 * normalized_transformer + 0.30 * normalized_forest

    rows = []
    for threshold in np.quantile(ensemble_score, np.linspace(0.50, 0.995, 60)):
        pred = (ensemble_score >= threshold).astype(int)
        rows.append({"threshold": float(threshold), **safe_metric_summary(frame["y_true"].to_numpy(), pred, ensemble_score)})
    sweep = pd.DataFrame(rows)
    sweep.to_csv(output_dir / "isolation_forest_ensemble_threshold_sweep.csv", index=False)
    guarded = sweep[sweep["precision"] >= min_precision]
    selected = guarded.loc[guarded["recall"].idxmax()] if not guarded.empty else sweep.loc[sweep["f1_score"].idxmax()]
    predictions = (ensemble_score >= float(selected["threshold"])).astype(int)
    metrics = safe_metric_summary(frame["y_true"].to_numpy(), predictions, ensemble_score)

    ensemble_output = frame[["timestamp", "meter_id", "y_true", "anomaly_score"]].copy()
    ensemble_output["isolation_forest_score"] = forest_scores
    ensemble_output["ensemble_score"] = ensemble_score
    ensemble_output["ensemble_prediction"] = predictions
    ensemble_output.to_csv(output_dir / "isolation_forest_ensemble_predictions.csv", index=False)

    plt.figure(figsize=(8, 5))
    plt.hist(ensemble_score[frame["y_true"].to_numpy() == 0], bins=50, alpha=0.7, label="Normal")
    plt.hist(ensemble_score[frame["y_true"].to_numpy() == 1], bins=50, alpha=0.7, label="Anomaly")
    plt.axvline(float(selected["threshold"]), color="black", linestyle="--", label="Selected threshold")
    plt.title("Transformer + Isolation Forest Ensemble Scores")
    plt.xlabel("Ensemble anomaly score")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "ensemble_score_distribution.png", dpi=160)
    plt.close()

    return {"metrics": metrics, "selected_threshold": float(selected["threshold"]), "features_used": available_features}


def temporal_context_thresholds(frame: pd.DataFrame, output_dir: Path, min_precision: float) -> dict[str, object]:
    predictions = np.zeros(len(frame), dtype=int)
    thresholds = []
    for hour, group in frame.groupby("hour"):
        if group["y_true"].nunique() < 2 or len(group) < 20:
            threshold = float(frame["dynamic_threshold"].iloc[0])
        else:
            candidates = []
            for threshold in np.quantile(group["anomaly_score"], np.linspace(0.50, 0.99, 60)):
                pred = (group["anomaly_score"].to_numpy() >= threshold).astype(int)
                candidates.append({"threshold": float(threshold), **safe_metric_summary(group["y_true"].to_numpy(), pred, group["anomaly_score"].to_numpy())})
            candidate_frame = pd.DataFrame(candidates)
            guarded = candidate_frame[candidate_frame["precision"] >= min_precision]
            selected = guarded.loc[guarded["recall"].idxmax()] if not guarded.empty else candidate_frame.loc[candidate_frame["f1_score"].idxmax()]
            threshold = float(selected["threshold"])
        thresholds.append({"hour": int(hour), "threshold": threshold})
        predictions[group.index.to_numpy()] = (group["anomaly_score"].to_numpy() >= threshold).astype(int)

    pd.DataFrame(thresholds).to_csv(output_dir / "hourly_context_thresholds.csv", index=False)
    return {"metrics": safe_metric_summary(frame["y_true"].to_numpy(), predictions, frame["anomaly_score"].to_numpy())}


def bootstrap_intervals(frame: pd.DataFrame, output_dir: Path, samples: int) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(42)
    y_true = frame["y_true"].to_numpy()
    y_pred = frame["y_pred"].to_numpy()
    scores = frame["anomaly_score"].to_numpy()
    metric_samples = {"precision": [], "recall": [], "f1_score": [], "roc_auc": []}
    for _ in range(samples):
        indices = rng.integers(0, len(frame), len(frame))
        if len(np.unique(y_true[indices])) < 2:
            continue
        metrics = safe_metric_summary(y_true[indices], y_pred[indices], scores[indices])
        for key in metric_samples:
            metric_samples[key].append(metrics[key])

    intervals = {}
    for key, values in metric_samples.items():
        intervals[key] = {
            "mean": float(np.mean(values)),
            "ci_95_low": float(np.percentile(values, 2.5)),
            "ci_95_high": float(np.percentile(values, 97.5)),
        }
    Path(output_dir / "bootstrap_confidence_intervals.json").write_text(json.dumps(intervals, indent=2), encoding="utf-8")
    return intervals


def per_anomaly_type_breakdown(frame: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    anomaly_frame = frame[frame["y_true"] == 1]
    rows = []
    for anomaly_type, group in anomaly_frame.groupby("anomaly_type"):
        rows.append(
            {
                "anomaly_type": anomaly_type,
                "count": int(len(group)),
                "recall": float((group["y_pred"] == 1).mean()),
                "missed": int((group["y_pred"] == 0).sum()),
            }
        )
    result = pd.DataFrame(rows).sort_values("missed", ascending=False)
    result.to_csv(output_dir / "per_anomaly_type_recall.csv", index=False)
    return {"types": result.to_dict(orient="records")}


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = load_predictions(Path(args.predictions))

    current_metrics = safe_metric_summary(frame["y_true"].to_numpy(), frame["y_pred"].to_numpy(), frame["anomaly_score"].to_numpy())
    report = {
        "current_metrics": current_metrics,
        "false_negative_analysis": false_negative_analysis(frame, output_dir),
        "threshold_optimization": threshold_optimization(frame, output_dir, args.min_precision),
        "per_meter_thresholds": per_meter_thresholds(frame, output_dir, args.min_precision),
        "isolation_forest_ensemble": isolation_forest_ensemble(frame, output_dir, args.min_precision),
        "temporal_context_thresholds": temporal_context_thresholds(frame, output_dir, args.min_precision),
        "bootstrap_confidence_intervals": bootstrap_intervals(frame, output_dir, args.bootstrap_samples),
        "per_anomaly_type_breakdown": per_anomaly_type_breakdown(frame, output_dir),
    }
    (output_dir / "model_improvement_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    markdown = [
        "# Model Improvement Analysis",
        "",
        "## Current Transformer Autoencoder",
        "",
        f"- Precision: `{current_metrics['precision']:.4f}`",
        f"- Recall: `{current_metrics['recall']:.4f}`",
        f"- F1-score: `{current_metrics['f1_score']:.4f}`",
        f"- ROC-AUC: `{current_metrics['roc_auc']:.4f}`",
        "",
        "## Recommended Thresholds",
        "",
        f"- Best F1 threshold: `{report['threshold_optimization']['best_f1_threshold']:.8f}`",
        f"- Best recall threshold with precision guard: `{report['threshold_optimization']['best_recall_threshold_at_min_precision']:.8f}`",
        "",
        "## Alternative Strategies",
        "",
        f"- Per-meter thresholds: `{report['per_meter_thresholds']['metrics']}`",
        f"- Isolation Forest ensemble: `{report['isolation_forest_ensemble']['metrics']}`",
        f"- Hourly context thresholds: `{report['temporal_context_thresholds']['metrics']}`",
        "",
        "## Key Plots",
        "",
        "- `false_negative_score_distribution.png`",
        "- `false_negatives_by_meter.png`",
        "- `false_negatives_by_hour.png`",
        "- `precision_recall_curve.png`",
        "- `threshold_metrics.png`",
        "- `per_meter_threshold_distribution.png`",
        "- `ensemble_score_distribution.png`",
    ]
    (output_dir / "model_improvement_report.md").write_text("\n".join(markdown), encoding="utf-8")
    print(f"Saved improvement analysis to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
