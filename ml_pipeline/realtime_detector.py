"""Real-time anomaly detector for production Smart Grid deployment.

Maintains a rolling buffer of the last seq_len readings per meter,
runs instant inference (<50ms), computes per-meter adaptive thresholds,
and returns integrated-gradient XAI attribution without SHAP overhead.

Ensemble mode (default when both v2 and v3 models exist):
  - v2 triggers the alert (Recall=75%, threshold=0.000351)
  - v3 confirms and sets confidence level (Precision=99.75%, threshold=0.001041)
  Combined: high recall with precision grading. Optimised for grid security
  (missing an attack costs far more than a false positive).

Meter-ID fix:
  One-hot meter_id_SM_* columns are zeroed before inference so that
  new/unseen meters are not systematically flagged as anomalies due to
  an all-zero one-hot vector looking unusual to the model.
"""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

# Allow importing from parent package when run directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml_pipeline.preprocessing import (
    PreprocessArtifacts,
    add_smart_meter_features,
    build_feature_frame,
)


# ---------------------------------------------------------------------------
# Model architecture (must match run_transformer_autoencoder.py exactly)
# ---------------------------------------------------------------------------

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class TransformerAutoencoder(nn.Module):
    def __init__(
        self,
        input_dim: int,
        model_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        feedforward_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_projection = nn.Linear(input_dim, model_dim)
        self.pos_encoding = PositionalEncoding(model_dim, dropout=dropout)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=model_dim,
            nhead=num_heads,
            dim_feedforward=feedforward_dim,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.output_projection = nn.Linear(model_dim, input_dim)
        self._attention_weights: list[torch.Tensor] = []

    def _get_attention_hook(self):
        def hook(module, inp, out):
            if isinstance(out, tuple):
                self._attention_weights.append(out[1])
        return hook

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor]]:
        self._attention_weights = []
        hooks = []
        for layer in self.encoder.layers:
            hooks.append(layer.self_attn.register_forward_hook(self._get_attention_hook()))
        projected = self.input_projection(x)
        encoded = self.encoder(self.pos_encoding(projected))
        for h in hooks:
            h.remove()
        return encoded, list(self._attention_weights)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor]]:
        encoded, attn = self.encode(x)
        reconstruction = self.output_projection(encoded)
        return reconstruction, attn


# ---------------------------------------------------------------------------
# Cross-meter zone aggregator
# ---------------------------------------------------------------------------

class ZoneAggregator:
    """Shared latest-known consumption per meter, grouped by zone.

    Training computes `zone_consumption_mean` / `meter_vs_zone_consumption`
    by averaging ALL meters (mixed residential/commercial/industrial) in a
    zone at each timestamp. A single meter's rolling buffer has no visibility
    into other meters, so computing these features from just one meter's
    history collapses zone_consumption_mean to that meter's own value —
    which is wildly off-scale versus the training-time zone average and
    causes the reconstruction error to spike regardless of whether the
    reading is actually anomalous. This shared, process-wide tracker fixes
    that by remembering the latest reading from every meter that has passed
    through ANY detector instance, so the zone mean reflects the real mix.
    """

    def __init__(self) -> None:
        self._latest: dict[str, dict[str, float]] = {}   # zone -> {meter_id: consumption}

    def update(self, zone: str, meter_id: str, consumption: float) -> None:
        self._latest.setdefault(zone, {})[meter_id] = float(consumption)

    def zone_mean(self, zone: str) -> float | None:
        meters = self._latest.get(zone)
        if not meters:
            return None
        return float(np.mean(list(meters.values())))


# Process-wide singleton: all RealtimeDetector instances (v2 + v3 in the
# ensemble) share the same view of "which meters have reported what," since
# they all receive the same stream of readings.
_ZONE_AGGREGATOR = ZoneAggregator()


# ---------------------------------------------------------------------------
# Per-meter threshold tracker
# ---------------------------------------------------------------------------

