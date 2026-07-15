"""
End-to-end workflow tests against the REAL api_server app (in-process,
TestClient — no network/Docker required). Validates the actual integration:
config -> logging -> auth -> RBAC -> detection -> blockchain, all wired
together exactly as they run in production, catching regressions that
component-level tests can't see (e.g. import ordering, dependency wiring).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

import api_server


@pytest.fixture(scope="module")
def client():
    with TestClient(api_server.app) as c:
        yield c


def test_dashboard_still_serves_unauthenticated(client):
    """Regression guard: the existing dashboard must keep working exactly as
    before Phase 6 — no auth requirement was added to read-mostly routes."""
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert b"<html" in r.content.lower() or b"<!doctype" in r.content.lower()


def test_detect_endpoint_still_open_no_regression(client):
    r = client.post("/api/detect", json={
        "meter_id": "SM_0001", "zone": "Zone A", "type": "industriel",
        "consommation_kw": 14.0, "tension_v": 227.0, "courant_a": 62.0,
        "power_factor": 0.9, "frequency_hz": 60.0,
    })
    assert r.status_code == 200
    assert "is_anomaly" in r.json()


def test_blockchain_status_open_no_regression(client):
    r = client.get("/api/blockchain/status")
    assert r.status_code == 200


def test_health_endpoints_present(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").status_code in (200, 503)
    assert client.get("/health/detailed").status_code in (200, 503)


def test_metrics_endpoint_present(client):
    assert client.get("/metrics").status_code == 200


def test_login_then_protected_endpoint_full_flow(client):
    login = client.post("/api/auth/login", data={
        "username": "analyst", "password": "ChangeMe-Analyst-2026!"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    r = client.post("/api/simulate/attack", params={"bus_id": 2, "attack_type": "dos"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_protected_endpoint_rejects_unauthenticated(client):
    r = client.post("/api/simulate/attack", params={"bus_id": 2, "attack_type": "dos"})
    assert r.status_code == 401


def test_protected_endpoint_rejects_insufficient_role(client):
    login = client.post("/api/auth/login", data={
        "username": "viewer", "password": "ChangeMe-Viewer-2026!"})
    token = login.json()["access_token"]
    r = client.post("/api/simulate/attack", params={"bus_id": 2, "attack_type": "dos"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_invalid_detection_payload_returns_422_not_500(client):
    r = client.post("/api/detect", json={"meter_id": "SM_0001"})   # missing required fields
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"
    assert "request_id" in body


def test_every_response_has_request_id_header(client):
    r = client.get("/health")
    assert "x-request-id" in r.headers


def test_model_status_endpoint(client):
    r = client.get("/api/model/status")
    assert r.status_code == 200


def test_openapi_schema_generates(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "/api/auth/login" in schema["paths"]
    assert "/health" in schema["paths"]
