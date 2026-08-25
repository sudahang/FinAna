from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from finana.config import get_settings

    get_settings.cache_clear()


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DSH_MODEL", raising=False)
    from finana.config import Settings

    s = Settings()
    assert s.deepseek_api_key == ""
    assert s.dsh_model == "deepseek-v4-flash"
    assert s.database_path == tmp_path / "finana.db"
    assert s.sessions_dir == tmp_path / "sessions"
    assert s.logs_dir == tmp_path / "logs"


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DSH_MODEL", "deepseek-v4-pro")
    from finana.config import Settings

    s = Settings()
    assert s.deepseek_api_key == "sk-test"
    assert s.dsh_model == "deepseek-v4-pro"


def test_get_settings_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana.config import get_settings

    assert get_settings() is get_settings()


def test_finana_home_expands_user(monkeypatch):
    monkeypatch.setenv("FINANA_HOME", "~/finana-x")
    from finana.config import Settings

    s = Settings()
    home = Path.home() / "finana-x"
    assert s.database_path == home / "finana.db"
    assert s.sessions_dir == home / "sessions"
    assert s.logs_dir == home / "logs"
    assert "~" not in str(s.database_path)
    assert "~" not in str(s.sessions_dir)
    assert "~" not in str(s.logs_dir)


def test_provider_order_default_and_override():
    from finana.config import Settings
    from finana.datacore.registry import build_providers

    s = Settings(alltick_token="")
    assert s.provider_order == "eastmoney,sina_tencent,akshare,alltick"
    names = [p.name for p in build_providers(s)]
    assert names[0] == "eastmoney" and "sina_tencent" in names
    assert "alltick" not in names

    custom = Settings(provider_order="sina_tencent,eastmoney")
    assert [p.name for p in build_providers(custom)] == ["sina_tencent", "eastmoney"]