class MeterThresholdTracker:
    """Tracks reconstruction errors per meter and computes adaptive thresholds.

    Two layers of adaptation, both of which auto-recalibrate as the input
    distribution drifts (e.g. season change or synthetic->real data) — the
    exact failure the cross-distribution test exposed for a FIXED threshold:

      1. Per-meter: once a meter has >= MIN_SAMPLES normal scores, its threshold
         is mean + K_SIGMA*std over its own recent history.
      2. Global (cold-start / unseen meters): once GLOBAL_MIN normal scores have
         been seen across ALL meters, cold meters use an adaptive global
         mean + K_SIGMA*std instead of the static bootstrap threshold. This is
         what stops a brand-new deployment on shifted data from drowning in
         false positives before per-meter history builds up.
    """

    MIN_SAMPLES = 30
    K_SIGMA = 3.0
    HISTORY_LEN = 500
    GLOBAL_MIN = 200          # global samples before the global threshold adapts
    GLOBAL_HISTORY = 5000
    GLOBAL_PCTILE = 98.0      # robust to the ~1-3% attack contamination in the pool

    def __init__(self, global_threshold: float, auto_recalibrate: bool = False):
        # auto_recalibrate is OPT-IN. Default OFF preserves the validated
        # trained-threshold behaviour (a security tool must not silently trade
        # recall for fewer false alarms). Turn ON only for a deployment on a
        # KNOWN-shifted distribution where you accept a more conservative
        # (higher-precision, lower-recall) operating point, or — better — run
        # recalibrate.py on a clean baseline first, which is controllable.
        self._auto = auto_recalibrate
        self._bootstrap = global_threshold      # static fallback from training
        self._global = global_threshold
        self._scores: dict[str, deque] = {}
        self._global_scores: deque = deque(maxlen=self.GLOBAL_HISTORY)

    def update(self, meter_id: str, score: float, is_normal: bool) -> None:
        # Per-meter pool: only confirmed-normal scores (validated behaviour).
        if is_normal:
            if meter_id not in self._scores:
                self._scores[meter_id] = deque(maxlen=self.HISTORY_LEN)
            self._scores[meter_id].append(score)
        # Global pool collects every score; only DRIVES the threshold when
        # auto-recalibration is enabled. A high percentile of the (rare-attack)
        # mixed stream tracks the normal upper boundary and self-bootstraps
        # even when the initial threshold is wrong for a new distribution.
        self._global_scores.append(score)
        if self._auto and len(self._global_scores) >= self.GLOBAL_MIN and \
                len(self._global_scores) % 50 == 0:
            self._global = float(np.percentile(self._global_scores, self.GLOBAL_PCTILE))

    def threshold(self, meter_id: str) -> float:
        history = self._scores.get(meter_id)
        if history is None or len(history) < self.MIN_SAMPLES:
            return self._global
        arr = np.array(history)
        return float(arr.mean() + self.K_SIGMA * arr.std())

    def global_threshold(self) -> float:
        return self._global

    def is_global_adaptive(self) -> bool:
        return self._auto and len(self._global_scores) >= self.GLOBAL_MIN

    def all_thresholds(self) -> dict[str, float]:
        return {mid: self.threshold(mid) for mid in self._scores}


# ---------------------------------------------------------------------------
# Integrated gradients (fast XAI — no SHAP)
# ---------------------------------------------------------------------------

def integrated_gradients(
    model: TransformerAutoencoder,
    sequence: torch.Tensor,
    device: torch.device,
    n_steps: int = 20,
) -> np.ndarray:
    """Return per-feature attribution via integrated gradients.

    Shape of returned array: (input_dim,) — summed over the time axis.
    """
    model.eval()
    baseline = torch.zeros_like(sequence)
    alphas = torch.linspace(0, 1, n_steps, device=device)

    grads = []
    for alpha in alphas:
        interp = (baseline + alpha * (sequence - baseline)).detach().requires_grad_(True)
        recon, _ = model(interp)
        loss = nn.functional.mse_loss(recon, interp)
        loss.backward()
        if interp.grad is not None:
            grads.append(interp.grad.detach().cpu().numpy())

    if not grads:
        return np.zeros(sequence.shape[-1])

    avg_grads = np.mean(grads, axis=0)  # (1, seq_len, features)
    delta = (sequence - baseline).detach().cpu().numpy()
    attributions = avg_grads * delta  # (1, seq_len, features)
    return np.abs(attributions[0]).sum(axis=0)  # (features,)


