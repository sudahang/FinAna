"""Configuration for user module."""

from pydantic import BaseModel


class AppConfig(BaseModel):
    """Application configuration."""

    app_name: str = "FinAna"
    notification_time_morning: str = "08:00"
    notification_time_evening: str = "20:00"


config = AppConfig()