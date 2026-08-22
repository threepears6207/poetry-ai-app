import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_connection, initialize_database, resolve_db_path
from poem_catalog import normalize_poem_text, poem_content_hash
from tag_rules import validate_tag_metadata

CORE_SOURCE_PATH = BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json"
SUPPLEMENT_SOURCE_PATH = BACKEND_DIR / "data_sources" / "classic_poems" / "tang_poems_candidates.json"
DEFAULT_SOURCE_PATH = CORE_SOURCE_PATH
SOURCE_NAME = "小学古诗词目录与 chinese-poetry 开源语料核验集"
SOURCE_URL = "https://github.com/chinese-poetry/chinese-poetry"
SOURCE_VERSION = "b8594f81a89752241442f2ce267d6f66f96704ee"
ARRAY_FIELDS = ("content", "tags", "theme_tags", "knowledge_tags")
REQUIRED_FIELDS = (
    "id", "title", "author", "dynasty", "content", "translation", "tags",
    "age_level", "age_range", "difficulty", "theme_tags", "knowledge_tags",
    "recommend_reason",
)
VALID_AGE_LEVELS = {"age_3_4", "age_5_7"}
MAX_TITLE_HAN_CHARACTERS = 6


def title_han_character_count(value):
    return sum(0x3400 <= ord(character) <= 0x9FFF for character in str(value or ""))


