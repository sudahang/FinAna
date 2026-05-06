"""Configuration for user module."""

from pydantic import BaseModel
import os


class AppConfig(BaseModel):
    """Application configuration."""

    app_name: str = "FinAna"
    notification_time_morning: str = "08:00"
    notification_time_evening: str = "20:00"
    enable_scheduler: bool = False
    scheduler_timezone: str = "Asia/Shanghai"
    scheduler_max_instances: int = 1
    scheduler_misfire_grace_seconds: int = 300


def get_app_config() -> AppConfig:
    """Get app configuration from environment."""
    return AppConfig(
        app_name=os.getenv("APP_NAME", "FinAna"),
        notification_time_morning=os.getenv("NOTIFICATION_TIME_MORNING", "08:00"),
        notification_time_evening=os.getenv("NOTIFICATION_TIME_EVENING", "20:00"),
        enable_scheduler=os.getenv("ENABLE_SCHEDULER", "false").lower() == "true",
        scheduler_timezone=os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai"),
        scheduler_max_instances=int(os.getenv("SCHEDULER_MAX_INSTANCES", "1")),
        scheduler_misfire_grace_seconds=int(os.getenv("SCHEDULER_MISFIRE_GRACE_SECONDS", "300")),
    )


config = get_app_config()