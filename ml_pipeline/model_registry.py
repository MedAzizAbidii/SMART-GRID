"""Model registry for production Smart Grid anomaly detection.

Tracks every trained model version with its metrics, supports auto-rollback
when a new model's AUC drops more than 2% below the current champion, and
provides a simple CLI for listing and promoting models.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REGISTRY_FILE = "outputs/model_registry.json"
ROLLBACK_AUC_DELTA = 0.02  # auto-rollback if new AUC < champion AUC - 2%


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelRegistry:
    """Persistent model version tracker stored as a JSON file."""

    def __init__(self, registry_path: Path | None = None):
        base = Path(__file__).resolve().parent.parent
        self.path = (registry_path or (base / REGISTRY_FILE)).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        model_dir: Path,
        metrics: dict[str, float],
        config: dict[str, Any] | None = None,
        tag: str = "",
    ) -> str:
        """Register a newly trained model and determine if it should be promoted.

        Returns the version id (e.g. "v3").
        """
        version = f"v{len(self._data['versions']) + 1}"
        entry = {
            "version": version,
            "tag": tag or version,
            "model_dir": str(model_dir),
            "metrics": metrics,
            "config": config or {},
            "registered_at": _utcnow(),
            "status": "candidate",  # candidate → champion / rolled_back
        }
        self._data["versions"].append(entry)

        champion = self._champion()
        if champion is None:
            # First model is always champion
            entry["status"] = "champion"
            self._data["champion_version"] = version
        else:
            new_auc = float(metrics.get("roc_auc", 0.0))
            champ_auc = float(champion["metrics"].get("roc_auc", 0.0))
            if new_auc >= champ_auc - ROLLBACK_AUC_DELTA:
                # New model is as good or better — promote it
                champion["status"] = "retired"
                entry["status"] = "champion"
                self._data["champion_version"] = version
            else:
                # Rollback: new model is worse — keep champion, mark candidate as rolled_back
                entry["status"] = "rolled_back"
                entry["rollback_reason"] = (
                    f"AUC {new_auc:.4f} < champion AUC {champ_auc:.4f} - {ROLLBACK_AUC_DELTA}"
                )

        self._save()
        return version

    def champion(self) -> dict[str, Any] | None:
        """Return the current champion model entry, or None."""
        return self._champion()

    def champion_model_dir(self) -> Path | None:
        champ = self._champion()
        if champ is None:
            return None
        return Path(champ["model_dir"])

    def list_versions(self) -> list[dict[str, Any]]:
        return list(self._data["versions"])

    def summary(self) -> dict[str, Any]:
        champ = self._champion()
        return {
            "total_versions": len(self._data["versions"]),
            "champion_version": self._data.get("champion_version"),
            "champion_metrics": champ["metrics"] if champ else {},
            "champion_dir": champ["model_dir"] if champ else None,
            "last_updated": self._data.get("last_updated"),
        }

    def copy_champion_to(self, dest_dir: Path) -> bool:
        """Copy champion model files to dest_dir. Returns True on success."""
        champ = self._champion()
        if champ is None:
            return False
        src = Path(champ["model_dir"])
        if not src.exists():
            return False
        dest_dir.mkdir(parents=True, exist_ok=True)
        for fname in ["transformer_autoencoder.pt", "preprocessing_artifacts.json", "training_report.json"]:
            src_file = src / fname
            if src_file.exists():
                shutil.copy2(src_file, dest_dir / fname)
        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _champion(self) -> dict[str, Any] | None:
        champ_ver = self._data.get("champion_version")
        if not champ_ver:
            return None
        for entry in self._data["versions"]:
            if entry["version"] == champ_ver:
                return entry
        return None

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"versions": [], "champion_version": None, "last_updated": _utcnow()}

    def _save(self) -> None:
        self._data["last_updated"] = _utcnow()
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Helper called from run_transformer_autoencoder.py after training completes
# ---------------------------------------------------------------------------

def register_run(
    output_dir: Path,
    metrics: dict[str, float],
    config: dict[str, Any] | None = None,
    tag: str = "",
) -> tuple[str, bool]:
    """Register a training run.  Returns (version_id, was_promoted)."""
    registry = ModelRegistry()
    version = registry.register(output_dir, metrics, config, tag)
    champ = registry.champion()
    promoted = champ is not None and champ["version"] == version
    return version, promoted
