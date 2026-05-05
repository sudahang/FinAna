"""Configuration for user module."""

from pydantic import BaseModel
import os


class AppConfig(BaseModel):
    """Application configuration."""

    app_name: str = "FinAna"
    notification_time_morning: str = "08:00"
    notification_time_evening: str = "20:00"


def get_app_config() -> AppConfig:
    """Get app configuration from environment."""
    return AppConfig(
        app_name=os.getenv("APP_NAME", "FinAna"),
        notification_time_morning=os.getenv("NOTIFICATION_TIME_MORNING", "08:00"),
        notification_time_evening=os.getenv("NOTIFICATION_TIME_EVENING", "20:00")
    )


config = get_app_config()