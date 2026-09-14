"""User management domain models and database schemas."""
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator


class UserRole(str, Enum):
    ADMIN = "administrator"
    OPERATOR = "grid_operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class User(BaseModel):
    id: str
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    organization: str
    created_at: datetime
    last_login: Optional[datetime] = None
    mfa_enabled: bool = False
    is_service_account: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=12)
    role: UserRole = UserRole.VIEWER
    organization: str = Field(min_length=1, max_length=128)
    mfa_enabled: bool = False

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain special character")
        return v


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    mfa_enabled: Optional[bool] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=12)

    @validator("new_password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain special character")
        return v


class APIKey(BaseModel):
    id: str
    user_id: str
    name: str
    prefix: str
    last_used: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    expires_in_days: Optional[int] = None


class UserPreferences(BaseModel):
    user_id: str
    theme: str = "dark"  # dark, light, auto
    language: str = "en"
    notifications_enabled: bool = True
    notification_channels: list[str] = ["push", "email"]
    dashboard_widgets: list[str] = []

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserSession(BaseModel):
    id: str
    user_id: str
    device_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_active: datetime
    expires_at: datetime
    is_active: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
