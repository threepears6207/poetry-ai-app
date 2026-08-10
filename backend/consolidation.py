import json
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection


router = APIRouter()


class ConsolidationResultIn(BaseModel):
    poem_id: str
    user_id: Optional[str] = "test_user"
    passed: bool


class PracticeProgressIn(BaseModel):
    poem_id: str
    user_id: Optional[str] = "test_user"
    activity: Literal["reading", "connection"]
    completed: bool = True


def today_text():
    return datetime.now().strftime("%Y-%m-%d")


def date_after_days(days):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_array(value):
    try:
        data = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def normalize_user_id(user_id):
    return str(user_id or "test_user").strip() or "test_user"


def consolidation_from_row(row):
    available = set(row.keys())
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "poem_id": row["poem_id"],
        "status": row["status"],
        "practice_count": int(row["practice_count"] or 0),
        "next_review_date": row["next_review_date"],
        "reading_completed": bool(row["reading_completed"]) if "reading_completed" in available else False,
        "connection_completed": bool(row["connection_completed"]) if "connection_completed" in available else False,
        "collection_state": row["collection_state"] if "collection_state" in available else "gray",
        "flower_count": int(row["flower_count"] or 0) if "flower_count" in available else 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def ensure_user(connection, user_id):
    connection.execute(
        """
        INSERT OR IGNORE INTO users(user_id, age_level, age_range)
        VALUES (?, 'age_3_4', '3-4岁')
        """,
        (user_id,),
    )


def ensure_poem_exists(connection, poem_id):
    exists = connection.execute(
        "SELECT 1 FROM poems WHERE id = ?", (poem_id,)
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail=f"未找到古诗：{poem_id}")


