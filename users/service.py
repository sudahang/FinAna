"""User service for managing user profiles and preferences."""

import json
import uuid
import hashlib
import logging
from typing import Optional, List
from datetime import datetime

from users.schemas import (
    UserProfile, UserCreate, UserUpdate, UserPreference,
    NotificationTime, MarketType
)
from storage.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class UserService:
    """Service for user profile management using Redis."""

    USER_KEY_PREFIX = "user:"
    USER_INDEX_KEY = "user:index:email"

    def __init__(self, redis_client=None):
        """Initialize user service."""
        self.redis = redis_client or get_redis_client()

    def _get_user_key(self, user_id: str) -> str:
        """Get Redis key for user."""
        return f"{self.USER_KEY_PREFIX}{user_id}"

    def _get_email_index_key(self) -> str:
        """Get Redis key for email index."""
        return self.USER_INDEX_KEY

    def _generate_user_id(self, email: str) -> str:
        """Generate unique user ID from email."""
        return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

    def create_user(self, user_data: UserCreate) -> UserProfile:
        """Create a new user profile."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Creating user: email={user_data.email}")

        user_id = self._generate_user_id(user_data.email)

        user_profile = UserProfile(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            preferences=user_data.preferences or UserPreference(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True
        )

        user_key = self._get_user_key(user_id)
        self.redis.client.set(
            user_key,
            user_profile.model_dump_json(),
            ex=None
        )

        email_index_key = self._get_email_index_key()
        self.redis.client.hset(email_index_key, user_data.email.lower(), user_id)

        logger.info(f"[TRACE={trace_id}] User created: user_id={user_id}")
        return user_profile

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.debug(f"[TRACE={trace_id}] Getting user: user_id={user_id}")

        user_key = self._get_user_key(user_id)
        data = self.redis.client.get(user_key)

        if not data:
            logger.debug(f"[TRACE={trace_id}] User not found: user_id={user_id}")
            return None

        return UserProfile.model_validate_json(data)

    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.debug(f"[TRACE={trace_id}] Getting user by email: email={email}")

        email_index_key = self._get_email_index_key()
        user_id = self.redis.client.hget(email_index_key, email.lower())

        if not user_id:
            logger.debug(f"[TRACE={trace_id}] Email not found in index: {email}")
            return None

        return self.get_user(user_id)

    def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[UserProfile]:
        """Update user profile."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Updating user: user_id={user_id}")

        user = self.get_user(user_id)
        if not user:
            logger.warning(f"[TRACE={trace_id}] User not found for update: user_id={user_id}")
            return None

        if update_data.name is not None:
            user.name = update_data.name

        if update_data.preferences is not None:
            user.preferences = update_data.preferences

        if update_data.is_active is not None:
            user.is_active = update_data.is_active

        user.updated_at = datetime.now()

        user_key = self._get_user_key(user_id)
        self.redis.client.set(user_key, user.model_dump_json())

        logger.info(f"[TRACE={trace_id}] User updated: user_id={user_id}")
        return user

    def delete_user(self, user_id: str) -> bool:
        """Delete user profile."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Deleting user: user_id={user_id}")

        user = self.get_user(user_id)
        if not user:
            return False

        user_key = self._get_user_key(user_id)
        self.redis.client.delete(user_key)

        email_index_key = self._get_email_index_key()
        self.redis.client.hdel(email_index_key, user.email.lower())

        logger.info(f"[TRACE={trace_id}] User deleted: user_id={user_id}")
        return True

    def list_users(self, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """List all users."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.debug(f"[TRACE={trace_id}] Listing users: limit={limit}, offset={offset}")

        users = []
        email_index_key = self._get_email_index_key()

        all_emails = self.redis.client.hkeys(email_index_key)

        for i, email in enumerate(all_emails):
            if i < offset:
                continue
            if i >= offset + limit:
                break

            user = self.get_user_by_email(email)
            if user:
                users.append(user)

        return users

    def update_preferences(
        self,
        user_id: str,
        watched_industries: Optional[List[str]] = None,
        watched_stocks: Optional[List[str]] = None,
        preferred_markets: Optional[List[MarketType]] = None,
        notification_time: Optional[NotificationTime] = None,
        email_enabled: Optional[bool] = None
    ) -> Optional[UserProfile]:
        """Update specific preference fields."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Updating preferences: user_id={user_id}")

        user = self.get_user(user_id)
        if not user:
            return None

        prefs = user.preferences

        if watched_industries is not None:
            prefs.watched_industries = watched_industries

        if watched_stocks is not None:
            prefs.watched_stocks = watched_stocks

        if preferred_markets is not None:
            prefs.preferred_markets = preferred_markets

        if notification_time is not None:
            prefs.notification_time = notification_time

        if email_enabled is not None:
            prefs.email_enabled = email_enabled

        user.preferences = prefs
        user.updated_at = datetime.now()

        user_key = self._get_user_key(user_id)
        self.redis.client.set(user_key, user.model_dump_json())

        logger.info(f"[TRACE={trace_id}] Preferences updated: user_id={user_id}")
        return user

    def get_users_by_industry(self, industry: str) -> List[UserProfile]:
        """Get all users watching a specific industry."""
        all_users = self.list_users(limit=1000)
        return [
            user for user in all_users
            if industry in user.preferences.watched_industries
        ]

    def get_users_by_stock(self, symbol: str) -> List[UserProfile]:
        """Get all users watching a specific stock."""
        all_users = self.list_users(limit=1000)
        symbol_upper = symbol.upper()
        return [
            user for user in all_users
            if any(s.upper() == symbol_upper for s in user.preferences.watched_stocks)
        ]


_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get singleton user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service