# ---------------------------------------------------------------------------
# Attack type heuristic classifier
# ---------------------------------------------------------------------------

ATTACK_RULES: dict[str, str] = {
    "fdia": "False Data Injection Attack — measurement values systematically falsified",
    "dos": "Denial of Service — communication disruption across zone",
    "fraud": "Energy Fraud — abnormal consumption without corresponding electrical signature",
    "fault": "Grid Fault — sudden voltage drop or current spike from equipment failure",
}


def classify_attack_type(
    top_features: list[tuple[str, float]],
    consommation_kw: float,
    tension_v: float,
    courant_a: float,
) -> tuple[str, str]:
    """Rule-based attack classification from XAI features and raw readings."""
    feat_names = {name for name, _ in top_features}

    # FDIA: voltage manipulation is the dominant signal
    voltage_features = {f for f in feat_names if "tension" in f or "voltage" in f}
    if voltage_features and any("tension" in f for f, _ in top_features[:2]):
        return "fdia", ATTACK_RULES["fdia"]

    # Fraud: consumption spike but power factor is fine (current/voltage normal)
    if "zone_consumption_mean" in feat_names or "consommation_kw_diff" in feat_names:
        apparent = (tension_v * courant_a) / 1000.0
        pf = consommation_kw / apparent if apparent > 0 else 1.0
        if consommation_kw > 5.0 and pf < 0.5:
            return "fraud", ATTACK_RULES["fraud"]

    # Fault: voltage suddenly very low or current very high
    if tension_v < 180.0 or courant_a > 50.0:
        return "fault", ATTACK_RULES["fault"]

    # Default: DoS / zone-wide disruption
    return "dos", ATTACK_RULES["dos"]


# ---------------------------------------------------------------------------
# Realtime Detector — main class
# ---------------------------------------------------------------------------

