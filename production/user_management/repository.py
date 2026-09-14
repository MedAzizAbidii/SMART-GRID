"""User management repository with in-memory storage (can be swapped for DB)."""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import bcrypt
from .models import User, UserCreateRequest, UserUpdateRequest, UserStatus, UserRole, APIKey, UserSession, UserPreferences


class UserRepository:
    """In-memory user repository. Swap with SQLAlchemy for production DB."""

    def __init__(self):
        self._users: dict[str, dict] = {}
        self._sessions: dict[str, dict] = {}
        self._api_keys: dict[str, dict] = {}
        self._preferences: dict[str, dict] = {}
        self._failed_logins: dict[str, int] = {}
        self._init_default_admin()

    def _init_default_admin(self):
        """Initialize default admin if none exists."""
        if not self._users:
            admin_id = str(uuid.uuid4())
            hashed = bcrypt.hashpw(b"Admin@12345!", bcrypt.gensalt())
            self._users[admin_id] = {
                "id": admin_id,
                "username": "admin",
                "email": "admin@smartgrid.local",
                "password_hash": hashed,
                "role": UserRole.ADMIN,
                "status": UserStatus.ACTIVE,
                "organization": "System",
                "created_at": datetime.utcnow(),
                "last_login": None,
                "mfa_enabled": False,
                "is_service_account": False,
            }
            self._preferences[admin_id] = {
                "user_id": admin_id,
                "theme": "dark",
                "language": "en",
                "notifications_enabled": True,
                "notification_channels": ["push"],
                "dashboard_widgets": [],
            }

    def create_user(self, req: UserCreateRequest) -> User:
        """Create new user with password hashing."""
        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt())

        if any(u["username"] == req.username for u in self._users.values()):
            raise ValueError("Username already exists")
        if any(u["email"] == req.email for u in self._users.values()):
            raise ValueError("Email already exists")

        self._users[user_id] = {
            "id": user_id,
            "username": req.username,
            "email": req.email,
            "password_hash": hashed,
            "role": req.role,
            "status": UserStatus.ACTIVE,
            "organization": req.organization,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "mfa_enabled": req.mfa_enabled,
            "is_service_account": False,
        }
        self._preferences[user_id] = {
            "user_id": user_id,
            "theme": "dark",
            "language": "en",
            "notifications_enabled": True,
            "notification_channels": ["push"],
            "dashboard_widgets": [],
        }
        return self._to_user(self._users[user_id])

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        if user_id in self._users:
            return self._to_user(self._users[user_id])
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user["username"] == username:
                return self._to_user(user)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user["email"] == email:
                return self._to_user(user)
        return None

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        users_list = list(self._users.values())
        return [self._to_user(u) for u in users_list[skip : skip + limit]]

    def update_user(self, user_id: str, req: UserUpdateRequest) -> Optional[User]:
        if user_id not in self._users:
            return None
        user = self._users[user_id]
        if req.email:
            user["email"] = req.email
        if req.role:
            user["role"] = req.role
        if req.status:
            user["status"] = req.status
        if req.mfa_enabled is not None:
            user["mfa_enabled"] = req.mfa_enabled
        return self._to_user(user)

    def delete_user(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            if user_id in self._preferences:
                del self._preferences[user_id]
            return True
        return False

    def verify_password(self, user_id: str, password: str) -> bool:
        if user_id not in self._users:
            return False
        user = self._users[user_id]
        if user["status"] == UserStatus.LOCKED:
            return False
        is_valid = bcrypt.checkpw(password.encode(), user["password_hash"])
        if is_valid:
            self._failed_logins[user_id] = 0
            user["last_login"] = datetime.utcnow()
        else:
            self._failed_logins[user_id] = self._failed_logins.get(user_id, 0) + 1
            if self._failed_logins[user_id] >= 5:
                user["status"] = UserStatus.LOCKED
        return is_valid

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        if not self.verify_password(user_id, old_password):
            return False
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        self._users[user_id]["password_hash"] = hashed
        return True

    def unlock_user(self, user_id: str) -> bool:
        if user_id in self._users:
            self._users[user_id]["status"] = UserStatus.ACTIVE
            self._failed_logins[user_id] = 0
            return True
        return False

    def create_session(self, user_id: str, device_id: str, ip_address: str, user_agent: str) -> UserSession:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        self._sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": now,
            "last_active": now,
            "expires_at": now + timedelta(days=7),
            "is_active": True,
        }
        return UserSession(**self._sessions[session_id])

    def get_session(self, session_id: str) -> Optional[UserSession]:
        if session_id in self._sessions:
            sess = self._sessions[session_id]
            if sess["is_active"] and datetime.fromisoformat(sess["expires_at"].isoformat()) > datetime.utcnow():
                return UserSession(**sess)
        return None

    def invalidate_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id]["is_active"] = False
            return True
        return False

    def create_api_key(self, user_id: str, name: str, expires_in_days: Optional[int] = None) -> APIKey:
        key_id = str(uuid.uuid4())
        prefix = f"sgrid_{user_id[:8]}"
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        self._api_keys[key_id] = {
            "id": key_id,
            "user_id": user_id,
            "name": name,
            "prefix": prefix,
            "last_used": None,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "is_active": True,
        }
        return APIKey(**self._api_keys[key_id])

    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        if user_id in self._preferences:
            return UserPreferences(**self._preferences[user_id])
        return None

    def update_preferences(self, user_id: str, **kwargs) -> Optional[UserPreferences]:
        if user_id not in self._preferences:
            return None
        self._preferences[user_id].update(kwargs)
        return UserPreferences(**self._preferences[user_id])

    def _to_user(self, user_data: dict) -> User:
        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            role=user_data["role"],
            status=user_data["status"],
            organization=user_data["organization"],
            created_at=user_data["created_at"],
            last_login=user_data.get("last_login"),
            mfa_enabled=user_data.get("mfa_enabled", False),
            is_service_account=user_data.get("is_service_account", False),
        )
