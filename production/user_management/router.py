"""User management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from typing import Optional
from .models import (
    User, UserCreateRequest, UserUpdateRequest, PasswordChangeRequest,
    UserPreferences, APIKeyCreateRequest, UserRole
)
from .service import UserService
from ..security.auth import require_role, get_current_user


router = APIRouter(prefix="/api/users", tags=["users"])
_service = UserService()


@router.post("/register", response_model=User, status_code=201)
async def register(req: UserCreateRequest):
    """Public registration endpoint."""
    try:
        user = _service.register_user(req)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(
    username: str = Body(...),
    password: str = Body(...),
    device_id: str = Body(...),
    x_forwarded_for: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
):
    """Authenticate user and return session."""
    ip_address = x_forwarded_for or "unknown"
    user_agent = user_agent or "unknown"

    try:
        user, session = _service.authenticate(username, password, device_id, ip_address, user_agent)
        if not user or not session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "user": user,
            "session_id": session.id,
            "expires_at": session.expires_at.isoformat(),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/logout")
async def logout(session_id: str = Header(...)):
    """Logout user (invalidate session)."""
    if _service.invalidate_session(session_id):
        return {"message": "Logged out"}
    raise HTTPException(status_code=400, detail="Invalid session")


@router.get("/me", response_model=User)
async def get_current(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return user


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, _: User = Depends(require_role(UserRole.ANALYST))):
    """Get user by ID (analysts+)."""
    user = _service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_role(UserRole.OPERATOR)),
):
    """List users (operators+)."""
    return _service.list_users(skip, limit)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    req: UserUpdateRequest,
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update user (admins only)."""
    user = _service.update_user(user_id, req)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete user (admins only)."""
    if not _service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.post("/{user_id}/change-password")
async def change_password(
    user_id: str,
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
):
    """Change password (self or admin)."""
    if current_user.id != user_id and current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Forbidden")
    if not _service.change_password(user_id, req.old_password, req.new_password):
        raise HTTPException(status_code=400, detail="Invalid old password")
    return {"message": "Password changed"}


@router.post("/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Unlock locked user (admins only)."""
    if not _service.unlock_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User unlocked"}


@router.get("/{user_id}/preferences", response_model=UserPreferences)
async def get_preferences(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get user preferences (self only)."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    prefs = _service.get_preferences(user_id)
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.put("/{user_id}/preferences", response_model=UserPreferences)
async def update_preferences(
    user_id: str,
    theme: Optional[str] = None,
    language: Optional[str] = None,
    notifications_enabled: Optional[bool] = None,
    notification_channels: Optional[list[str]] = None,
    current_user: User = Depends(get_current_user),
):
    """Update user preferences (self only)."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    kwargs = {}
    if theme:
        kwargs["theme"] = theme
    if language:
        kwargs["language"] = language
    if notifications_enabled is not None:
        kwargs["notifications_enabled"] = notifications_enabled
    if notification_channels:
        kwargs["notification_channels"] = notification_channels
    prefs = _service.update_preferences(user_id, **kwargs)
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.post("/{user_id}/api-keys", response_model=dict)
async def create_api_key(
    user_id: str,
    req: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create API key for user (self or admin)."""
    if current_user.id != user_id and current_user.role != "administrator":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        key = _service.create_api_key(user_id, req)
        return {
            "id": key.id,
            "name": key.name,
            "prefix": key.prefix,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
