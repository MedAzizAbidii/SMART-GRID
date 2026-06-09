#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score, roc_curve
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ml_pipeline.preprocessing import prepare_sequences
from ml_pipeline.transformer_autoencoder import TransformerAutoencoder, reconstruction_error
from ml_pipeline.xai import attention_timestep_scores, feature_contributions, fuse_explanation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pretrain and train a Transformer Autoencoder for smart-grid anomalies.")
    parser.add_argument("--data", default="donnees_smart_meters.csv", help="Smart-meter CSV file.")
    parser.add_argument("--label-column", default=None, help="Optional label column, e.g. stabf for Kaggle stability data.")
    parser.add_argument("--output-dir", default="outputs/transformer_autoencoder", help="Directory for models and reports.")
    parser.add_argument("--sequence-length", type=int, default=8, help="Temporal events per sequence.")
    parser.add_argument("--epochs", type=int, default=15, help="Fine-tuning epochs.")
    parser.add_argument("--pretrain-epochs", type=int, default=8, help="Self-supervised pretraining epochs.")
    parser.add_argument("--batch-size", type=int, default=64, help="Training batch size.")
    parser.add_argument("--model-dim", type=int, default=64, help="Transformer embedding dimension.")
    parser.add_argument("--heads", type=int, default=4, help="Multi-head attention heads.")
    parser.add_argument("--layers", type=int, default=2, help="Transformer encoder layers.")
    parser.add_argument("--threshold-percentile", type=float, default=95.0, help="Dynamic anomaly threshold percentile.")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"], help="Training device.")
    parser.add_argument(
        "--train-on-all",
        action="store_true",
        help="Fine-tune on all sequences. Default is normal-only training, recommended for autoencoder anomaly detection.",
    )
    return parser


def choose_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def train_epoch(model: TransformerAutoencoder, loader: DataLoader, optimizer: torch.optim.Optimizer, device: torch.device) -> float:
    model.train()
    criterion = nn.MSELoss()
    losses = []
    for (batch,) in loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        reconstruction, _ = model(batch)
        loss = criterion(reconstruction, batch)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))
    return float(np.mean(losses))


