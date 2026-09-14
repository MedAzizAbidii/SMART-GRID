"""production/security/user_store.py — CRUD on the JSON user store.

Replaces manual editing of users.json with a real API (see router.py's
/api/auth/users endpoints). Still a JSON file, not a database — that
tradeoff is unchanged and documented in deployment_guide.md as a known
limitation for a real deployment — but administrators no longer need
filesystem access or to hand-craft bcrypt hashes to manage accounts.

Concurrency: a single process-wide lock serializes writes (mirrors the
existing single-process in-memory state pattern already used by the
rate limiter and PoA ledger). Writes are atomic (write to a temp file,
then os.replace) so a crash mid-write can never corrupt the store.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from production.config.settings import get_settings
from production.security.auth import ROLE_HIERARCHY, User, hash_password, verify_password

_write_lock = threading.Lock()

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    full_name: str = ""

    @field_validator("username")
    @classmethod
    def _valid_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("username must be 3-32 chars: letters, digits, underscore, dot, hyphen")
        return v

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        if v not in ROLE_HIERARCHY:
            raise ValueError(f"role must be one of {ROLE_HIERARCHY}")
        return v

    @field_validator("password")
    @classmethod
    def _valid_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    role: str | None = None
    full_name: str | None = None

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ROLE_HIERARCHY:
            raise ValueError(f"role must be one of {ROLE_HIERARCHY}")
        return v


class PasswordChange(BaseModel):
    new_password: str = Field(min_length=8)


class UserStoreError(ValueError):
    """Raised for user-facing store errors (duplicate username, unknown
    user, last-administrator protection). Router maps this to 400/404/409."""


def _store_path() -> Path:
    return Path(get_settings().users_file)


def _read_raw() -> dict:
    path = _store_path()
    if not path.exists():
        return {"_comment": "Smart Grid user store — managed via /api/auth/users", "users": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_raw(data: dict) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)  # atomic on both POSIX and Windows


def _to_public(record: dict) -> User:
    return User(username=record["username"], role=record["role"], full_name=record.get("full_name", ""))


def list_users() -> list[User]:
    data = _read_raw()
    return [_to_public(u) for u in data.get("users", [])]


def create_user(payload: UserCreate) -> User:
    with _write_lock:
        data = _read_raw()
        users = data.setdefault("users", [])
        if any(u["username"] == payload.username for u in users):
            raise UserStoreError(f"username '{payload.username}' already exists")
        users.append({
            "username": payload.username,
            "password_hash": hash_password(payload.password),
            "role": payload.role,
            "full_name": payload.full_name,
        })
        _write_raw(data)
        return User(username=payload.username, role=payload.role, full_name=payload.full_name)


def update_user(username: str, payload: UserUpdate) -> User:
    with _write_lock:
        data = _read_raw()
        users = data.get("users", [])
        record = next((u for u in users if u["username"] == username), None)
        if record is None:
            raise UserStoreError(f"user '{username}' not found")

        if payload.role is not None and payload.role != record["role"]:
            _assert_not_last_administrator(users, username, action="demote")
            record["role"] = payload.role
        if payload.full_name is not None:
            record["full_name"] = payload.full_name

        _write_raw(data)
        return _to_public(record)


def delete_user(username: str) -> None:
    with _write_lock:
        data = _read_raw()
        users = data.get("users", [])
        record = next((u for u in users if u["username"] == username), None)
        if record is None:
            raise UserStoreError(f"user '{username}' not found")

        _assert_not_last_administrator(users, username, action="delete")
        data["users"] = [u for u in users if u["username"] != username]
        _write_raw(data)


def reset_password(username: str, new_password: str) -> None:
    with _write_lock:
        data = _read_raw()
        users = data.get("users", [])
        record = next((u for u in users if u["username"] == username), None)
        if record is None:
            raise UserStoreError(f"user '{username}' not found")
        record["password_hash"] = hash_password(new_password)
        _write_raw(data)


def change_own_password(username: str, current_password: str, new_password: str) -> None:
    with _write_lock:
        data = _read_raw()
        users = data.get("users", [])
        record = next((u for u in users if u["username"] == username), None)
        if record is None:
            raise UserStoreError(f"user '{username}' not found")
        if not verify_password(current_password, record["password_hash"]):
            raise UserStoreError("current password is incorrect")
        record["password_hash"] = hash_password(new_password)
        _write_raw(data)


def _assert_not_last_administrator(users: list[dict], username: str, action: str) -> None:
    """Refuses to demote/delete the only remaining administrator — the
    store would otherwise lock every operator out of user management
    with no way back in short of hand-editing the JSON file again,
    defeating the point of this module."""
    target = next((u for u in users if u["username"] == username), None)
    if target is None or target["role"] != "administrator":
        return
    other_admins = [u for u in users if u["role"] == "administrator" and u["username"] != username]
    if not other_admins:
        raise UserStoreError(f"cannot {action} '{username}': at least one administrator must remain")