def create_consolidation_if_missing(
    poem_id,
    user_id="test_user",
    connection=None,
):
    """在 SQLite 中创建待巩固记录；已有记录时保持原进度。"""
    user_id = normalize_user_id(user_id)
    owns_connection = connection is None
    connection = connection or get_connection()
    try:
        ensure_user(connection, user_id)
        ensure_poem_exists(connection, poem_id)
        existing = connection.execute(
            """
            SELECT * FROM consolidations
            WHERE user_id = ? AND poem_id = ?
            """,
            (user_id, poem_id),
        ).fetchone()
        if existing:
            return consolidation_from_row(existing)

        now = now_text()
        cursor = connection.execute(
            """
            INSERT INTO consolidations(
                user_id, poem_id, status, practice_count,
                next_review_date, created_at, updated_at
            ) VALUES (?, ?, '待巩固', 0, ?, ?, ?)
            """,
            (user_id, poem_id, today_text(), now, now),
        )
        if owns_connection:
            connection.commit()
        row = connection.execute(
            "SELECT * FROM consolidations WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return consolidation_from_row(row)
    except Exception:
        if owns_connection:
            connection.rollback()
        raise
    finally:
        if owns_connection:
            connection.close()


def is_due_today(next_review_date):
    return not next_review_date or next_review_date <= today_text()


def get_next_interval_days(practice_count):
    if practice_count <= 1:
        return 1
    if practice_count == 2:
        return 3
    return 7


def get_display_status(item):
    status = item.get("status", "待巩固")
    if status == "已掌握":
        return "已掌握"
    if status == "已巩固" and not is_due_today(item.get("next_review_date", "")):
        return "已巩固"
    return "待巩固"


def apply_practice_activity(data: PracticeProgressIn, db_path=None):
    """Persist one required activity and atomically unlock the collection card."""
    from database import initialize_database

    initialize_database(db_path)
    user_id = normalize_user_id(data.user_id)
    connection = get_connection(db_path)
    try:
        with connection:
            item = create_consolidation_if_missing(
                data.poem_id, user_id, connection=connection,
            )
            reading_completed = bool(item["reading_completed"])
            connection_completed = bool(item["connection_completed"])
            if data.activity == "reading":
                reading_completed = bool(data.completed)
            else:
                connection_completed = bool(data.completed)

            was_color = item["collection_state"] == "color"
            unlocked = reading_completed and connection_completed
            collection_state = "color" if was_color or unlocked else "gray"
            flower_count = int(item["flower_count"])
            practice_count = int(item["practice_count"])
            status = item["status"]
            next_review_date = item["next_review_date"]
            just_unlocked = unlocked and not was_color
            if just_unlocked:
                flower_count += 1
                practice_count += 1
                status = "已掌握" if practice_count >= 3 else "已巩固"
                next_review_date = date_after_days(get_next_interval_days(practice_count))

            connection.execute(
                """
                UPDATE consolidations
                SET reading_completed=?, connection_completed=?,
                    collection_state=?, flower_count=?, status=?,
                    practice_count=?, next_review_date=?, updated_at=?
                WHERE user_id=? AND poem_id=?
                """,
                (
                    int(reading_completed), int(connection_completed),
                    collection_state, flower_count, status, practice_count,
                    next_review_date, now_text(), user_id, data.poem_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM consolidations WHERE user_id=? AND poem_id=?",
                (user_id, data.poem_id),
            ).fetchone()
        return consolidation_from_row(row), just_unlocked
    finally:
        connection.close()


@router.post("/consolidation/progress")
def update_practice_progress(data: PracticeProgressIn):
    state, just_unlocked = apply_practice_activity(data)
    return {
        "success": True,
        "just_unlocked": just_unlocked,
        "data": state,
    }


def collection_wall_data(user_id="test_user", db_path=None):
    from database import initialize_database

    initialize_database(db_path)
    user_id = normalize_user_id(user_id)
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            """
            SELECT p.id AS poem_id, p.title, p.author, p.dynasty,
                   p.age_level, p.difficulty,
                   COALESCE(c.reading_completed, 0) AS reading_completed,
                   COALESCE(c.connection_completed, 0) AS connection_completed,
                   COALESCE(c.collection_state, 'gray') AS collection_state,
                   COALESCE(c.flower_count, 0) AS flower_count,
                   COALESCE(c.next_review_date, '') AS next_review_date
            FROM poems AS p
            JOIN (
                SELECT poem_id, MAX(created_at) AS learned_at
                FROM learning_records WHERE user_id=? GROUP BY poem_id
            ) AS learned ON learned.poem_id=p.id
            LEFT JOIN consolidations AS c
                ON c.poem_id=p.id AND c.user_id=?
            ORDER BY learned.learned_at DESC, p.id
            """,
            (user_id, user_id),
        ).fetchall()
    finally:
        connection.close()
    poems = [dict(row) for row in rows]
    for poem in poems:
        poem["reading_completed"] = bool(poem["reading_completed"])
        poem["connection_completed"] = bool(poem["connection_completed"])
    return {
        "success": True,
        "user_id": user_id,
        "total": len(poems),
        "color_count": sum(poem["collection_state"] == "color" for poem in poems),
        "flower_count": sum(int(poem["flower_count"]) for poem in poems),
        "poems": poems,
    }


@router.get("/collection/wall")
def get_collection_wall(user_id="test_user"):
    return collection_wall_data(user_id)


@router.get("/consolidation/list")
def get_consolidation_list(user_id="test_user"):
    user_id = normalize_user_id(user_id)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                COALESCE(c.id, 0) AS id,
                learned.user_id AS user_id,
                learned.poem_id AS poem_id,
                COALESCE(c.status, '待巩固') AS status,
                COALESCE(c.practice_count, 0) AS practice_count,
                COALESCE(c.next_review_date, '') AS next_review_date,
                COALESCE(c.reading_completed, 0) AS reading_completed,
                COALESCE(c.connection_completed, 0) AS connection_completed,
                COALESCE(c.collection_state, 'gray') AS collection_state,
                COALESCE(c.flower_count, 0) AS flower_count,
                COALESCE(c.created_at, learned.learned_at) AS created_at,
                COALESCE(c.updated_at, learned.learned_at) AS updated_at,
                p.title, p.author, p.dynasty, p.tags_json
            FROM (
                SELECT user_id, poem_id, MAX(created_at) AS learned_at
                FROM learning_records
                WHERE user_id = ?
                GROUP BY user_id, poem_id
            ) AS learned
            JOIN poems AS p ON p.id = learned.poem_id
            LEFT JOIN consolidations AS c
                ON c.poem_id = learned.poem_id AND c.user_id = learned.user_id
            ORDER BY learned.learned_at DESC, p.id
            """,
            (user_id,),
        ).fetchall()
    finally:
        connection.close()

    result = []
    for row in rows:
        item = consolidation_from_row(row)
        next_review_date = item["next_review_date"]
        result.append({
            **item,
            "title": row["title"],
            "author": row["author"],
            "dynasty": row["dynasty"],
            "tags": json_array(row["tags_json"]),
            "status": get_display_status(item),
            "due_today": is_due_today(next_review_date),
        })

    return {
        "success": True,
        "user_id": user_id,
        "total_count": len(result),
        "mastered_count": sum(item["status"] == "已掌握" for item in result),
        "consolidated_count": sum(item["collection_state"] == "color" for item in result),
        "pending_count": sum(item["collection_state"] != "color" for item in result),
        "due_today_count": sum(bool(item["due_today"]) for item in result),
        "data": result,
    }


@router.get("/consolidation/status/{poem_id}")
def get_consolidation_status(poem_id, user_id="test_user"):
    user_id = normalize_user_id(user_id)
    connection = get_connection()
    try:
        poem = connection.execute(
            "SELECT title, author, dynasty FROM poems WHERE id = ?",
            (poem_id,),
        ).fetchone()
        if not poem:
            raise HTTPException(status_code=404, detail=f"未找到古诗：{poem_id}")
        row = connection.execute(
            """
            SELECT * FROM consolidations
            WHERE user_id = ? AND poem_id = ?
            """,
            (user_id, poem_id),
        ).fetchone()
    finally:
        connection.close()

    if not row:
        return {
            "success": True,
            "user_id": user_id,
            "poem_id": poem_id,
            "title": poem["title"],
            "author": poem["author"],
            "dynasty": poem["dynasty"],
            "status": "未学习",
            "practice_count": 0,
            "next_review_date": None,
            "due_today": False,
        }

    item = consolidation_from_row(row)
    return {
        "success": True,
        **item,
        "title": poem["title"],
        "author": poem["author"],
        "dynasty": poem["dynasty"],
        "status": get_display_status(item),
        "due_today": is_due_today(item["next_review_date"]),
    }


@router.post("/consolidation/result")
def update_consolidation_result(result: ConsolidationResultIn):
    user_id = normalize_user_id(result.user_id)
    if result.passed:
        apply_practice_activity(PracticeProgressIn(
            poem_id=result.poem_id,
            user_id=user_id,
            activity="reading",
            completed=True,
        ))
        updated, just_unlocked = apply_practice_activity(PracticeProgressIn(
            poem_id=result.poem_id,
            user_id=user_id,
            activity="connection",
            completed=True,
        ))
        return {
            "success": True,
            "message": "巩固结果已更新",
            "just_unlocked": just_unlocked,
            "data": updated,
        }
    connection = get_connection()
    try:
        with connection:
            item = create_consolidation_if_missing(
                result.poem_id,
                user_id,
                connection=connection,
            )
            if not is_due_today(item["next_review_date"]):
                return {
                    "success": True,
                    "message": "当前巩固已完成，请到复习日期再来",
                    "data": item,
                    "already_done_today": True,
                }

            if result.passed:
                new_count = int(item["practice_count"] or 0) + 1
                status = "已掌握" if new_count >= 3 else "已巩固"
                next_review_date = date_after_days(
                    7 if new_count >= 3 else get_next_interval_days(new_count)
                )
            else:
                new_count = int(item["practice_count"] or 0)
                status = item["status"]
                next_review_date = today_text()

            updated_at = now_text()
            connection.execute(
                """
                UPDATE consolidations
                SET status = ?, practice_count = ?, next_review_date = ?, updated_at = ?
                WHERE user_id = ? AND poem_id = ?
                """,
                (
                    status,
                    new_count,
                    next_review_date,
                    updated_at,
                    user_id,
                    result.poem_id,
                ),
            )
            row = connection.execute(
                """
                SELECT * FROM consolidations
                WHERE user_id = ? AND poem_id = ?
                """,
                (user_id, result.poem_id),
            ).fetchone()
            updated = consolidation_from_row(row)
    finally:
        connection.close()

    return {
        "success": True,
        "message": "巩固结果已更新",
        "data": updated,
    }
