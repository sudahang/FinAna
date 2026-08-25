# tests/v2/test_db.py
import sqlite3


def test_connect_wal_and_schema(tmp_path):
    from finana.storage.db import connect

    conn = connect(tmp_path / "t.db")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"metrics", "kv"} <= tables


def test_connect_idempotent(tmp_path):
    from finana.storage.db import connect

    connect(tmp_path / "t.db")
    conn = connect(tmp_path / "t.db")
    assert isinstance(conn, sqlite3.Connection)


def test_get_db_singleton(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana.storage import db

    db._conn = None
    assert db.get_db() is db.get_db()
