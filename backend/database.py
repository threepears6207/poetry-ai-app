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
        _migrate_poem_catalog(connection)
        connection.commit()
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


def _migrate_poem_catalog(connection: sqlite3.Connection) -> None:
    """Apply additive poem-catalog migrations to databases created by v1."""
    existing_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(poems)").fetchall()
    }
    additions = {
        "content_hash": "TEXT NOT NULL DEFAULT ''",
        "library_scope": "TEXT NOT NULL DEFAULT 'core'",
        "source_name": "TEXT NOT NULL DEFAULT ''",
        "source_url": "TEXT NOT NULL DEFAULT ''",
        "source_version": "TEXT NOT NULL DEFAULT ''",
        "verification_status": "TEXT NOT NULL DEFAULT 'verified'",
        "content_complete": "INTEGER NOT NULL DEFAULT 1",
        "recommend_eligible": "INTEGER NOT NULL DEFAULT 1",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }
    for column, definition in additions.items():
        if column not in existing_columns:
            connection.execute(f"ALTER TABLE poems ADD COLUMN {column} {definition}")

    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_poems_content_hash ON poems(content_hash)"
    )
    consolidation_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(consolidations)").fetchall()
    }
    consolidation_additions = {
        "reading_completed": "INTEGER NOT NULL DEFAULT 0",
        "connection_completed": "INTEGER NOT NULL DEFAULT 0",
        "collection_state": "TEXT NOT NULL DEFAULT 'gray'",
        "flower_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for column, definition in consolidation_additions.items():
        if column not in consolidation_columns:
            connection.execute(
                f"ALTER TABLE consolidations ADD COLUMN {column} {definition}"
            )
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations(version, name)
        VALUES (3, 'learning_collection_state')
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_poems_title_author ON poems(title, author)"
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations(version, name)
        VALUES (2, 'poem_catalog_provenance_and_dedup')
        """
    )