def evaluate_scores(model: TransformerAutoencoder, sequences: np.ndarray, device: torch.device, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    scores: list[np.ndarray] = []
    reconstructions: list[np.ndarray] = []
    loader = DataLoader(TensorDataset(torch.tensor(sequences)), batch_size=batch_size)
    with torch.no_grad():
        for (batch,) in loader:
            batch = batch.to(device)
            reconstruction, _ = model(batch)
            scores.append(reconstruction_error(batch, reconstruction).cpu().numpy())
            reconstructions.append(reconstruction.cpu().numpy())
    return np.concatenate(scores), np.concatenate(reconstructions)


def safe_metrics(labels: np.ndarray, predictions: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1_score": float(f1_score(labels, predictions, zero_division=0)),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(labels, scores))
    except ValueError:
        metrics["roc_auc"] = 0.0
    return metrics


def save_plots(
    output_dir: Path,
    history: dict[str, list[float]],
    labels: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    attention_scores: np.ndarray,
    contributions: list[dict[str, float | str]],
) -> None:
    import matplotlib.pyplot as plt

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    if history["pretrain_loss"]:
        plt.plot(range(1, len(history["pretrain_loss"]) + 1), history["pretrain_loss"], marker="o", label="Pretraining")
    if history["finetune_loss"]:
        offset = len(history["pretrain_loss"])
        epochs = range(offset + 1, offset + len(history["finetune_loss"]) + 1)
        plt.plot(list(epochs), history["finetune_loss"], marker="o", label="Fine-tuning")
    plt.title("Transformer Autoencoder Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("MSE reconstruction loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "training_loss.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.hist(scores[labels == 0], bins=40, label="Normal", color="#2ca02c", alpha=0.65)
    plt.hist(scores[labels == 1], bins=40, label="Anomaly", color="#d62728", alpha=0.65)
    plt.axvline(threshold, color="black", linestyle="--", label=f"Threshold={threshold:.4f}")
    plt.title("Anomaly Score Distribution")
    plt.xlabel("Reconstruction error")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "anomaly_score_distribution.png", dpi=160)
    plt.close()

    matrix = confusion_matrix(labels, predictions)
    plt.figure(figsize=(5, 4))
    plt.imshow(matrix, cmap="Blues")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            plt.text(column, row, str(matrix[row, column]), ha="center", va="center", color="black")
    plt.xticks([0, 1], ["Normal", "Anomaly"])
    plt.yticks([0, 1], ["Normal", "Anomaly"])
    plt.colorbar()
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(plots_dir / "confusion_matrix.png", dpi=160)
    plt.close()

    if len(np.unique(labels)) > 1:
        false_positive_rate, true_positive_rate, _ = roc_curve(labels, scores)
        plt.figure(figsize=(6, 5))
        plt.plot(false_positive_rate, true_positive_rate, label="Transformer AE")
        plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random")
        plt.title("ROC Curve")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.legend()
        plt.tight_layout()
        plt.savefig(plots_dir / "roc_curve.png", dpi=160)
        plt.close()

    if attention_scores.size:
        plt.figure(figsize=(8, 3))
        plt.imshow(attention_scores.reshape(1, -1), cmap="magma", aspect="auto")
        plt.yticks([0], ["attention"])
        plt.colorbar()
        plt.title("Attention Heatmap by Timestep")
        plt.xlabel("Timestep inside sequence")
        plt.tight_layout()
        plt.savefig(plots_dir / "attention_heatmap.png", dpi=160)
        plt.close()

    if contributions:
        names = [str(item["feature"]) for item in contributions][::-1]
        values = [float(item["contribution"]) for item in contributions][::-1]
        plt.figure(figsize=(8, 5))
        plt.barh(names, values, color="#ff7f0e")
        plt.title("Top XAI Feature Contributions")
        plt.xlabel("Mean reconstruction error contribution")
        plt.tight_layout()
        plt.savefig(plots_dir / "xai_feature_contributions.png", dpi=160)
        plt.close()


def save_checkpoint(path: Path, model: TransformerAutoencoder, args: argparse.Namespace, input_dim: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "input_dim": input_dim,
            "model_dim": args.model_dim,
            "heads": args.heads,
            "layers": args.layers,
            "sequence_length": args.sequence_length,
        },
        path,
    )


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    device = choose_device(args.device)

    sequences, labels, end_indices, source_frame, artifacts = prepare_sequences(Path(args.data), args.sequence_length, args.label_column)
    artifacts.save(output_dir / "preprocessing_artifacts.json")

    normal_sequences = sequences[labels == 0]
    if len(normal_sequences) == 0:
        raise RuntimeError("No NORMAL rows found. Autoencoder pretraining needs normal behavior examples.")

    input_dim = sequences.shape[2]
    model = TransformerAutoencoder(input_dim, args.model_dim, args.heads, args.layers).to(device)

    pretrain_loader = DataLoader(TensorDataset(torch.tensor(normal_sequences)), batch_size=args.batch_size, shuffle=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    history = {"pretrain_loss": [], "finetune_loss": []}

    for _ in range(args.pretrain_epochs):
        history["pretrain_loss"].append(train_epoch(model, pretrain_loader, optimizer, device))
    save_checkpoint(output_dir / "pretrained_transformer_autoencoder.pt", model, args, input_dim)

    finetune_sequences = sequences if args.train_on_all else normal_sequences
    finetune_loader = DataLoader(TensorDataset(torch.tensor(finetune_sequences)), batch_size=args.batch_size, shuffle=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-4)
    for _ in range(args.epochs):
        history["finetune_loss"].append(train_epoch(model, finetune_loader, optimizer, device))

    scores, reconstructions = evaluate_scores(model, sequences, device, args.batch_size)
    normal_scores = scores[labels == 0]
    mean_std_threshold = float(normal_scores.mean() + 3.0 * normal_scores.std())
    percentile_threshold = float(np.percentile(normal_scores, args.threshold_percentile))
    threshold = max(mean_std_threshold, percentile_threshold)
    predictions = (scores >= threshold).astype(int)
    metrics = safe_metrics(labels, predictions, scores)

    results = source_frame.iloc[end_indices].copy()
    results["sequence_label"] = labels
    results["anomaly_score"] = scores
    results["dynamic_threshold"] = threshold
    results["model_prediction"] = np.where(predictions == 1, "ANOMALY", "NORMAL")
    results.to_csv(output_dir / "anomaly_predictions.csv", index=False)

    model.eval()
    sample_index = int(np.argmax(scores))
    with torch.no_grad():
        sample = torch.tensor(sequences[sample_index : sample_index + 1]).to(device)
        reconstruction, attentions = model(sample, return_attention=True)
    attention_arrays = [attention.cpu().numpy()[0] for attention in attentions]
    timestep_scores = attention_timestep_scores(attention_arrays)
    contributions = feature_contributions(sequences[sample_index], reconstruction.cpu().numpy()[0], artifacts.feature_columns, top_k=5)
    explanation = fuse_explanation(float(scores[sample_index]), threshold, timestep_scores, contributions)
    save_plots(output_dir, history, labels, predictions, scores, threshold, timestep_scores, contributions)

    report = {
        "architecture": "Pretrained Transformer Encoder + Autoencoder",
        "pipeline": [
            "data collection",
            "preprocessing and normalization",
            "temporal sequence conversion",
            "self-supervised pretraining on normal behavior",
            "fine-tuning reconstruction model",
            "dynamic threshold anomaly detection",
            "attention + contribution explanation fusion",
        ],
        "rows": int(len(source_frame)),
        "sequences": int(len(sequences)),
        "normal_sequences": int((labels == 0).sum()),
        "alert_sequences": int((labels == 1).sum()),
        "finetune_mode": "all_sequences" if args.train_on_all else "normal_only",
        "threshold": threshold,
        "threshold_mean_plus_3std": mean_std_threshold,
        "threshold_percentile": percentile_threshold,
        "metrics": metrics,
        "example_explanation": explanation,
        "training_history": history,
    }
    (output_dir / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame({"epoch": range(1, len(history["pretrain_loss"]) + 1), "loss": history["pretrain_loss"]}).to_csv(
        output_dir / "pretraining_loss.csv", index=False
    )
    pd.DataFrame({"epoch": range(1, len(history["finetune_loss"]) + 1), "loss": history["finetune_loss"]}).to_csv(
        output_dir / "finetuning_loss.csv", index=False
    )
    save_checkpoint(output_dir / "transformer_autoencoder.pt", model, args, input_dim)

    print(f"Saved pretrained model: {output_dir / 'pretrained_transformer_autoencoder.pt'}")
    print(f"Saved final model: {output_dir / 'transformer_autoencoder.pt'}")
    print(f"Saved predictions: {output_dir / 'anomaly_predictions.csv'}")
    print(f"Saved plots: {output_dir / 'plots'}")
    print(f"Metrics: {metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
