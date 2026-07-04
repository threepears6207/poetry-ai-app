import os
import sqlite3
from pathlib import Path
from typing import Optional, Union


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "poetry_ai.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def resolve_db_path(db_path: Optional[Union[str, Path]] = None) -> Path:
    value = db_path or os.getenv("POETRY_DB_PATH")
    if not value:
        return DEFAULT_DB_PATH

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def get_connection(
    db_path: Optional[Union[str, Path]] = None,
) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(
    db_path: Optional[Union[str, Path]] = None,
) -> dict:
    path = resolve_db_path(db_path)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    connection = get_connection(path)
    try:
        connection.executescript(schema)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        ]
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        connection.close()

    return {
        "database_path": str(path),
        "integrity_check": integrity,
        "foreign_keys_enabled": bool(foreign_keys_enabled),
        "tables": tables,
    }
