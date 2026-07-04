import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_connection, initialize_database, resolve_db_path


DATA_DIR = BACKEND_DIR / "data"
RECORDS_PATH = DATA_DIR / "records.json"
CONSOLIDATIONS_PATH = DATA_DIR / "consolidations.json"
USER_PROFILES_PATH = DATA_DIR / "user_profiles.json"
VALID_AGE_LEVELS = {
    "age_3_4": "3-4岁",
    "age_5_7": "5-7岁",
}
VALID_STATUSES = {"待巩固", "已巩固", "已掌握"}


def load_list(path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"缺少数据文件：{path}")
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"数据文件顶层必须是数组：{path}")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"数据文件中存在非对象记录：{path}")
    return data


def safe_nonnegative_int(value, field_name, record_id):
    try:
        result = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"记录{record_id}的{field_name}不是整数") from exc
    if result < 0:
        raise ValueError(f"记录{record_id}的{field_name}不能为负数")
    return result


def profile_map(profiles):
    result = {}
    for profile in profiles:
        user_id = str(profile.get("user_id") or "").strip()
        if not user_id:
            continue
        if user_id in result:
            raise ValueError(f"user_profiles.json 中用户重复：{user_id}")
        result[user_id] = profile
    return result


def collect_users(records, consolidations, profiles):
    profiles_by_user = profile_map(profiles)
    timestamps = defaultdict(list)
    user_ids = set(profiles_by_user)

    for item in records + consolidations:
        user_id = str(item.get("user_id") or "").strip()
        if not user_id:
            continue
        user_ids.add(user_id)
        for field in ("created_at", "updated_at"):
            value = str(item.get(field) or "").strip()
            if value:
                timestamps[user_id].append(value)

    users = []
    for user_id in sorted(user_ids):
        profile = profiles_by_user.get(user_id, {})
        age_level = profile.get("age_level")
        if age_level not in VALID_AGE_LEVELS:
            age_level = "age_3_4"
        age_range = VALID_AGE_LEVELS[age_level]
        known_times = sorted(timestamps[user_id])
        created_at = profile.get("created_at") or (known_times[0] if known_times else None)
        updated_at = profile.get("updated_at") or (known_times[-1] if known_times else None)
        users.append({
            "user_id": user_id,
            "age_level": age_level,
            "age_range": age_range,
            "created_at": created_at,
            "updated_at": updated_at,
        })
    return users, profiles_by_user


def normalize_reading_scores(profiles_by_user, valid_poem_ids):
    valid = []
    skipped = []
    for user_id, profile in profiles_by_user.items():
        scores = profile.get("reading_scores") or {}
        if not isinstance(scores, dict):
            raise ValueError(f"用户{user_id}的 reading_scores 必须是对象")
        for poem_id, value in scores.items():
            if poem_id not in valid_poem_ids:
                skipped.append({
                    "user_id": user_id,
                    "poem_id": poem_id,
                    "reason": "poem_id 不存在",
                })
                continue
            if isinstance(value, dict):
                raw_score = value.get("score")
                source = str(value.get("source") or "reading")
                updated_at = value.get("updated_at")
            else:
                raw_score = value
                source = "reading"
                updated_at = None
            try:
                score = float(raw_score)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"用户{user_id}对{poem_id}的评分无效") from exc
            if not 0 <= score <= 100:
                raise ValueError(f"用户{user_id}对{poem_id}的评分超出0-100")
            valid.append({
                "user_id": user_id,
                "poem_id": poem_id,
                "score": score,
                "source": source,
                "updated_at": updated_at,
            })
    return valid, skipped


