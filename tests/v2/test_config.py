from pathlib import Path


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
