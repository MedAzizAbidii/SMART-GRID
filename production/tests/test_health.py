"""Unit tests: health/readiness/metrics router."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from production.monitoring.health import build_health_router


class _FakeDetector:
    def avg_latency_ms(self): return 12.3


class _FakeLedger:
    chain = [1, 2, 3]
    def validate(self): return True, []


def _app(detector=None, ledger=None):
    app = FastAPI()
    app.include_router(build_health_router(lambda: detector, lambda: ledger))
    return app


def test_health_always_ok():
    client = TestClient(_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_ready_fails_without_model():
    client = TestClient(_app(detector=None, ledger=_FakeLedger()))
    r = client.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["checks"]["model_loaded"] is False


def test_ready_ok_with_both_dependencies():
    client = TestClient(_app(detector=_FakeDetector(), ledger=_FakeLedger()))
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_detailed_reports_resource_usage():
    client = TestClient(_app(detector=_FakeDetector(), ledger=_FakeLedger()))
    r = client.get("/health/detailed")
    assert r.status_code == 200
    body = r.json()
    assert body["model"]["loaded"] is True
    assert body["blockchain"]["blocks"] == 3
    assert "memory_mb" in body["resources"]


def test_metrics_endpoint_serves_prometheus_or_json():
    client = TestClient(_app(detector=_FakeDetector(), ledger=_FakeLedger()))
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(("text/plain", "application/json"))
