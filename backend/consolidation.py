import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection


router = APIRouter()


class ConsolidationResultIn(BaseModel):
    poem_id: str
    user_id: Optional[str] = "test_user"
    passed: bool


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
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "poem_id": row["poem_id"],
        "status": row["status"],
        "practice_count": int(row["practice_count"] or 0),
        "next_review_date": row["next_review_date"],
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


@router.get("/consolidation/list")
def get_consolidation_list(user_id="test_user"):
    user_id = normalize_user_id(user_id)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT c.*, p.title, p.author, p.dynasty, p.tags_json
            FROM consolidations AS c
            JOIN poems AS p ON p.id = c.poem_id
            WHERE c.user_id = ?
            ORDER BY c.id
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
        "pending_count": sum(item["status"] == "待巩固" for item in result),
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
