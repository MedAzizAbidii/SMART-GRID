"""
production/inference_service.py — standalone AI inference microservice.

Wraps the EXISTING, UNMODIFIED ml_pipeline.realtime_detector.get_detector()
behind its own tiny FastAPI app, so the AI model can run in its own container
(own resource limits, own restart policy, independently scalable) rather than
always being in-process with the main API.

api_server.py's /api/detect endpoint calls this over HTTP automatically when
SGRID_INFERENCE_SERVICE_URL is set (see production/config/settings.py); when
unset, it keeps calling get_detector() in-process exactly as before — so
single-machine / local-dev deployments are completely unaffected, and this
is a genuinely optional deployment topology, not a forced rewrite.

No model weights, training code, or detection logic are touched — this file
only adds a network boundary around the existing detector object.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ml_pipeline.realtime_detector import get_detector

app = FastAPI(title="Smart Grid AI Inference Service", version="1.0.0")
_detector = None
_start = time.time()


class Reading(BaseModel):
    meter_id: str
    timestamp: str | float | None = None
    consommation_kw: float
    tension_v: float
    courant_a: float
    power_factor: float = 0.9
    frequency_hz: float = 60.0
    zone: str = "Zone A"
    type: str = "residentiel"


@app.on_event("startup")
async def _load_model() -> None:
    global _detector
    _detector = get_detector()


@app.get("/health")
async def health() -> dict:
    return {"status": "alive", "uptime_seconds": round(time.time() - _start, 1)}


@app.get("/health/ready")
async def ready() -> dict:
    return {"status": "ready" if _detector is not None else "not_ready",
            "model_loaded": _detector is not None}


@app.post("/predict")
async def predict(reading: Reading) -> dict[str, Any]:
    if _detector is None:
        return {"error": "model_unavailable"}
    raw = reading.model_dump()
    return _detector.ingest(raw)


@app.get("/model/status")
async def model_status() -> dict:
    if _detector is None:
        return {"loaded": False}
    return {
        "loaded": True,
        "seq_len": getattr(_detector, "seq_len", None),
        "feature_count": len(getattr(_detector, "feature_columns", [])),
        "avg_latency_ms": _detector.avg_latency_ms() if hasattr(_detector, "avg_latency_ms") else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("inference_service:app", host="0.0.0.0", port=8100, reload=False)
