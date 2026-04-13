"""User models for personalized investment research."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class NotificationTime(str, Enum):
    """Notification time preference."""
    MORNING = "08:00"
    EVENING = "20:00"
    BOTH = "both"


class MarketType(str, Enum):
    """Stock market type."""
    A_STOCK = "a_stock"      # A股 (沪深)
    HK_STOCK = "hk_stock"    # 港股
    US_STOCK = "us_stock"    # 美股
    ALL = "all"


class UserPreference(BaseModel):
    """User's investment preference settings."""

    watched_industries: List[str] = Field(
        default_factory=list,
        description="List of industries user is interested in"
    )
    watched_stocks: List[str] = Field(
        default_factory=list,
        description="List of stock symbols user follows"
    )
    preferred_markets: List[MarketType] = Field(
        default_factory=lambda: [MarketType.ALL],
        description="Preferred stock markets"
    )
    notification_time: NotificationTime = Field(
        default=NotificationTime.BOTH,
        description="When to send notifications"
    )
    email_enabled: bool = Field(
        default=True,
        description="Whether to send email notifications"
    )


class UserProfile(BaseModel):
    """User profile model."""

    user_id: str = Field(description="Unique user identifier")
    email: EmailStr = Field(description="User email address")
    name: Optional[str] = Field(default=None, description="User display name")
    preferences: UserPreference = Field(
        default_factory=UserPreference,
        description="User preference settings"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Profile creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update time"
    )
    is_active: bool = Field(default=True, description="Whether user is active")


class UserCreate(BaseModel):
    """Request model for creating a user."""

    email: EmailStr = Field(description="User email address")
    name: Optional[str] = Field(default=None, description="User display name")
    preferences: Optional[UserPreference] = Field(
        default=None,
        description="Initial preference settings"
    )


class UserUpdate(BaseModel):
    """Request model for updating a user."""

    name: Optional[str] = None
    preferences: Optional[UserPreference] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for user data."""

    user_id: str
    email: str
    name: Optional[str]
    preferences: UserPreference
    created_at: datetime
    updated_at: datetime
    is_active: bool