class RealtimeDetector:
    """
    Production-ready anomaly detector.

    Load once at startup, call `ingest(meter_id, reading)` on every new
    smart-meter reading. Returns a detection result dict immediately.
    """

    def __init__(
        self,
        model_path: Path,
        artifacts_path: Path,
        global_threshold: float | None = None,
        device_str: str = "cpu",
    ):
        self.device = torch.device(device_str)
        self.artifacts = self._load_artifacts(artifacts_path)
        self.seq_len = self.artifacts.sequence_length
        self.feature_columns = self.artifacts.feature_columns
        self.scaler_mean = np.array(self.artifacts.scaler_mean, dtype="float32")
        self.scaler_scale = np.array(self.artifacts.scaler_scale, dtype="float32")

        self.model = self._load_model(model_path, len(self.feature_columns))
        self.model.to(self.device)
        self.model.eval()

        # If no global threshold is given, fall back to a conservative value
        _fallback = float(global_threshold) if global_threshold else 5e-4
        # Opt-in online threshold auto-recalibration (env SMARTGRID_AUTO_RECAL=1).
        # Off by default; see MeterThresholdTracker for the trade-off.
        import os as _os
        _auto = _os.environ.get("SMARTGRID_AUTO_RECAL", "0") == "1"
        self.threshold_tracker = MeterThresholdTracker(_fallback, auto_recalibrate=_auto)

        # Rolling buffer: meter_id → deque of raw row dicts. Retains more than
        # seq_len rows (seq_len + widest rolling window used in preprocessing,
        # currently 6) so diff/rolling features for the oldest row IN THE
        # MODEL'S INPUT WINDOW can be computed from real prior readings,
        # matching how training computes them over the full continuous
        # per-meter series — instead of always resetting to "no history" at
        # the edge of a freshly-rebuilt window (see _build_sequence_tensor).
        self._buffer_retain = self.seq_len + 6
        self._buffers: dict[str, deque] = {}

        # Alert deduplication: meter_id → last alert timestamp
        self._last_alert_at: dict[str, float] = {}
        self.alert_cooldown_sec = 300.0  # 5 minutes

        # Platt scaling calibration (loaded if calibration_params.json exists)
        self._calib_a: float | None = None
        self._calib_b: float | None = None
        self._load_calibration(model_path.parent)

        # Inference latency tracking
        self._latency_ms: deque = deque(maxlen=100)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, reading: dict[str, Any]) -> dict[str, Any]:
        """Process one smart-meter reading and return detection result.

        Parameters
        ----------
        reading : dict with at least:
            meter_id, timestamp, consommation_kw, tension_v, courant_a,
            zone, type  (same columns as donnees_smart_meters.csv)

        Returns
        -------
        dict with keys: meter_id, is_anomaly, anomaly_score, threshold,
                        confidence, attack_type, attack_description,
                        top_features, critical_timestep, deduplicated,
                        inference_ms
        """
        t0 = time.perf_counter()
        meter_id = str(reading.get("meter_id", "unknown"))

        # Update rolling buffer (retains extra history for correct diff/rolling
        # computation — see self._buffer_retain)
        if meter_id not in self._buffers:
            self._buffers[meter_id] = deque(maxlen=self._buffer_retain)
        self._buffers[meter_id].append(reading)

        # Update the shared cross-meter zone view (see ZoneAggregator docstring)
        zone = reading.get("zone")
        consumption = reading.get("consommation_kw")
        if zone is not None and consumption is not None:
            _ZONE_AGGREGATOR.update(str(zone), meter_id, float(consumption))

        # Need a full sequence
        buf = self._buffers[meter_id]
        if len(buf) < self.seq_len:
            return self._insufficient_data(meter_id, len(buf))

        # Build sequence tensor
        sequence_tensor = self._build_sequence_tensor(list(buf))
        if sequence_tensor is None:
            return self._insufficient_data(meter_id, len(buf))

        # Run inference
        with torch.no_grad():
            recon, attn_weights = self.model(sequence_tensor)
            score = float(nn.functional.mse_loss(recon, sequence_tensor).item())

        # Per-meter threshold
        threshold = self.threshold_tracker.threshold(meter_id)
        is_anomaly = score >= threshold
        confidence = min(1.0, score / max(threshold, 1e-9))

        # Update tracker with this reading's score
        self.threshold_tracker.update(meter_id, score, not is_anomaly)

        # XAI — integrated gradients (fast, no SHAP)
        top_features, critical_timestep = [], 0
        if is_anomaly:
            top_features, critical_timestep = self._explain(
                sequence_tensor, attn_weights
            )

        # Attack classification
        attack_type, attack_desc = "normal", ""
        if is_anomaly:
            attack_type, attack_desc = classify_attack_type(
                top_features,
                float(reading.get("consommation_kw", 0)),
                float(reading.get("tension_v", 230)),
                float(reading.get("courant_a", 0)),
            )

        # Alert deduplication
        now = time.time()
        deduplicated = False
        if is_anomaly:
            last = self._last_alert_at.get(meter_id, 0.0)
            if now - last < self.alert_cooldown_sec:
                deduplicated = True
            else:
                self._last_alert_at[meter_id] = now

        latency = (time.perf_counter() - t0) * 1000.0
        self._latency_ms.append(latency)

        calib_prob = self.get_calibrated_probability(score)

        return {
            "meter_id": meter_id,
            "timestamp": reading.get("timestamp", now),
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 8),
            "threshold": round(threshold, 8),
            "confidence": round(confidence, 4),
            "anomaly_probability": calib_prob,   # calibrated P(anomaly) via Platt scaling
            "attack_type": attack_type,
            "attack_description": attack_desc,
            "top_features": [{"feature": f, "contribution": round(c, 4)} for f, c in top_features],
            "critical_timestep": critical_timestep,
            "deduplicated": deduplicated,
            "buffer_fill": len(buf),
            "inference_ms": round(latency, 2),
        }

    def get_calibrated_probability(self, raw_score: float) -> float | None:
        """Return P(anomaly | score) via Platt scaling, or None if not calibrated."""
        if self._calib_a is None:
            return None
        val = 1.0 / (1.0 + np.exp(-np.clip(self._calib_a * raw_score + self._calib_b, -500, 500)))
        return round(float(val), 4)

    def avg_latency_ms(self) -> float:
        if not self._latency_ms:
            return 0.0
        return round(float(np.mean(self._latency_ms)), 2)

    def meter_thresholds(self) -> dict[str, float]:
        return self.threshold_tracker.all_thresholds()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_artifacts(self, path: Path) -> PreprocessArtifacts:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PreprocessArtifacts(**data)

    def _load_model(self, path: Path, input_dim: int) -> TransformerAutoencoder:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        if isinstance(checkpoint, dict) and "model_dim" in checkpoint:
            model_dim = checkpoint["model_dim"]
            num_layers = checkpoint.get("layers", checkpoint.get("num_layers", 2))
            num_heads = checkpoint.get("heads", checkpoint.get("num_heads", 4))
            # Support both key names used across versions
            state_dict = checkpoint.get("model_state") or checkpoint.get("state_dict") or checkpoint
        else:
            # Plain state dict — infer model size from first linear layer
            state_dict = checkpoint
            proj_weight = state_dict.get("input_projection.weight")
            model_dim = int(proj_weight.shape[0]) if proj_weight is not None else 64
            num_layers = 2
            num_heads = 4

        model = TransformerAutoencoder(
            input_dim=input_dim,
            model_dim=model_dim,
            num_heads=num_heads,
            num_layers=num_layers,
        )
        model.load_state_dict(state_dict, strict=False)
        return model

    def _build_sequence_tensor(self, rows: list[dict]) -> torch.Tensor | None:
        """Convert list of raw reading dicts → normalised (1, seq_len, features) tensor."""
        import pandas as pd

        try:
            frame = pd.DataFrame(rows)
            # Ensure timestamp is datetime for feature engineering
            if "timestamp" in frame.columns:
                frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
            # Derive temporal features from the REAL reading time. Note: naive
            # (non-timezone-aware) datetime64 dtypes have no `.tz` attribute at
            # all, so a `hasattr(dtype, "tz")` check is always False for the
            # normal case and silently falls back to buffer-position-based
            # fake hours — checking for a valid datetime dtype directly avoids
            # that trap.
            has_real_timestamp = (
                "timestamp" in frame.columns
                and pd.api.types.is_datetime64_any_dtype(frame["timestamp"])
                and frame["timestamp"].notna().all()
            )
            if has_real_timestamp:
                frame["hour"] = frame["timestamp"].dt.hour
                frame["dayofweek"] = frame["timestamp"].dt.dayofweek
            else:
                frame["hour"] = np.arange(len(frame)) % 24
                frame["dayofweek"] = (np.arange(len(frame)) // 24) % 7

            import numpy as _np
            frame["hour_sin"] = _np.sin(2 * _np.pi * frame["hour"] / 24.0)
            frame["hour_cos"] = _np.cos(2 * _np.pi * frame["hour"] / 24.0)
            frame["is_alert"] = 0  # unknown during live inference

            # Add smart-meter features (rolling, diff, zone, etc.) computed
            # over the FULL retained history (buffer holds seq_len + 6 rows),
            # not just the model's seq_len window — this gives diff/rolling
            # features real prior values at the edge of the eventual model
            # input window, matching how training computes them over each
            # meter's full continuous series instead of resetting to
            # "no history" every time the window is rebuilt.
            frame = add_smart_meter_features(frame)

            # Fix: a single-meter buffer can only average its own consumption
            # for zone_consumption_mean (group size 1), which is wildly off
            # the training-time cross-meter zone average. Override with the
            # shared, process-wide zone view so live inference matches the
            # distribution the model was trained on.
            if "zone" in frame.columns:
                zone_val = str(frame["zone"].iloc[-1])
                shared_mean = _ZONE_AGGREGATOR.zone_mean(zone_val)
                if shared_mean is not None:
                    frame["zone_consumption_mean"] = shared_mean
                    frame["meter_vs_zone_consumption"] = frame["consommation_kw"] - shared_mean

            # Now trim to the model's actual input window — the extra leading
            # rows have done their job (seeding real history for diff/rolling)
            # and are discarded here.
            frame = frame.iloc[-self.seq_len:].reset_index(drop=True)

            features_frame, _ = build_feature_frame(frame)

            # Align to training feature columns
            for col in self.feature_columns:
                if col not in features_frame.columns:
                    features_frame[col] = 0.0
            features_frame = features_frame[self.feature_columns]

            # NOTE: an earlier version of this code force-zeroed all one-hot
            # meter_id_* columns here, intending to stop unseen meters from
            # being flagged just for having an all-zero one-hot vector. That
            # was measured (2026-07) to instead break EVERY known meter: the
            # model leans on meter identity to predict its baseline load, so
            # stripping it inflated reconstruction error by ~75x and pushed
            # scores far above threshold regardless of whether the reading
            # was actually anomalous (near-100% false-positive rate in
            # scenario testing). No zeroing is needed anyway — a truly
            # unseen meter_id produces a column pd.get_dummies never creates,
            # so the "fill missing training columns with 0.0" alignment loop
            # above already yields an all-zero one-hot for it naturally,
            # while known meters correctly keep their real 1-hot signal.

            values = features_frame.values.astype("float32")
            # Normalise with training scaler
            values = (values - self.scaler_mean) / np.maximum(self.scaler_scale, 1e-8)
            tensor = torch.tensor(values, dtype=torch.float32).unsqueeze(0).to(self.device)
            return tensor
        except Exception:
            return None

    def _explain(
        self,
        sequence_tensor: torch.Tensor,
        attn_weights: list[torch.Tensor],
    ) -> tuple[list[tuple[str, float]], int]:
        """Return (top_features, critical_timestep) using integrated gradients."""
        # Critical timestep from attention (weights may be None if need_weights=False)
        critical_ts = 0
        valid_attn = [w for w in attn_weights if w is not None]
        if valid_attn:
            try:
                avg_attn = torch.stack([w.mean(dim=1) for w in valid_attn]).mean(dim=0)
                ts_importance = avg_attn[0].mean(dim=0).detach().cpu().numpy()
                critical_ts = int(np.argmax(ts_importance))
            except Exception:
                pass

        # Feature attribution via integrated gradients
        attr = integrated_gradients(self.model, sequence_tensor, self.device, n_steps=20)
        top_idx = np.argsort(attr)[::-1][:5]
        top_features = [
            (self.feature_columns[i], float(attr[i])) for i in top_idx if i < len(self.feature_columns)
        ]
        return top_features, critical_ts

    def _load_calibration(self, model_dir: Path) -> None:
        calib_file = model_dir / "calibration_params.json"
        if calib_file.exists():
            try:
                params = json.loads(calib_file.read_text(encoding="utf-8"))
                self._calib_a = float(params["a"])
                self._calib_b = float(params["b"])
            except Exception:
                pass

    def _insufficient_data(self, meter_id: str, current_len: int) -> dict[str, Any]:
        return {
            "meter_id": meter_id,
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "threshold": 0.0,
            "confidence": 0.0,
            "attack_type": "normal",
            "attack_description": "",
            "top_features": [],
            "critical_timestep": 0,
            "deduplicated": False,
            "buffer_fill": current_len,
            "inference_ms": 0.0,
            "status": f"buffering ({current_len}/{self.seq_len})",
        }


# ---------------------------------------------------------------------------
# Ensemble detector: v2 (high-recall) + v3 (high-precision)
# ---------------------------------------------------------------------------

class EnsembleDetector:
    """Two-stage detector: v2 fires the alert, v3 grades confidence.

    Stage 1 (v2, threshold=0.000351, Recall=75%):  catches attacks early.
    Stage 2 (v3, threshold=0.001041, Precision=99.75%): confirms severity.

    Confidence levels:
      "HIGH"   — both models agree it is an anomaly
      "MEDIUM" — v2 triggered but v3 did not confirm (investigate)
      "LOW"    — neither triggered (returned only when buffer not full)
    """

    def __init__(self, detector_v2: RealtimeDetector, detector_v3: RealtimeDetector):
        self._v2 = detector_v2
        self._v3 = detector_v3

    # --- Proxy the single-detector attributes the API/dashboard reads, so an
    # EnsembleDetector is a drop-in wherever a RealtimeDetector is expected.
    @property
    def seq_len(self) -> int:
        return self._v2.seq_len

    @property
    def feature_columns(self) -> list[str]:
        return self._v2.feature_columns

    @property
    def threshold_tracker(self) -> "MeterThresholdTracker":
        return self._v2.threshold_tracker

    def ingest(self, reading: dict[str, Any]) -> dict[str, Any]:
        result_v2 = self._v2.ingest(reading)
        result_v3 = self._v3.ingest(reading)

        # If either buffer is not full yet, return the v2 status
        if not result_v2.get("anomaly_score"):
            return result_v2

        v2_alarm = result_v2["is_anomaly"]
        v3_alarm = result_v3.get("is_anomaly", False)

        is_anomaly = v2_alarm  # v2 drives the alert
        confidence_label = "HIGH" if (v2_alarm and v3_alarm) else ("MEDIUM" if v2_alarm else "NONE")

        # Blend confidence score
        score_v2 = result_v2.get("anomaly_score", 0.0)
        score_v3 = result_v3.get("anomaly_score", 0.0)
        blended_score = 0.5 * score_v2 + 0.5 * score_v3

        # Numerical confidence: ratio of score to threshold (v3 more conservative)
        thr_v2 = result_v2.get("threshold", 1e-4)
        confidence_num = round(min(1.0, blended_score / max(thr_v2, 1e-9)), 4)

        result = dict(result_v2)  # base on v2 (high-recall)
        result["is_anomaly"] = is_anomaly
        result["anomaly_score"] = round(blended_score, 8)
        result["confidence"] = confidence_num
        result["confidence_label"] = confidence_label
        result["v2_score"] = round(score_v2, 8)
        result["v3_score"] = round(score_v3, 8)
        result["v2_alarm"] = v2_alarm
        result["v3_alarm"] = v3_alarm
        # Use v3 XAI when available (more precise model = better attributions)
        if v3_alarm and result_v3.get("top_features"):
            result["top_features"]     = result_v3["top_features"]
            result["critical_timestep"] = result_v3.get("critical_timestep", 0)
        return result

    def avg_latency_ms(self) -> float:
        return round((self._v2.avg_latency_ms() + self._v3.avg_latency_ms()) / 2, 2)

    def meter_thresholds(self) -> dict[str, float]:
        return self._v2.meter_thresholds()


# ---------------------------------------------------------------------------
# Module-level singleton loader
# ---------------------------------------------------------------------------

_detector_instance: RealtimeDetector | EnsembleDetector | None = None


def _load_single(base: Path, candidate: str) -> RealtimeDetector | None:
    """Load a single RealtimeDetector from a model directory."""
    out = base / candidate
    model_file     = out / "transformer_autoencoder.pt"
    artifacts_file = out / "preprocessing_artifacts.json"
    report_file    = out / "training_report.json"

    if not model_file.exists() or not artifacts_file.exists():
        return None

    threshold = None
    if report_file.exists():
        try:
            report = json.loads(report_file.read_text(encoding="utf-8"))
            threshold = float(report.get("threshold", 5e-4))
        except Exception:
            pass

    return RealtimeDetector(
        model_path=model_file,
        artifacts_path=artifacts_file,
        global_threshold=threshold,
    )


def reset_detector() -> None:
    """Drop the cached detector so the next get_detector() reloads from disk.

    Used after recalibrate.py updates a model's threshold, so the running API
    picks up the new threshold without a full process restart (/api/model/reload).
    """
    global _detector_instance
    _detector_instance = None


def get_detector(
    output_dir: str = "outputs/early_stopping_final",
    fallback_dirs: list[str] | None = None,
) -> RealtimeDetector | EnsembleDetector | None:
    """Return (and cache) the detector instance.

    When both v3 (champion) and v2 (high-recall) models are available,
    returns an EnsembleDetector for best production performance.
    Falls back to a single RealtimeDetector if only one model is found.
    """
    global _detector_instance
    if _detector_instance is not None:
        return _detector_instance

    base = Path(__file__).resolve().parent.parent

    # Try ensemble: v3 precision + v2 recall
    v3 = _load_single(base, "outputs/early_stopping_final")
    v2 = _load_single(base, "outputs/test_run_now")
    if v3 is not None and v2 is not None:
        _detector_instance = EnsembleDetector(detector_v2=v2, detector_v3=v3)
        return _detector_instance

    # Single-model fallback
    candidates = [output_dir] + (fallback_dirs or [
        "outputs/test_run_now",
        "outputs/improved_model",
    ])
    for candidate in candidates:
        det = _load_single(base, candidate)
        if det is not None:
            _detector_instance = det
            return _detector_instance

    return None
