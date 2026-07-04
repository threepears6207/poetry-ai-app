import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_connection, initialize_database, resolve_db_path


SOURCE_PATH = (
    BACKEND_DIR
    / "data_sources"
    / "generated"
    / "children_poems_candidates.json"
)
EXPECTED_COUNT = 150
ARRAY_FIELDS = ("content", "tags", "theme_tags", "knowledge_tags")


def load_and_validate_poems() -> list[dict]:
    with open(SOURCE_PATH, "r", encoding="utf-8") as file:
        poems = json.load(file)

    if not isinstance(poems, list):
        raise ValueError("候选古诗文件必须是 JSON 数组")
    if len(poems) != EXPECTED_COUNT:
        raise ValueError(f"候选古诗应为 {EXPECTED_COUNT} 首，实际为 {len(poems)} 首")

    seen_ids = set()
    seen_first_lines = set()
    for index, poem in enumerate(poems, start=1):
        poem_id = str(poem.get("id", "")).strip()
        title = str(poem.get("title", "")).strip()
        author = str(poem.get("author", "")).strip()
        content = poem.get("content")

        if not poem_id or not title or not author:
            raise ValueError(f"第 {index} 首缺少 id、title 或 author")
        if not isinstance(content, list) or not content:
            raise ValueError(f"{poem_id} 的 content 必须是非空数组")
        if poem_id in seen_ids:
            raise ValueError(f"存在重复古诗 ID：{poem_id}")

        first_line = str(content[0]).strip()
        if first_line in seen_first_lines:
            raise ValueError(f"存在重复首句：{first_line}")

        for field in ARRAY_FIELDS:
            value = poem.get(field, [])
            if not isinstance(value, list):
                raise ValueError(f"{poem_id} 的 {field} 必须是数组")

        difficulty = poem.get("difficulty", 1)
        if not isinstance(difficulty, int) or difficulty < 1:
            raise ValueError(f"{poem_id} 的 difficulty 必须是大于等于1的整数")

        seen_ids.add(poem_id)
        seen_first_lines.add(first_line)

    return poems


def json_text(value) -> str:
    return json.dumps(value or [], ensure_ascii=False, separators=(",", ":"))


def import_poems(sync_existing: bool = False) -> dict:
    poems = load_and_validate_poems()
    initialize_database()
    database_path = resolve_db_path()
    connection = get_connection(database_path)

    try:
        before_count = connection.execute("SELECT COUNT(*) FROM poems").fetchone()[0]
        before_changes = connection.total_changes

        connection.execute("BEGIN")
        insert_sql = """
            INSERT OR IGNORE INTO poems (
                id, title, author, dynasty, content_json, translation,
                tags_json, age_level, age_range, difficulty,
                theme_tags_json, knowledge_tags_json, recommend_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        if sync_existing:
            insert_sql = """
                INSERT INTO poems (
                    id, title, author, dynasty, content_json, translation,
                    tags_json, age_level, age_range, difficulty,
                    theme_tags_json, knowledge_tags_json, recommend_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    dynasty = excluded.dynasty,
                    content_json = excluded.content_json,
                    translation = excluded.translation,
                    tags_json = excluded.tags_json,
                    age_level = excluded.age_level,
                    age_range = excluded.age_range,
                    difficulty = excluded.difficulty,
                    theme_tags_json = excluded.theme_tags_json,
                    knowledge_tags_json = excluded.knowledge_tags_json,
                    recommend_reason = excluded.recommend_reason
            """

        for poem in poems:
            connection.execute(
                insert_sql,
                (
                    poem["id"],
                    poem["title"],
                    poem.get("author", ""),
                    poem.get("dynasty", ""),
                    json_text(poem.get("content", [])),
                    poem.get("translation", ""),
                    json_text(poem.get("tags", [])),
                    poem.get("age_level", ""),
                    poem.get("age_range", ""),
                    poem.get("difficulty", 1),
                    json_text(poem.get("theme_tags", [])),
                    json_text(poem.get("knowledge_tags", [])),
                    poem.get("recommend_reason", ""),
                ),
            )
        connection.commit()

        inserted_count = connection.total_changes - before_changes
        after_count = connection.execute("SELECT COUNT(*) FROM poems").fetchone()[0]
        empty_translation_count = connection.execute(
            "SELECT COUNT(*) FROM poems WHERE TRIM(translation) = ''"
        ).fetchone()[0]
        age_counts = {
            row["age_level"]: row["count"]
            for row in connection.execute(
                """
                SELECT age_level, COUNT(*) AS count
                FROM poems
                GROUP BY age_level
                ORDER BY age_level
                """
            ).fetchall()
        }
        invalid_json_count = 0
        for row in connection.execute(
            """
            SELECT id, content_json, tags_json, theme_tags_json, knowledge_tags_json
            FROM poems
            """
        ).fetchall():
            try:
                json.loads(row["content_json"])
                json.loads(row["tags_json"])
                json.loads(row["theme_tags_json"])
                json.loads(row["knowledge_tags_json"])
            except (TypeError, json.JSONDecodeError):
                invalid_json_count += 1

        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "database_path": str(database_path),
        "source_path": str(SOURCE_PATH),
        "source_count": len(poems),
        "sync_existing": sync_existing,
        "before_count": before_count,
        "inserted_count": inserted_count,
        "skipped_existing_count": len(poems) - inserted_count,
        "after_count": after_count,
        "empty_translation_count": empty_translation_count,
        "age_counts": age_counts,
        "invalid_json_count": invalid_json_count,
        "integrity_check": integrity_check,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将儿童古诗候选库导入 SQLite")
    parser.add_argument(
        "--sync-existing",
        action="store_true",
        help="按候选文件同步更新数据库中已有的古诗",
    )
    args = parser.parse_args()
    print(json.dumps(import_poems(sync_existing=args.sync_existing), ensure_ascii=False, indent=2))
