"""
production/security/auth.py — JWT authentication + role-based access control.

Four roles (per spec): administrator, grid_operator, analyst, viewer.
Permission model (least-privilege, additive):
  viewer        — read-only: status/health/alerts/dashboard data
  analyst       — + run detection (/api/detect), view model internals
  grid_operator — + simulate attacks, issue packet-tracer commands, grid control
  administrator — + reload model, modify configuration, manage users

User store is a JSON file (dev-appropriate; documented as a placeholder for a
real identity provider / DB-backed user table in production — see
production/docs/deployment_guide.md). Passwords are bcrypt-hashed, never
stored or logged in plaintext.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from production.config.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Role hierarchy: each role inherits the permissions of the ones before it.
ROLE_HIERARCHY = ["viewer", "analyst", "grid_operator", "administrator"]


class TokenData(BaseModel):
    username: str
    role: str


class User(BaseModel):
    username: str
    role: str
    full_name: str = ""


def hash_password(plain: str) -> str:
    # bcrypt has a hard 72-BYTE input limit; truncate defensively rather than
    # raising, since a user picking a long passphrase shouldn't hard-crash login.
    raw = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    raw = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(raw, hashed.encode("utf-8"))
    except ValueError:
        return False   # malformed hash in the user store -> fail closed, not 500


def _load_users() -> dict[str, dict]:
    path = Path(get_settings().users_file)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {u["username"]: u for u in data.get("users", [])}


def authenticate_user(username: str, password: str) -> User | None:
    users = _load_users()
    record = users.get(username)
    if record is None or not verify_password(password, record["password_hash"]):
        return None
    return User(username=record["username"], role=record["role"], full_name=record.get("full_name", ""))


def create_access_token(user: User) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user.username, "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenData:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                               detail="Invalid token payload")
        return TokenData(username=username, role=role)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="Invalid or expired token",
                           headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> TokenData:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return decode_token(token)


def require_role(minimum_role: str):
    """FastAPI dependency: allow access if the caller's role is >= minimum_role
    in ROLE_HIERARCHY (e.g. require_role("analyst") also admits grid_operator
    and administrator)."""
    if minimum_role not in ROLE_HIERARCHY:
        raise ValueError(f"Unknown role {minimum_role!r}")
    min_level = ROLE_HIERARCHY.index(minimum_role)

    async def _dependency(current: TokenData = Depends(get_current_user)) -> TokenData:
        if current.role not in ROLE_HIERARCHY:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role")
        if ROLE_HIERARCHY.index(current.role) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum_role}' or higher; caller has '{current.role}'")
        return current
    return _dependency