def migrate(apply_changes=False, db_path=None):
    initialize_database(db_path)
    records = load_list(RECORDS_PATH)
    consolidations = load_list(CONSOLIDATIONS_PATH)
    profiles = load_list(USER_PROFILES_PATH, required=False)

    connection = get_connection(db_path)
    try:
        valid_poem_ids = {
            row[0] for row in connection.execute("SELECT id FROM poems").fetchall()
        }
        users, profiles_by_user = collect_users(records, consolidations, profiles)
        user_ids = {item["user_id"] for item in users}

        valid_records = []
        skipped_records = []
        seen_record_ids = set()
        for item in records:
            record_id = safe_nonnegative_int(item.get("id"), "id", item.get("id"))
            if record_id <= 0:
                raise ValueError("学习记录 id 必须大于0")
            if record_id in seen_record_ids:
                raise ValueError(f"学习记录 id 重复：{record_id}")
            seen_record_ids.add(record_id)
            user_id = str(item.get("user_id") or "").strip()
            poem_id = str(item.get("poem_id") or "").strip()
            if user_id not in user_ids:
                skipped_records.append({
                    "id": record_id,
                    "user_id": user_id,
                    "poem_id": poem_id,
                    "reason": "user_id 为空",
                })
                continue
            if poem_id not in valid_poem_ids:
                skipped_records.append({
                    "id": record_id,
                    "user_id": user_id,
                    "poem_id": poem_id,
                    "reason": "poem_id 不存在",
                })
                continue
            valid_records.append({
                "id": record_id,
                "user_id": user_id,
                "poem_id": poem_id,
                "duration_seconds": safe_nonnegative_int(
                    item.get("duration_seconds"), "duration_seconds", record_id
                ),
                "created_at": item.get("created_at"),
            })

        valid_consolidations = []
        skipped_consolidations = []
        seen_consolidation_keys = set()
        for item in consolidations:
            record_id = safe_nonnegative_int(item.get("id"), "id", item.get("id"))
            user_id = str(item.get("user_id") or "").strip()
            poem_id = str(item.get("poem_id") or "").strip()
            key = (user_id, poem_id)
            if key in seen_consolidation_keys:
                raise ValueError(f"巩固记录重复：{user_id}/{poem_id}")
            seen_consolidation_keys.add(key)
            if user_id not in user_ids or poem_id not in valid_poem_ids:
                skipped_consolidations.append({
                    "id": record_id,
                    "user_id": user_id,
                    "poem_id": poem_id,
                    "reason": "user_id 为空或 poem_id 不存在",
                })
                continue
            status = item.get("status") or "待巩固"
            if status not in VALID_STATUSES:
                raise ValueError(f"巩固记录{record_id}状态无效：{status}")
            valid_consolidations.append({
                "id": record_id,
                "user_id": user_id,
                "poem_id": poem_id,
                "status": status,
                "practice_count": safe_nonnegative_int(
                    item.get("practice_count"), "practice_count", record_id
                ),
                "next_review_date": str(item.get("next_review_date") or ""),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })

        reading_scores, skipped_scores = normalize_reading_scores(
            profiles_by_user, valid_poem_ids
        )
        before = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "learning_records", "consolidations", "reading_scores")
        }
        report = {
            "database_path": str(resolve_db_path(db_path)),
            "applied": apply_changes,
            "source_counts": {
                "users": len(users),
                "learning_records": len(records),
                "consolidations": len(consolidations),
                "reading_scores": len(reading_scores) + len(skipped_scores),
            },
            "valid_counts": {
                "users": len(users),
                "learning_records": len(valid_records),
                "consolidations": len(valid_consolidations),
                "reading_scores": len(reading_scores),
            },
            "skipped": {
                "learning_records": skipped_records,
                "consolidations": skipped_consolidations,
                "reading_scores": skipped_scores,
            },
            "before_counts": before,
        }
        if not apply_changes:
            report["after_counts"] = before
            return report

        inserted = defaultdict(int)
        existing = defaultdict(int)
        with connection:
            for item in users:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO users(
                        user_id, age_level, age_range, created_at, updated_at
                    ) VALUES (?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP),
                              COALESCE(?, CURRENT_TIMESTAMP))
                    """,
                    (
                        item["user_id"], item["age_level"], item["age_range"],
                        item["created_at"], item["updated_at"],
                    ),
                )
                inserted["users"] += cursor.rowcount
                existing["users"] += int(cursor.rowcount == 0)

            for item in valid_records:
                old = connection.execute(
                    "SELECT * FROM learning_records WHERE id = ?", (item["id"],)
                ).fetchone()
                if old:
                    comparable = (
                        old["user_id"], old["poem_id"], old["duration_seconds"],
                        old["created_at"],
                    )
                    incoming = (
                        item["user_id"], item["poem_id"], item["duration_seconds"],
                        item["created_at"],
                    )
                    if comparable != incoming:
                        raise ValueError(f"学习记录 id 冲突：{item['id']}")
                    existing["learning_records"] += 1
                    continue
                connection.execute(
                    """
                    INSERT INTO learning_records(
                        id, user_id, poem_id, duration_seconds, created_at
                    ) VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                    """,
                    (
                        item["id"], item["user_id"], item["poem_id"],
                        item["duration_seconds"], item["created_at"],
                    ),
                )
                inserted["learning_records"] += 1

            for item in valid_consolidations:
                old = connection.execute(
                    "SELECT id FROM consolidations WHERE user_id = ? AND poem_id = ?",
                    (item["user_id"], item["poem_id"]),
                ).fetchone()
                if old:
                    connection.execute(
                        """
                        UPDATE consolidations
                        SET status = ?, practice_count = ?, next_review_date = ?,
                            created_at = COALESCE(?, created_at),
                            updated_at = COALESCE(?, updated_at)
                        WHERE user_id = ? AND poem_id = ?
                        """,
                        (
                            item["status"], item["practice_count"],
                            item["next_review_date"], item["created_at"],
                            item["updated_at"], item["user_id"], item["poem_id"],
                        ),
                    )
                    existing["consolidations"] += 1
                    continue
                occupied = connection.execute(
                    "SELECT 1 FROM consolidations WHERE id = ?", (item["id"],)
                ).fetchone()
                if occupied:
                    raise ValueError(f"巩固记录 id 冲突：{item['id']}")
                connection.execute(
                    """
                    INSERT INTO consolidations(
                        id, user_id, poem_id, status, practice_count,
                        next_review_date, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP),
                              COALESCE(?, CURRENT_TIMESTAMP))
                    """,
                    (
                        item["id"], item["user_id"], item["poem_id"],
                        item["status"], item["practice_count"],
                        item["next_review_date"], item["created_at"],
                        item["updated_at"],
                    ),
                )
                inserted["consolidations"] += 1

            for item in reading_scores:
                old = connection.execute(
                    "SELECT 1 FROM reading_scores WHERE user_id = ? AND poem_id = ?",
                    (item["user_id"], item["poem_id"]),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO reading_scores(
                        user_id, poem_id, score, source, updated_at
                    ) VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                    ON CONFLICT(user_id, poem_id) DO UPDATE SET
                        score = excluded.score,
                        source = excluded.source,
                        updated_at = excluded.updated_at
                    """,
                    (
                        item["user_id"], item["poem_id"], item["score"],
                        item["source"], item["updated_at"],
                    ),
                )
                key = "existing" if old else "inserted"
                (existing if old else inserted)["reading_scores"] += 1

        after = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "learning_records", "consolidations", "reading_scores")
        }
        foreign_key_errors = [dict(row) for row in connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        report.update({
            "inserted_counts": dict(inserted),
            "existing_counts": dict(existing),
            "after_counts": after,
            "foreign_key_errors": foreign_key_errors,
            "integrity_check": integrity,
        })
        return report
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="将现有 JSON 动态数据迁移到 SQLite")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写入数据库；不传时只做预检",
    )
    parser.add_argument("--db-path", help="可选的 SQLite 数据库路径")
    args = parser.parse_args()
    print(json.dumps(
        migrate(apply_changes=args.apply, db_path=args.db_path),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
