from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype
from sklearn.preprocessing import StandardScaler


NUMERIC_COLUMNS = ["consommation_kw", "tension_v", "courant_a"]
CATEGORICAL_COLUMNS = ["meter_id", "zone", "type"]
LABEL_COLUMN = "statut"
KAGGLE_LABEL_COLUMN = "stabf"
KAGGLE_DROP_COLUMNS = ["stab"]
SMART_GRID_BINARY_LABELS = ["Overload Condition", "Transformer Fault"]


@dataclass
class PreprocessArtifacts:
    numeric_columns: list[str]
    categorical_columns: list[str]
    feature_columns: list[str]
    sequence_length: int
    scaler_mean: list[float]
    scaler_scale: list[float]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def _label_to_anomaly(values: pd.Series) -> pd.Series:
    normalized = values.astype(str).str.strip().str.lower()
    normal_values = {"normal", "stable", "0", "false", "benign"}
    return (~normalized.isin(normal_values)).astype(int)


def load_dataset(path: Path, label_column: str | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, on_bad_lines="skip")
    is_smart_meter_data = False

    if "Timestamp" in frame.columns and "timestamp" not in frame.columns:
        frame = frame.rename(columns={"Timestamp": "timestamp"})

    if set(NUMERIC_COLUMNS).issubset(frame.columns):
        is_smart_meter_data = True
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame = frame.dropna(subset=["timestamp"]).sort_values(["meter_id", "timestamp"])
        label_column = label_column or LABEL_COLUMN
    else:
        if "timestamp" in frame.columns:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
            frame = frame.dropna(subset=["timestamp"])
        else:
            frame["timestamp"] = pd.RangeIndex(start=0, stop=len(frame), step=1)
        label_column = label_column or (KAGGLE_LABEL_COLUMN if KAGGLE_LABEL_COLUMN in frame.columns else None)

    numeric_columns = [column for column in frame.select_dtypes(include=[np.number]).columns if column not in KAGGLE_DROP_COLUMNS]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame[column] = frame[column].fillna(frame[column].median())

    if is_datetime64_any_dtype(frame["timestamp"]):
        frame["hour"] = frame["timestamp"].dt.hour
        frame["dayofweek"] = frame["timestamp"].dt.dayofweek
    else:
        frame["hour"] = np.arange(len(frame)) % 24
        frame["dayofweek"] = (np.arange(len(frame)) // 24) % 7
    frame["hour_sin"] = np.sin(2 * np.pi * frame["hour"] / 24.0)
    frame["hour_cos"] = np.cos(2 * np.pi * frame["hour"] / 24.0)
    binary_labels = [column for column in SMART_GRID_BINARY_LABELS if column in frame.columns]
    if label_column and label_column in frame.columns:
        frame["is_alert"] = _label_to_anomaly(frame[label_column])
    elif binary_labels:
        frame["is_alert"] = frame[binary_labels].astype(int).max(axis=1)
    else:
        frame["is_alert"] = 0

    if is_smart_meter_data:
        frame = add_smart_meter_features(frame)
    else:
        frame = add_generic_temporal_features(frame)
    return frame


def add_smart_meter_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    grouped = frame.groupby("meter_id", sort=False)

    for column in NUMERIC_COLUMNS:
        frame[f"{column}_diff"] = grouped[column].diff().fillna(0.0)
        # Rolling window of 3
        frame[f"{column}_rolling_mean_3"] = grouped[column].transform(lambda values: values.rolling(3, min_periods=1).mean())
        frame[f"{column}_rolling_std_3"] = (
            grouped[column].transform(lambda values: values.rolling(3, min_periods=1).std()).fillna(0.0)
        )
        # Wider rolling window of 6 for slower trend detection
        frame[f"{column}_rolling_mean_6"] = grouped[column].transform(lambda values: values.rolling(6, min_periods=1).mean())
        frame[f"{column}_rolling_std_6"] = (
            grouped[column].transform(lambda values: values.rolling(6, min_periods=1).std()).fillna(0.0)
        )

    frame["voltage_deviation_230"] = (frame["tension_v"] - 230.0).abs()
    frame["voltage_nominal_ratio"] = frame["tension_v"] / 230.0

    frame["current_voltage_ratio"] = frame["courant_a"] / frame["tension_v"].replace(0, np.nan)
    frame["current_voltage_ratio"] = frame["current_voltage_ratio"].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # Power factor approximation: P(kW) / S(kVA).
    # Clip tightly to [0, 1.1] — values above 1 are physically impossible but
    # can appear from measurement noise; clipping prevents extreme outliers from
    # dominating the StandardScaler and the reconstruction error.
    apparent_power = (frame["tension_v"] * frame["courant_a"]) / 1000.0
    frame["power_factor"] = (frame["consommation_kw"] / apparent_power.replace(0, np.nan)).clip(0.0, 1.1).fillna(1.0)

    # Weekend indicator
    frame["is_weekend"] = (frame["dayofweek"] >= 5).astype(float)

    if "zone" in frame.columns:
        frame["zone_consumption_mean"] = frame.groupby(["timestamp", "zone"])["consommation_kw"].transform("mean")
        frame["meter_vs_zone_consumption"] = frame["consommation_kw"] - frame["zone_consumption_mean"]
    else:
        frame["zone_consumption_mean"] = frame["consommation_kw"]
        frame["meter_vs_zone_consumption"] = 0.0

    return frame


def add_generic_temporal_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    numeric_columns = [
        column
        for column in frame.select_dtypes(include=[np.number]).columns
        if column not in {"is_alert", "hour", "dayofweek", *SMART_GRID_BINARY_LABELS, *KAGGLE_DROP_COLUMNS}
    ]
    for column in numeric_columns:
        frame[f"{column}_diff"] = frame[column].diff().fillna(0.0)
        frame[f"{column}_rolling_mean_3"] = frame[column].rolling(3, min_periods=1).mean()
        frame[f"{column}_rolling_std_3"] = frame[column].rolling(3, min_periods=1).std().fillna(0.0)
    return frame


def build_feature_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if set(NUMERIC_COLUMNS).issubset(frame.columns):
        excluded_smart = {"is_alert", "hour", "dayofweek", "hour_sin", "hour_cos"}
        base_numeric = [
            column
            for column in frame.select_dtypes(include=[np.number]).columns
            if column not in excluded_smart and not column.startswith("Unnamed")
        ]
        categorical = [column for column in CATEGORICAL_COLUMNS if column in frame.columns]
    else:
        excluded = {
            "is_alert",
            "timestamp",
            "hour",
            "dayofweek",
            KAGGLE_LABEL_COLUMN,
            LABEL_COLUMN,
            *KAGGLE_DROP_COLUMNS,
            *SMART_GRID_BINARY_LABELS,
        }
        base_numeric = [
            column
            for column in frame.select_dtypes(include=[np.number]).columns
            if column not in excluded and not column.startswith("Unnamed")
        ]
        categorical = [
            column
            for column in frame.select_dtypes(exclude=[np.number]).columns
            if column not in excluded and not column.startswith("Unnamed")
        ]
    encoded = pd.get_dummies(frame[categorical], prefix=categorical, dtype=float) if categorical else pd.DataFrame(index=frame.index)
    numeric = frame[base_numeric + ["hour_sin", "hour_cos"]].astype(float)
    features = pd.concat([numeric, encoded], axis=1)
    return features, list(features.columns)


def scale_features(features: pd.DataFrame, scaler: StandardScaler | None = None) -> tuple[np.ndarray, StandardScaler]:
    scaler = scaler or StandardScaler()
    values = scaler.fit_transform(features.values) if not hasattr(scaler, "mean_") else scaler.transform(features.values)
    return values.astype("float32"), scaler


def make_sequences(
    values: np.ndarray,
    labels: np.ndarray,
    sequence_length: int,
    label_strategy: str = "last",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build sliding-window sequences.

    label_strategy:
      "last"     – sequence label = label of the final timestep (recommended for
                   anomaly detection: predict current state from recent history)
      "any"      – anomaly if any timestep in the window is an anomaly
      "majority" – anomaly if more than half of the timesteps are anomalies
    """
    if label_strategy not in {"last", "any", "majority"}:
        raise ValueError("label_strategy must be one of: last, any, majority")
    if len(values) < sequence_length:
        raise ValueError(f"Need at least {sequence_length} rows to build temporal sequences")

    sequences: list[np.ndarray] = []
    sequence_labels: list[int] = []
    end_indices: list[int] = []
    for end in range(sequence_length, len(values) + 1):
        start = end - sequence_length
        window = values[start:end]
        window_labels = labels[start:end]
        if label_strategy == "last":
            label = int(window_labels[-1])
        elif label_strategy == "majority":
            label = int(window_labels.mean() >= 0.5)
        else:
            label = int(window_labels.max())
        sequences.append(window)
        sequence_labels.append(label)
        end_indices.append(end - 1)
    return np.stack(sequences), np.asarray(sequence_labels), np.asarray(end_indices)


def prepare_sequences(
    csv_path: Path,
    sequence_length: int,
    label_column: str | None = None,
    label_strategy: str = "last",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame, PreprocessArtifacts]:
    frame = load_dataset(csv_path, label_column)
    features, feature_columns = build_feature_frame(frame)
    values, scaler = scale_features(features)
    sequences, labels, end_indices = make_sequences(values, frame["is_alert"].values, sequence_length, label_strategy)
    artifacts = PreprocessArtifacts(
        numeric_columns=[column for column in features.columns if column in frame.columns],
        categorical_columns=[
            column for column in frame.select_dtypes(exclude=[np.number]).columns if column not in {LABEL_COLUMN, KAGGLE_LABEL_COLUMN}
        ],
        feature_columns=feature_columns,
        sequence_length=sequence_length,
        scaler_mean=scaler.mean_.tolist(),
        scaler_scale=scaler.scale_.tolist(),
    )
    return sequences, labels, end_indices, frame, artifacts
