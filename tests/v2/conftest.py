import pytest

from finana.config import get_settings


@pytest.fixture(autouse=True)
def _isolated_finana_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    get_settings.cache_clear()
    yield
    from finana.storage import db

    db._conn = None
    get_settings.cache_clear()
