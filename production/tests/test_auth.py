"""Unit + integration tests: password hashing, JWT issuance, RBAC enforcement."""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from production.security.auth import (
    hash_password, verify_password, authenticate_user, create_access_token,
    decode_token, require_role, User, ROLE_HIERARCHY,
)
from production.security.router import router as auth_router


# ── password hashing ──────────────────────────────────────────────────────────

def test_hash_and_verify_roundtrip():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong password", h)


def test_hash_truncates_long_password_safely():
    long_pw = "x" * 200
    h = hash_password(long_pw)
    assert verify_password(long_pw, h)   # doesn't raise on >72 bytes


def test_verify_password_malformed_hash_fails_closed():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


# ── real users.json ────────────────────────────────────────────────────────────

def test_authenticate_real_dev_users():
    for username, password in [
        ("admin", "ChangeMe-Admin-2026!"), ("operator", "ChangeMe-Operator-2026!"),
        ("analyst", "ChangeMe-Analyst-2026!"), ("viewer", "ChangeMe-Viewer-2026!"),
    ]:
        user = authenticate_user(username, password)
        assert user is not None, f"{username} failed to authenticate"


def test_authenticate_wrong_password_rejected():
    assert authenticate_user("admin", "wrong-password") is None


def test_authenticate_unknown_user_rejected():
    assert authenticate_user("nobody", "whatever") is None


# ── JWT ────────────────────────────────────────────────────────────────────────

def test_create_and_decode_token_roundtrip():
    user = User(username="admin", role="administrator")
    token = create_access_token(user)
    data = decode_token(token)
    assert data.username == "admin" and data.role == "administrator"


def test_decode_garbage_token_raises_401():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.valid.jwt")
    assert exc.value.status_code == 401


# ── role hierarchy ─────────────────────────────────────────────────────────────

def test_role_hierarchy_order():
    assert ROLE_HIERARCHY == ["viewer", "analyst", "grid_operator", "administrator"]


# ── RBAC enforcement via a tiny test app ──────────────────────────────────────

def _build_test_app():
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/protected/analyst")
    async def analyst_only(auth=Depends(require_role("analyst"))):
        return {"ok": True, "role": auth.role}

    @app.get("/protected/admin")
    async def admin_only(auth=Depends(require_role("administrator"))):
        return {"ok": True}

    return app


def _token_for(client, username, password):
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_rbac_no_token_is_401():
    client = TestClient(_build_test_app())
    r = client.get("/protected/analyst")
    assert r.status_code == 401


def test_rbac_insufficient_role_is_403():
    client = TestClient(_build_test_app())
    tok = _token_for(client, "viewer", "ChangeMe-Viewer-2026!")
    r = client.get("/protected/analyst", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_rbac_sufficient_role_is_200():
    client = TestClient(_build_test_app())
    tok = _token_for(client, "analyst", "ChangeMe-Analyst-2026!")
    r = client.get("/protected/analyst", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200


def test_rbac_higher_role_inherits_lower_permission():
    """administrator must also pass an analyst-level gate (hierarchy is additive)."""
    client = TestClient(_build_test_app())
    tok = _token_for(client, "admin", "ChangeMe-Admin-2026!")
    r = client.get("/protected/analyst", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200


def test_rbac_wrong_password_login_is_401():
    client = TestClient(_build_test_app())
    r = client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_whoami_reflects_token():
    client = TestClient(_build_test_app())
    tok = _token_for(client, "operator", "ChangeMe-Operator-2026!")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == {"username": "operator", "role": "grid_operator"}
