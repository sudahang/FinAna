import sqlite3
from pathlib import Path

_conn: sqlite3.Connection | None = None

_SCHEMA = Path(__file__).parent / "schema.sql"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    return conn


def get_db():
    global _conn
    if _conn is None:
        from finana.config import get_settings

        _conn = connect(get_settings().database_path)
    return _conn
