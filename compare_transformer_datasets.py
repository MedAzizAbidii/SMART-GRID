#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and compare Transformer Autoencoder on generated and Kaggle datasets.")
    parser.add_argument("--generated-data", default="donnees_smart_meters.csv")
    parser.add_argument("--kaggle-data", default="data_generation/assetes/smart_grid_stability_augmented.csv")
    parser.add_argument("--output-root", default="outputs/dataset_comparison")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--pretrain-epochs", type=int, default=3)
    parser.add_argument("--sequence-length", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", default="cpu")
    return parser


def run_training(name: str, data_path: Path, output_dir: Path, args: argparse.Namespace, label_column: str | None = None) -> dict[str, object]:
    command = [
        sys.executable,
        "run_transformer_autoencoder.py",
        "--data",
        str(data_path),
        "--output-dir",
        str(output_dir),
        "--epochs",
        str(args.epochs),
        "--pretrain-epochs",
        str(args.pretrain_epochs),
        "--sequence-length",
        str(args.sequence_length),
        "--batch-size",
        str(args.batch_size),
        "--device",
        args.device,
    ]
    if label_column:
        command.extend(["--label-column", label_column])

    print(f"\n=== Training {name} ===")
    subprocess.run(command, check=True)
    report_path = output_dir / "training_report.json"
    return json.loads(report_path.read_text(encoding="utf-8"))


def write_comparison(output_root: Path, reports: dict[str, dict[str, object]]) -> None:
    rows = []
    for dataset_name, report in reports.items():
        metrics = report["metrics"]
        rows.append(
            {
                "dataset": dataset_name,
                "rows": report["rows"],
                "sequences": report["sequences"],
                "normal_sequences": report["normal_sequences"],
                "alert_sequences": report["alert_sequences"],
                "threshold": report["threshold"],
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1_score": metrics["f1_score"],
                "roc_auc": metrics["roc_auc"],
            }
        )

    csv_path = output_root / "comparison_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Transformer Autoencoder Dataset Comparison",
        "",
        "| Dataset | Rows | Sequences | Accuracy | Precision | Recall | F1 | ROC-AUC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['dataset']} | {row['rows']} | {row['sequences']} | "
            f"{row['accuracy']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1_score']:.4f} | {row['roc_auc']:.4f} |"
        )

    best_auc = max(rows, key=lambda item: float(item["roc_auc"]))
    best_f1 = max(rows, key=lambda item: float(item["f1_score"]))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Best ROC-AUC: `{best_auc['dataset']}` with `{best_auc['roc_auc']:.4f}`.",
            f"- Best F1-score: `{best_f1['dataset']}` with `{best_f1['f1_score']:.4f}`.",
            "- Generated smart-meter data tests the project simulator behavior.",
            "- Kaggle stability data tests generalization on an external public smart-grid stability dataset.",
            "",
            "## Output folders",
            "",
            "- `outputs/dataset_comparison/generated/`",
            "- `outputs/dataset_comparison/kaggle/`",
        ]
    )
    (output_root / "comparison_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    reports = {
        "generated_smart_meters": run_training(
            "generated_smart_meters",
            Path(args.generated_data),
            output_root / "generated",
            args,
        ),
        "kaggle_stability": run_training(
            "kaggle_stability",
            Path(args.kaggle_data),
            output_root / "kaggle",
            args,
            label_column="stabf",
        ),
    }
    write_comparison(output_root, reports)
    print(f"\nSaved comparison: {output_root / 'comparison_report.md'}")
    print(f"Saved metrics CSV: {output_root / 'comparison_metrics.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

