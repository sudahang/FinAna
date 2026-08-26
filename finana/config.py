from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FinAna v2 全局配置，从环境变量与 .env 读取。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    dsh_model: str = "deepseek-v4-flash"
    dsh_max_tokens: int = 49152
    dsh_runtime: str = "auto"
    dsh_npm_bin: Path | None = None
    report_ttl_days: int = 30
    finana_home: Path = Path.home() / ".finana"
    db_path: Path | None = None
    log_level: str = "INFO"
    http_timeout: int = 10
    alltick_token: str = ""
    # 实测校准（Task 11）：东财全域可用且最快；新浪/腾讯在东财断连时兜底稳定；
    # akshare 仅 K 线备用；alltick 需 token，未配置时自动跳过。
    provider_order: str = "eastmoney,sina_tencent,akshare,alltick"

    @property
    def database_path(self) -> Path:
        """SQLite 数据库路径（db_path 优先），~ 已展开。"""
        if self.db_path is not None:
            return self.db_path.expanduser()
        return self.finana_home.expanduser() / "finana.db"

    @property
    def sessions_dir(self) -> Path:
        """会话存储目录，~ 已展开。"""
        return self.finana_home.expanduser() / "sessions"

    @property
    def logs_dir(self) -> Path:
        """日志目录，~ 已展开。"""
        return self.finana_home.expanduser() / "logs"

    def ensure_dirs(self) -> None:
        """创建运行所需的 home/sessions/logs/reports 目录。"""
        home = self.finana_home.expanduser()
        for d in (home, home / "sessions", home / "logs", home / "reports"):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """返回进程级单例 Settings。"""
    return Settings()
