"""User API router for managing user profiles and preferences."""

import uuid
import logging
from fastapi import APIRouter, HTTPException
from pydantic import EmailStr

from users.schemas import (
    UserCreate, UserUpdate, UserResponse,
    NotificationTime, MarketType
)
from users.service import get_user_service
from users.email_service import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
async def create_user(request: UserCreate) -> UserResponse:
    """
    Create a new user profile.

    Args:
        request: User creation request with email and optional preferences.

    Returns:
        Created user profile.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[TRACE={trace_id}] Creating user: email={request.email}")

    user_service = get_user_service()
    user = user_service.create_user(request)

    logger.info(f"[TRACE={trace_id}] User created: user_id={user.user_id}")
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """
    Get user profile by ID.

    Args:
        user_id: User identifier.

    Returns:
        User profile.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.debug(f"[TRACE={trace_id}] Getting user: user_id={user_id}")

    user_service = get_user_service()
    user = user_service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str) -> UserResponse:
    """
    Get user profile by email address.

    Args:
        email: User email address.

    Returns:
        User profile.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.debug(f"[TRACE={trace_id}] Getting user by email: {email}")

    user_service = get_user_service()
    user = user_service.get_user_by_email(email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, request: UserUpdate) -> UserResponse:
    """
    Update user profile.

    Args:
        user_id: User identifier.
        request: Update request with fields to update.

    Returns:
        Updated user profile.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[TRACE={trace_id}] Updating user: user_id={user_id}")

    user_service = get_user_service()
    user = user_service.update_user(user_id, request)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"[TRACE={trace_id}] User updated: user_id={user_id}")
    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(user_id: str) -> dict:
    """
    Delete a user profile.

    Args:
        user_id: User identifier.

    Returns:
        Success message.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[TRACE={trace_id}] Deleting user: user_id={user_id}")

    user_service = get_user_service()
    success = user_service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"[TRACE={trace_id}] User deleted: user_id={user_id}")
    return {"message": "User deleted successfully", "user_id": user_id}


@router.get("/")
async def list_users(limit: int = 100, offset: int = 0) -> dict:
    """
    List all users.

    Args:
        limit: Maximum number of users to return.
        offset: Number of users to skip.

    Returns:
        List of users.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.debug(f"[TRACE={trace_id}] Listing users: limit={limit}, offset={offset}")

    user_service = get_user_service()
    users = user_service.list_users(limit=limit, offset=offset)

    return {
        "total": len(users),
        "users": [UserResponse.model_validate(u).model_dump() for u in users]
    }


@router.post("/{user_id}/preferences")
async def update_preferences(
    user_id: str,
    watched_industries: list[str] = None,
    watched_stocks: list[str] = None,
    preferred_markets: list[MarketType] = None,
    notification_time: NotificationTime = None,
    email_enabled: bool = None
) -> UserResponse:
    """
    Update user's preference settings.

    Args:
        user_id: User identifier.
        watched_industries: List of industries to watch.
        watched_stocks: List of stock symbols to watch.
        preferred_markets: Preferred stock markets.
        notification_time: When to send notifications.
        email_enabled: Whether to enable email notifications.

    Returns:
        Updated user profile.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[TRACE={trace_id}] Updating preferences: user_id={user_id}")

    user_service = get_user_service()
    user = user_service.update_preferences(
        user_id=user_id,
        watched_industries=watched_industries,
        watched_stocks=watched_stocks,
        preferred_markets=preferred_markets,
        notification_time=notification_time,
        email_enabled=email_enabled
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"[TRACE={trace_id}] Preferences updated: user_id={user_id}")
    return UserResponse.model_validate(user)


@router.post("/{user_id}/test-email")
async def send_test_email(user_id: str) -> dict:
    """
    Send a test email to the user.

    Args:
        user_id: User identifier.

    Returns:
        Success message.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[TRACE={trace_id}] Sending test email: user_id={user_id}")

    user_service = get_user_service()
    user = user_service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email_service = get_email_service()
    success = email_service.send_daily_report(user)

    if success:
        logger.info(f"[TRACE={trace_id}] Test email sent: user_id={user_id}")
        return {"message": "Test email sent successfully"}
    else:
        logger.warning(f"[TRACE={trace_id}] Failed to send test email: user_id={user_id}")
        raise HTTPException(status_code=500, detail="Failed to send test email")


@router.get("/industry/{industry}")
async def get_users_by_industry(industry: str) -> dict:
    """
    Get all users watching a specific industry.

    Args:
        industry: Industry name.

    Returns:
        List of users watching this industry.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.debug(f"[TRACE={trace_id}] Finding users by industry: {industry}")

    user_service = get_user_service()
    users = user_service.get_users_by_industry(industry)

    return {
        "industry": industry,
        "count": len(users),
        "users": [UserResponse.model_validate(u).model_dump() for u in users]
    }


@router.get("/stock/{symbol}")
async def get_users_by_stock(symbol: str) -> dict:
    """
    Get all users watching a specific stock.

    Args:
        symbol: Stock symbol.

    Returns:
        List of users watching this stock.
    """
    trace_id = str(uuid.uuid4())[:8]
    logger.debug(f"[TRACE={trace_id}] Finding users by stock: {symbol}")

    user_service = get_user_service()
    users = user_service.get_users_by_stock(symbol)

    return {
        "symbol": symbol,
        "count": len(users),
        "users": [UserResponse.model_validate(u).model_dump() for u in users]
    }