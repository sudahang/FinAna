from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    dsh_model: str = "deepseek-v4-flash"
    finana_home: Path = Path.home() / ".finana"
    db_path: Path | None = None
    log_level: str = "INFO"
    http_timeout: int = 10

    @property
    def database_path(self) -> Path:
        return self.db_path or self.finana_home / "finana.db"

    @property
    def sessions_dir(self) -> Path:
        return self.finana_home / "sessions"

    @property
    def logs_dir(self) -> Path:
        return self.finana_home / "logs"

    def ensure_dirs(self) -> None:
        for d in (self.finana_home, self.sessions_dir, self.logs_dir, self.finana_home / "reports"):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
