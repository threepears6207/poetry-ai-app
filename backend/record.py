import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from consolidation import create_consolidation_if_missing
from database import get_connection


router = APIRouter()


class RecordIn(BaseModel):
    poem_id: str
    user_id: Optional[str] = "test_user"
    duration_seconds: Optional[int] = 0


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_user_id(user_id):
    return str(user_id or "test_user").strip() or "test_user"


def safe_int(value, default=0):
    try:
        return max(0, int(value or default))
    except (TypeError, ValueError):
        return default


def parse_time(value):
    try:
        return datetime.strptime(value or "", "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return datetime.min


def record_from_row(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "poem_id": row["poem_id"],
        "duration_seconds": int(row["duration_seconds"] or 0),
        "created_at": row["created_at"],
    }


@router.post("/record")
def add_record(record: RecordIn):
    user_id = normalize_user_id(record.user_id)
    duration = safe_int(record.duration_seconds)
    created_at = now_text()
    connection = get_connection()
    try:
        with connection:
            poem = connection.execute(
                "SELECT 1 FROM poems WHERE id = ?", (record.poem_id,)
            ).fetchone()
            if not poem:
                raise HTTPException(
                    status_code=404,
                    detail=f"未找到古诗：{record.poem_id}",
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO users(user_id, age_level, age_range)
                VALUES (?, 'age_3_4', '3-4岁')
                """,
                (user_id,),
            )
            cursor = connection.execute(
                """
                INSERT INTO learning_records(
                    user_id, poem_id, duration_seconds, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (user_id, record.poem_id, duration, created_at),
            )
            row = connection.execute(
                "SELECT * FROM learning_records WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            consolidation = create_consolidation_if_missing(
                record.poem_id,
                user_id,
                connection=connection,
            )
            connection.execute(
                "UPDATE users SET updated_at = ? WHERE user_id = ?",
                (created_at, user_id),
            )
            new_record = record_from_row(row)
    finally:
        connection.close()

    return {
        "success": True,
        "message": "记录成功",
        "data": new_record,
        "consolidation": consolidation,
    }


@router.get("/record")
def get_records(user_id: Optional[str] = "test_user"):
    user_id = normalize_user_id(user_id)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT * FROM learning_records
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,),
        ).fetchall()
    finally:
        connection.close()
    data = [record_from_row(row) for row in rows]
    return {"success": True, "total": len(data), "data": data}


@router.get("/record/summary")
def get_learning_summary(user_id: str = "test_user"):
    user_id = normalize_user_id(user_id)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT r.*, p.title, p.author, p.dynasty, p.tags_json
            FROM learning_records AS r
            JOIN poems AS p ON p.id = r.poem_id
            WHERE r.user_id = ?
            ORDER BY r.id
            """,
            (user_id,),
        ).fetchall()
    finally:
        connection.close()

    records = [record_from_row(row) for row in rows]
    poem_summary = {}
    for row in rows:
        poem_id = row["poem_id"]
        duration = int(row["duration_seconds"] or 0)
        created_at = row["created_at"]
        created_time = parse_time(created_at)
        if poem_id not in poem_summary:
            poem_summary[poem_id] = {
                "id": poem_id,
                "poem_id": poem_id,
                "title": row["title"],
                "author": row["author"],
                "dynasty": row["dynasty"],
                "tags": json.loads(row["tags_json"] or "[]"),
                "latest_duration_seconds": duration,
                "total_duration_seconds": duration,
                "study_count": 1,
                "latest_time": created_at,
                "_latest_datetime": created_time,
            }
            continue

        item = poem_summary[poem_id]
        item["total_duration_seconds"] += duration
        item["study_count"] += 1
        if created_time >= item["_latest_datetime"]:
            item["latest_duration_seconds"] = duration
            item["latest_time"] = created_at
            item["_latest_datetime"] = created_time

    learned_poems = sorted(
        poem_summary.values(),
        key=lambda item: item["_latest_datetime"],
        reverse=True,
    )
    for item in learned_poems:
        item.pop("_latest_datetime", None)

    recent_records = sorted(
        records,
        key=lambda item: parse_time(item["created_at"]),
        reverse=True,
    )[:5]
    return {
        "success": True,
        "user_id": user_id,
        "learned_count": len(learned_poems),
        "record_count": len(records),
        "total_duration_seconds": sum(item["duration_seconds"] for item in records),
        "learned_poems": learned_poems,
        "recent_records": recent_records,
    }
