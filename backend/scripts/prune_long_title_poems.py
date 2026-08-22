import argparse
import json
import sqlite3
from pathlib import Path

MAX_TITLE_HAN_CHARACTERS = 6
SOURCE_PATHS = (
    Path("data_sources/generated/children_poems_candidates.json"),
    Path("data_sources/classic_poems/tang_poems_candidates.json"),
)


def title_han_character_count(value):
    return sum(0x3400 <= ord(character) <= 0x9FFF for character in str(value or ""))


def prune_source(path, apply=False):
    poems = json.loads(path.read_text(encoding="utf-8"))
    removed = [
        poem for poem in poems
        if title_han_character_count(poem.get("title")) > MAX_TITLE_HAN_CHARACTERS
    ]
    retained = [poem for poem in poems if poem not in removed]
    if apply and removed:
        path.write_text(
            json.dumps(retained, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {
        "path": str(path),
        "before_count": len(poems),
        "after_count": len(retained),
        "removed": [
            {
                "id": poem.get("id"),
                "title": poem.get("title"),
                "title_han_characters": title_han_character_count(poem.get("title")),
            }
            for poem in removed
        ],
    }


def prune_database(database_path, removed_ids):
    if not database_path.exists() or not removed_ids:
        return {"database_path": str(database_path), "deleted_poems": 0}
    placeholders = ",".join("?" for _ in removed_ids)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        before = connection.execute(
            f"SELECT COUNT(*) FROM poems WHERE id IN ({placeholders})", removed_ids
        ).fetchone()[0]
        for table in ("reading_scores", "consolidations", "learning_records"):
            connection.execute(
                f"DELETE FROM {table} WHERE poem_id IN ({placeholders})", removed_ids
            )
        connection.execute(
            f"DELETE FROM poem_aliases WHERE poem_id IN ({placeholders})", removed_ids
        )
        connection.execute(f"DELETE FROM poems WHERE id IN ({placeholders})", removed_ids)
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "database_path": str(database_path),
        "deleted_poems": before,
        "integrity_check": integrity,
    }


def main():
    parser = argparse.ArgumentParser(
        description="剔除标题超过 6 个汉字的古诗，并可同步清理本地 SQLite。"
    )
    parser.add_argument("--backend-dir", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true", help="实际修改源文件和数据库")
    parser.add_argument("--db-path", help="可选 SQLite 路径；默认 data/poetry_ai.db")
    args = parser.parse_args()

    backend_dir = Path(args.backend_dir).resolve()
    reports = [prune_source(backend_dir / relative, apply=args.apply) for relative in SOURCE_PATHS]
    removed_ids = [item["id"] for report in reports for item in report["removed"]]
    result = {
        "max_title_han_characters": MAX_TITLE_HAN_CHARACTERS,
        "applied": args.apply,
        "source_reports": reports,
        "removed_count": len(removed_ids),
        "remaining_count": sum(report["after_count"] for report in reports),
    }
    if args.apply:
        database_path = Path(args.db_path) if args.db_path else backend_dir / "data/poetry_ai.db"
        result["database"] = prune_database(database_path.resolve(), removed_ids)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