def load_catalog(source_path=DEFAULT_SOURCE_PATH):
    path = Path(source_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("诗库文件顶层必须是对象数组")
    return data


def load_default_catalogs():
    """Load both user-provided batches and reuse the first canonical content row."""
    specs = (
        (CORE_SOURCE_PATH, "儿童诗库"),
        (SUPPLEMENT_SOURCE_PATH, "补充批次（原文件 tang_poems_candidates.json）"),
    )
    merged = []
    duplicates = []
    seen_hashes = {}
    raw_count = 0
    for path, source_label in specs:
        poems = load_catalog(path)
        raw_count += len(poems)
        for poem in poems:
            item = dict(poem)
            item["_library_scope"] = "core"
            item["_source_name"] = f"{SOURCE_NAME} / {source_label}"
            content_hash = poem_content_hash(item.get("content") or [])
            canonical = seen_hashes.get(content_hash)
            if canonical:
                duplicates.append({
                    "duplicate_id": item.get("id"),
                    "duplicate_title": item.get("title"),
                    "canonical_id": canonical.get("id"),
                    "canonical_title": canonical.get("title"),
                    "reason": "same_content_hash",
                })
                continue
            seen_hashes[content_hash] = item
            merged.append(item)
    return merged, duplicates, raw_count, [str(spec[0]) for spec in specs]


def validate_catalog(poems):
    errors = []
    seen_ids = set()
    seen_hashes = {}
    for index, poem in enumerate(poems, start=1):
        poem_id = str(poem.get("id") or "").strip()
        label = poem_id or f"第{index}首"
        missing = [field for field in REQUIRED_FIELDS if field not in poem]
        if missing:
            errors.append(f"{label} 缺少字段：{','.join(missing)}")
            continue
        for field in ("id", "title", "author", "dynasty", "translation", "age_range", "recommend_reason"):
            if not str(poem.get(field) or "").strip():
                errors.append(f"{label} 的 {field} 不能为空")
        title_length = title_han_character_count(poem.get("title"))
        if title_length > MAX_TITLE_HAN_CHARACTERS:
            errors.append(
                f"{label} 的标题超过 {MAX_TITLE_HAN_CHARACTERS} 个汉字："
                f"{poem.get('title')}（{title_length}字）"
            )
        for field in ARRAY_FIELDS:
            value = poem.get(field)
            if not isinstance(value, list) or not value:
                errors.append(f"{label} 的 {field} 必须是非空数组")
        if poem.get("age_level") not in VALID_AGE_LEVELS:
            errors.append(f"{label} 的 age_level 无效")
        if not isinstance(poem.get("difficulty"), int) or not 1 <= poem["difficulty"] <= 5:
            errors.append(f"{label} 的 difficulty 必须为 1-5 整数")
        for error in validate_tag_metadata(poem):
            errors.append(f"{label}：{error}")

        content = poem.get("content") if isinstance(poem.get("content"), list) else []
        normalized = normalize_poem_text("".join(str(line) for line in content))
        if len(content) < 2 or len(normalized) < 8:
            errors.append(f"{label} 正文不完整")
        content_hash = poem_content_hash(content)
        if poem_id in seen_ids:
            errors.append(f"ID 重复：{poem_id}")
        elif poem_id:
            seen_ids.add(poem_id)
        if content_hash in seen_hashes:
            errors.append(f"正文重复：{seen_hashes[content_hash]} 与 {label}")
        elif content_hash:
            seen_hashes[content_hash] = label
    return errors


def _json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _poem_values(poem):
    return (
        str(poem["id"]).strip(), str(poem["title"]).strip(),
        str(poem["author"]).strip(), str(poem["dynasty"]).strip(),
        _json_text(poem["content"]), str(poem["translation"]).strip(),
        _json_text(poem["tags"]), poem["age_level"], str(poem["age_range"]).strip(),
        poem["difficulty"], _json_text(poem["theme_tags"]),
        _json_text(poem["knowledge_tags"]), str(poem["recommend_reason"]).strip(),
        poem_content_hash(poem["content"]), poem.get("_library_scope", "core"),
        poem.get("_source_name", SOURCE_NAME), SOURCE_URL, SOURCE_VERSION,
    )


UPSERT_SQL = """
INSERT INTO poems (
    id, title, author, dynasty, content_json, translation, tags_json,
    age_level, age_range, difficulty, theme_tags_json, knowledge_tags_json,
    recommend_reason, content_hash, library_scope, source_name, source_url,
    source_version, verification_status, content_complete, recommend_eligible
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
          'verified', 1, 1)
ON CONFLICT(id) DO UPDATE SET
    title=excluded.title, author=excluded.author, dynasty=excluded.dynasty,
    content_json=excluded.content_json, translation=excluded.translation,
    tags_json=excluded.tags_json, age_level=excluded.age_level,
    age_range=excluded.age_range, difficulty=excluded.difficulty,
    theme_tags_json=excluded.theme_tags_json,
    knowledge_tags_json=excluded.knowledge_tags_json,
    recommend_reason=excluded.recommend_reason, content_hash=excluded.content_hash,
    library_scope=excluded.library_scope, source_name=excluded.source_name,
    source_url=excluded.source_url, source_version=excluded.source_version,
    verification_status='verified', content_complete=1, recommend_eligible=1,
    updated_at=CURRENT_TIMESTAMP
"""


def import_catalog(apply_changes=False, db_path=None, source_path=None):
    if source_path is None:
        poems, duplicates, raw_count, source_paths = load_default_catalogs()
    else:
        poems = load_catalog(source_path)
        duplicates, raw_count, source_paths = [], len(poems), [str(Path(source_path))]
    errors = validate_catalog(poems)
    if errors:
        raise ValueError("诗库质量门禁未通过：\n" + "\n".join(errors))

    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        existing_ids = {row[0] for row in connection.execute("SELECT id FROM poems")}
        inserted = sum(str(poem["id"]) not in existing_ids for poem in poems)
        report = {
            "database_path": str(resolve_db_path(db_path)),
            "source_paths": source_paths,
            "source_row_count": raw_count,
            "unique_poem_count": len(poems),
            "duplicate_row_count": len(duplicates),
            "duplicate_rows": duplicates,
            "quality_gate": "passed",
            "applied": apply_changes, "planned_insert_count": inserted,
            "planned_update_count": len(poems) - inserted,
            "before_count": len(existing_ids),
        }
        if not apply_changes:
            report["after_count"] = len(existing_ids)
            return report

        with connection:
            for poem in poems:
                connection.execute(UPSERT_SQL, _poem_values(poem))
            for duplicate in duplicates:
                connection.execute(
                    """
                    INSERT INTO poem_aliases(alias_id, poem_id, reason)
                    VALUES (?, ?, ?)
                    ON CONFLICT(alias_id) DO UPDATE SET
                        poem_id=excluded.poem_id, reason=excluded.reason
                    """,
                    (
                        duplicate["duplicate_id"],
                        duplicate["canonical_id"],
                        duplicate["reason"],
                    ),
                )
        report.update({
            "after_count": connection.execute("SELECT COUNT(*) FROM poems").fetchone()[0],
            "recommend_eligible_count": connection.execute(
                "SELECT COUNT(*) FROM poems WHERE verification_status='verified' "
                "AND content_complete=1 AND recommend_eligible=1"
            ).fetchone()[0],
            "alias_count": connection.execute(
                "SELECT COUNT(*) FROM poem_aliases"
            ).fetchone()[0],
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_errors": [dict(row) for row in connection.execute("PRAGMA foreign_key_check")],
        })
        return report
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="预检或导入核心库与补充古诗库")
    parser.add_argument("--apply", action="store_true", help="通过质量门禁后实际写入")
    parser.add_argument("--db-path", help="可选 SQLite 路径")
    parser.add_argument("--source-path", help="仅导入指定文件；省略时合并两批诗库")
    args = parser.parse_args()
    print(json.dumps(
        import_catalog(args.apply, args.db_path, args.source_path),
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
