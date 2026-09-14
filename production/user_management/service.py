"""User management business logic service."""
from typing import Optional, List
from datetime import datetime
from .models import (
    User, UserCreateRequest, UserUpdateRequest, PasswordChangeRequest,
    UserPreferences, UserSession, APIKey, APIKeyCreateRequest, UserStatus
)
from .repository import UserRepository


class UserService:
    """High-level user management service."""

    def __init__(self, repository: Optional[UserRepository] = None):
        self.repo = repository or UserRepository()

    def register_user(self, req: UserCreateRequest) -> User:
        """Register new user with validation."""
        if len(req.password) < 12:
            raise ValueError("Password too short")
        try:
            return self.repo.create_user(req)
        except ValueError as e:
            raise ValueError(str(e))

    def authenticate(
        self, username: str, password: str, device_id: str, ip_address: str, user_agent: str
    ) -> tuple[Optional[User], Optional[UserSession]]:
        """Authenticate user and create session."""
        user = self.repo.get_user_by_username(username)
        if not user:
            return None, None

        if user.status == UserStatus.LOCKED:
            raise PermissionError(f"User {username} is locked")

        if not self.repo.verify_password(user.id, password):
            return None, None

        session = self.repo.create_session(user.id, device_id, ip_address, user_agent)
        return user, session

    def get_user(self, user_id: str) -> Optional[User]:
        return self.repo.get_user_by_id(user_id)

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.repo.list_users(skip, limit)

    def update_user(self, user_id: str, req: UserUpdateRequest) -> Optional[User]:
        """Update user details (admin operation)."""
        return self.repo.update_user(user_id, req)

    def change_password(self, user_id: str, req: PasswordChangeRequest) -> bool:
        return self.repo.change_password(user_id, req.old_password, req.new_password)

    def delete_user(self, user_id: str) -> bool:
        return self.repo.delete_user(user_id)

    def unlock_user(self, user_id: str) -> bool:
        """Unlock a locked user account."""
        return self.repo.unlock_user(user_id)

    def validate_session(self, session_id: str) -> Optional[User]:
        """Validate session and return associated user."""
        session = self.repo.get_session(session_id)
        if not session:
            return None
        return self.repo.get_user_by_id(session.user_id)

    def invalidate_session(self, session_id: str) -> bool:
        return self.repo.invalidate_session(session_id)

    def create_api_key(self, user_id: str, req: APIKeyCreateRequest) -> APIKey:
        """Create API key for user."""
        return self.repo.create_api_key(user_id, req.name, req.expires_in_days)

    def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        return self.repo.get_user_preferences(user_id)

    def update_preferences(self, user_id: str, **kwargs) -> Optional[UserPreferences]:
        return self.repo.update_preferences(user_id, **kwargs)
