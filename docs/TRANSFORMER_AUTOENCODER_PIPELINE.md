# Transformer Autoencoder XAI Pipeline

This implementation follows the end-to-end PDF pipeline:

1. **Data collection** from `donnees_smart_meters.csv`.
2. **Preprocessing** with missing-value handling, `StandardScaler`, categorical encoding, and timestamp features.
3. **Temporal sequences** using sliding windows of smart-meter events.
4. **Pretrained model** via self-supervised pretraining on normal sequences.
5. **Transformer Encoder + Autoencoder** with input embedding, positional encoding, multi-head attention, and feedforward layers.
6. **Anomaly detection** using reconstruction error and a dynamic threshold.
7. **XAI** using attention for *where* and reconstruction contributions for *why*.
8. **Evaluation** with accuracy, precision, recall, F1-score, and ROC-AUC.

## Install dependencies

```powershell
pip install -r requirements.txt
```

## Train

```powershell
python run_transformer_autoencoder.py --data donnees_smart_meters.csv
```

For a quick smoke run:

```powershell
python run_transformer_autoencoder.py --epochs 1 --pretrain-epochs 1 --batch-size 32
```

## Important outputs

- `outputs/transformer_autoencoder/pretrained_transformer_autoencoder.pt`
- `outputs/transformer_autoencoder/transformer_autoencoder.pt`
- `outputs/transformer_autoencoder/anomaly_predictions.csv`
- `outputs/transformer_autoencoder/training_report.json`
- `outputs/transformer_autoencoder/preprocessing_artifacts.json`

## Compare generated data with Kaggle data

Place the external Kaggle CSV at:

```text
data_generation/assetes/smart_grid_stability_augmented.csv
```

Then run:

```powershell
python compare_transformer_datasets.py --epochs 5 --pretrain-epochs 3 --device cpu
```

Comparison outputs:

- `outputs/dataset_comparison/comparison_report.md`
- `outputs/dataset_comparison/comparison_metrics.csv`
- `outputs/dataset_comparison/generated/`
- `outputs/dataset_comparison/kaggle/`

## Explanation logic

- **Attention** identifies the critical timestep in the sequence.
- **Feature contributions** rank variables with the largest reconstruction error.
- **Fusion** combines both into a final explanation: anomaly score, threshold, critical timestep, and top causes.
