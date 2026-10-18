import sqlite3
from pathlib import Path
from src.config import get_settings

def resolve_db_path(db_path: str = None) -> str:
    if db_path is None:
        url = get_settings().database_url
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "")
        return url
    return db_path

def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    target_path = resolve_db_path(db_path)
    conn = sqlite3.connect(target_path, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = None) -> None:
    conn = get_db_connection(db_path)
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    conn.close()
