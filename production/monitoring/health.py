"""
production/monitoring/health.py — health/readiness endpoints + Prometheus metrics.

Two-tier health check (standard k8s/Docker convention):
  /health       — liveness: process is up and can respond at all.
  /health/ready — readiness: dependencies are actually usable (model loaded,
                  blockchain ledger initialized). A load balancer should stop
                  routing traffic here on 503, but NOT restart the container
                  (that's what /health is for).

/metrics exposes Prometheus-format counters/gauges/histograms if
prometheus_client is installed; otherwise a plain-JSON fallback so monitoring
never hard-fails the app.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from fastapi import APIRouter, Response

try:
    from prometheus_client import (Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest)
    _PROM_AVAILABLE = True
except Exception:
    _PROM_AVAILABLE = False

_START_TIME = time.time()

if _PROM_AVAILABLE:
    REQUEST_COUNT = Counter("smartgrid_requests_total", "Total HTTP requests", ["method", "path", "status"])
    REQUEST_LATENCY = Histogram("smartgrid_request_latency_seconds", "Request latency", ["path"])
    PREDICTION_LATENCY = Histogram("smartgrid_prediction_latency_seconds", "Model inference latency")
    ANOMALY_COUNT = Counter("smartgrid_anomalies_total", "Total anomalies detected", ["attack_type"])
    MODEL_LOADED = Gauge("smartgrid_model_loaded", "1 if the detection model is loaded")
    BLOCKCHAIN_BLOCKS = Gauge("smartgrid_blockchain_blocks", "Number of blocks in the live ledger")
else:
    REQUEST_COUNT = REQUEST_LATENCY = PREDICTION_LATENCY = ANOMALY_COUNT = None
    MODEL_LOADED = BLOCKCHAIN_BLOCKS = None


def _safe_psutil():
    try:
        import psutil
        return psutil
    except Exception:
        return None


# Phase 8.5 fix: psutil.cpu_percent(interval=0.1) is a BLOCKING call — it
# sleeps for the interval before returning, which froze the event loop for
# ~100ms on every /health/detailed request (measured, Phase 7 profiling),
# polled every 5s by the dashboard's own health widget. psutil's own
# documented non-blocking pattern is interval=None, which returns the CPU
# usage since the LAST call to cpu_percent() instead of sleeping — but its
# first-ever call returns a meaningless 0.0, so we prime it once here at
# import time (module load, not per-request) and use interval=None in the
# handler from then on. Same JSON shape, same key, zero blocking.
_psutil_primed = _safe_psutil()
if _psutil_primed is not None:
    _psutil_primed.cpu_percent(interval=None)


def build_health_router(get_detector_fn: Callable[[], Any], get_ledger_fn: Callable[[], Any]) -> APIRouter:
    """Factory so the router can close over the app's existing detector/ledger
    accessors without importing api_server (avoids a circular import). A FRESH
    APIRouter is created per call — a module-level singleton here would
    silently accumulate duplicate route registrations across repeated calls
    (e.g. once per test, or per app instance), and FastAPI resolves each path
    to whichever route was registered FIRST, serving a stale closure instead
    of the one just built. Each call must be fully independent."""
    router = APIRouter(tags=["monitoring"])

    @router.get("/health", summary="Liveness probe")
    async def health() -> dict:
        return {"status": "alive", "uptime_seconds": round(time.time() - _START_TIME, 1)}

    @router.get("/health/ready", summary="Readiness probe")
    async def ready(response: Response) -> dict:
        detector = get_detector_fn()
        ledger = get_ledger_fn()
        checks = {
            "model_loaded": detector is not None,
            "blockchain_available": ledger is not None,
        }
        ok = all(checks.values())
        if not ok:
            response.status_code = 503
        return {"status": "ready" if ok else "not_ready", "checks": checks}

    @router.get("/health/detailed", summary="Detailed system + dependency status")
    async def detailed(response: Response) -> dict:
        detector = get_detector_fn()
        ledger = get_ledger_fn()
        psutil = _safe_psutil()
        resources = {}
        if psutil:
            proc = psutil.Process()
            resources = {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_mb": round(proc.memory_info().rss / 1e6, 1),
                "memory_percent": round(psutil.virtual_memory().percent, 1),
            }
        model_status: dict = {"loaded": detector is not None}
        if detector is not None:
            model_status["avg_latency_ms"] = getattr(detector, "avg_latency_ms", lambda: None)()
        blockchain_status: dict = {"available": ledger is not None}
        if ledger is not None:
            try:
                valid, errors = ledger.validate()
                blockchain_status.update(valid=valid, blocks=len(ledger.chain), error_count=len(errors))
            except Exception as exc:
                blockchain_status.update(valid=False, error=str(exc))
        overall_ok = model_status["loaded"] and blockchain_status["available"]
        if not overall_ok:
            response.status_code = 503
        return {
            "status": "ok" if overall_ok else "degraded",
            "uptime_seconds": round(time.time() - _START_TIME, 1),
            "resources": resources,
            "model": model_status,
            "blockchain": blockchain_status,
            "prometheus_available": _PROM_AVAILABLE,
        }

    @router.get("/metrics", summary="Prometheus metrics")
    async def metrics() -> Response:
        detector = get_detector_fn(); ledger = get_ledger_fn()
        if _PROM_AVAILABLE:
            MODEL_LOADED.set(1 if detector is not None else 0)
            if ledger is not None:
                try:
                    BLOCKCHAIN_BLOCKS.set(len(ledger.chain))
                except Exception:
                    pass
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        # fallback: plain JSON if prometheus_client isn't installed
        import json
        return Response(json.dumps({
            "model_loaded": detector is not None,
            "blockchain_blocks": len(ledger.chain) if ledger is not None else 0,
            "note": "prometheus_client not installed; JSON fallback",
        }), media_type="application/json")

    return router
