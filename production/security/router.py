"""production/security/router.py — /api/auth/* endpoints (login, whoami,
user management)."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from production.security.auth import authenticate_user, create_access_token, get_current_user, require_role, TokenData, User
from production.security.user_store import (
    PasswordChange, UserCreate, UserStoreError, UserUpdate,
    change_own_password, create_user, delete_user, list_users, reset_password, update_user,
)

# Firebase Cloud Messaging (FREE tier)
try:
    from firebase_admin import messaging
    _FIREBASE_AVAILABLE = True
except ImportError:
    _FIREBASE_AVAILABLE = False
    messaging = None

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class PasswordChangeSelf(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class FCMTokenRequest(BaseModel):
    token: str
    device_name: str | None = None


class PushNotificationRequest(BaseModel):
    title: str
    body: str
    alert_id: int | None = None
    severity: str = "info"
    data: Dict[str, Any] | None = None


@router.post("/login", response_model=TokenResponse,
            summary="Obtain a JWT access token",
            responses={401: {"description": "Invalid username or password"}})
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = authenticate_user(form.username, form.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="Invalid username or password",
                           headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token(user)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", summary="Current authenticated user")
async def whoami(current: TokenData = Depends(get_current_user)) -> dict:
    return {"username": current.username, "role": current.role}


@router.post("/change-password", summary="Change your own password")
async def change_password(payload: PasswordChangeSelf, current: TokenData = Depends(get_current_user)) -> dict:
    try:
        change_own_password(current.username, payload.current_password, payload.new_password)
    except UserStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"changed": True}


# ---------------------------------------------------------------------------
# User management (administrator-only) — replaces manual users.json editing.
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[User], summary="List all users")
async def list_all_users(_auth: TokenData = Depends(require_role("administrator"))) -> list[User]:
    return list_users()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED, summary="Create a user")
async def create_new_user(payload: UserCreate, _auth: TokenData = Depends(require_role("administrator"))) -> User:
    try:
        return create_user(payload)
    except UserStoreError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/users/{username}", response_model=User, summary="Update a user's role or name")
async def update_existing_user(
    username: str, payload: UserUpdate, _auth: TokenData = Depends(require_role("administrator"))
) -> User:
    try:
        return update_user(username, payload)
    except UserStoreError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc))


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user")
async def delete_existing_user(username: str, current: TokenData = Depends(require_role("administrator"))) -> None:
    if username == current.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot delete your own account")
    try:
        delete_user(username)
    except UserStoreError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc))


@router.post("/users/{username}/reset-password", summary="Administrator-issued password reset")
async def reset_user_password(
    username: str, payload: PasswordChange, _auth: TokenData = Depends(require_role("administrator"))
) -> dict:
    try:
        reset_password(username, payload.new_password)
    except UserStoreError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc))
    return {"reset": True}


# ── Push Notifications (Firebase Cloud Messaging - FREE tier) ────────────

@router.post("/fcm-register", summary="Register FCM token for push notifications")
async def register_fcm_token(
    request: FCMTokenRequest,
    current: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    """Register FCM token for push notifications (FREE Firebase tier: 1M messages/month)"""
    try:
        fcm_tokens_file = "data/fcm_tokens.json"
        os.makedirs("data", exist_ok=True)

        tokens = {}
        if os.path.exists(fcm_tokens_file):
            with open(fcm_tokens_file) as f:
                tokens = json.load(f)

        # Store token with user info
        tokens[request.token] = {
            "username": current.username,
            "device_name": request.device_name or "Unknown",
            "registered_at": time.time(),
            "active": True
        }

        with open(fcm_tokens_file, "w") as f:
            json.dump(tokens, f, indent=2)

        return {
            "status": "registered",
            "token_count": len(tokens),
            "message": "Push notifications enabled for this device"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/send-notification", summary="Send push notification to all users")
async def send_push_notification(
    request: PushNotificationRequest,
    _auth: TokenData = Depends(require_role("grid_operator"))
) -> Dict[str, Any]:
    """Send push notification to all subscribed users (FREE Firebase tier)"""

    if not _FIREBASE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase not initialized"
        )

    try:
        # Create FCM message
        message = messaging.Message(
            notification=messaging.Notification(
                title=request.title,
                body=request.body,
            ),
            data={
                "alert_id": str(request.alert_id or 0),
                "severity": request.severity,
                "timestamp": str(int(time.time())),
                **(request.data or {})
            },
            topic="alerts",  # Send to all users subscribed to "alerts" topic
        )

        response = messaging.send(message)

        return {
            "status": "sent",
            "message_id": response,
            "title": request.title,
            "recipients": "all subscribed to alerts topic",
            "timestamp": time.time()
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
