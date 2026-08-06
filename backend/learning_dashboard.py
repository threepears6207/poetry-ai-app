from datetime import date
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from database import get_connection, initialize_database


router = APIRouter()


class SuppressPracticePromptIn(BaseModel):
    user_id: Optional[str] = "test_user"


def _user_id(value):
    return str(value or "test_user").strip() or "test_user"


def _ensure_user(connection, user_id):
    connection.execute(
        """
        INSERT OR IGNORE INTO users(user_id, age_level, age_range)
        VALUES (?, 'age_3_4', '3-4岁')
        """,
        (user_id,),
    )


def reminder_status(user_id="test_user", db_path=None, current_date=None):
    initialize_database(db_path)
    user_id = _user_id(user_id)
    day = current_date or date.today().isoformat()
    connection = get_connection(db_path)
    try:
        _ensure_user(connection, user_id)
        learned_today = connection.execute(
            """
            SELECT COUNT(DISTINCT poem_id) FROM learning_records
            WHERE user_id=? AND substr(created_at, 1, 10)=?
            """,
            (user_id, day),
        ).fetchone()[0]
        pending_count = connection.execute(
            """
            SELECT COUNT(*) FROM consolidations
            WHERE user_id=? AND (
                status='待巩固' OR next_review_date='' OR next_review_date<=?
            )
            """,
            (user_id, day),
        ).fetchone()[0]
        setting = connection.execute(
            """
            SELECT practice_prompt_suppressed FROM daily_reminder_settings
            WHERE user_id=? AND setting_date=?
            """,
            (user_id, day),
        ).fetchone()
        suppressed = bool(setting[0]) if setting else False
    finally:
        connection.close()
    return {
        "success": True,
        "user_id": user_id,
        "date": day,
        "learned_today_count": learned_today,
        "pending_review_count": pending_count,
        "practice_prompt_suppressed": suppressed,
        "show_practice_prompt": bool(learned_today and pending_count and not suppressed),
        "practice_entry_badge": bool(pending_count),
        "practice_entry_badge_count": pending_count,
    }


def suppress_prompt_today(user_id="test_user", db_path=None, current_date=None):
    initialize_database(db_path)
    user_id = _user_id(user_id)
    day = current_date or date.today().isoformat()
    connection = get_connection(db_path)
    try:
        with connection:
            _ensure_user(connection, user_id)
            connection.execute(
                """
                INSERT INTO daily_reminder_settings(
                    user_id, setting_date, practice_prompt_suppressed, updated_at
                ) VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, setting_date) DO UPDATE SET
                    practice_prompt_suppressed=1,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, day),
            )
    finally:
        connection.close()
    return reminder_status(user_id, db_path, day)


def parent_overview(user_id="test_user", db_path=None, current_date=None):
    initialize_database(db_path)
    user_id = _user_id(user_id)
    day = current_date or date.today().isoformat()
    connection = get_connection(db_path)
    try:
        today_rows = connection.execute(
            """
            SELECT p.id AS poem_id, p.title, p.author,
                   COUNT(r.id) AS session_count,
                   SUM(r.duration_seconds) AS duration_seconds
            FROM learning_records AS r
            JOIN poems AS p ON p.id=r.poem_id
            WHERE r.user_id=? AND substr(r.created_at, 1, 10)=?
            GROUP BY p.id, p.title, p.author
            ORDER BY MAX(r.created_at) DESC
            """,
            (user_id, day),
        ).fetchall()
        learned_count = connection.execute(
            "SELECT COUNT(DISTINCT poem_id) FROM learning_records WHERE user_id=?",
            (user_id,),
        ).fetchone()[0]
        pending_count = connection.execute(
            """
            SELECT COUNT(*) FROM consolidations
            WHERE user_id=? AND (status='待巩固' OR next_review_date='' OR next_review_date<=?)
            """,
            (user_id, day),
        ).fetchone()[0]
        practice = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(reading_completed) AS reading_done,
                   SUM(connection_completed) AS connection_done,
                   SUM(CASE WHEN collection_state='color' THEN 1 ELSE 0 END) AS reinforced
            FROM consolidations WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()
        recent = connection.execute(
            """
            SELECT r.id, r.poem_id, p.title, p.author,
                   r.duration_seconds, r.created_at
            FROM learning_records AS r
            JOIN poems AS p ON p.id=r.poem_id
            WHERE r.user_id=?
            ORDER BY r.created_at DESC, r.id DESC LIMIT 10
            """,
            (user_id,),
        ).fetchall()
    finally:
        connection.close()

    total = int(practice["total"] or 0)
    reading_done = int(practice["reading_done"] or 0)
    return {
        "success": True,
        "user_id": user_id,
        "date": day,
        "today_learning": {
            "poem_count": len(today_rows),
            "session_count": sum(int(row["session_count"] or 0) for row in today_rows),
            "duration_seconds": sum(int(row["duration_seconds"] or 0) for row in today_rows),
            "poems": [dict(row) for row in today_rows],
        },
        "learned_poem_count": learned_count,
        "pending_review_count": pending_count,
        "reading_completion": {
            "completed_count": reading_done,
            "total_count": total,
            "rate": round(reading_done / total, 4) if total else 0.0,
        },
        "connection_completed_count": int(practice["connection_done"] or 0),
        "reinforced_poem_count": int(practice["reinforced"] or 0),
        "recent_records": [dict(row) for row in recent],
    }


@router.get("/reminders/status")
def get_reminder_status(user_id="test_user"):
    return reminder_status(user_id)


@router.post("/reminders/suppress-today")
def suppress_today(data: SuppressPracticePromptIn):
    return suppress_prompt_today(data.user_id)


@router.get("/parent/overview")
def get_parent_overview(user_id="test_user"):
    return parent_overview(user_id)
