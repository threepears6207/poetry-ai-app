import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

DATA_DIR = Path(__file__).parent / "data"
CONSOLIDATION_PATH = DATA_DIR / "consolidations.json"
POEMS_PATH = DATA_DIR / "poems.json"


class ConsolidationResultIn(BaseModel):
    """
    前端巩固练习完成后传给后端的数据
    """
    poem_id: str
    user_id: Optional[str] = "test_user"
    passed: bool


def today_text():
    return datetime.now().strftime("%Y-%m-%d")


def date_after_days(days: int):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_consolidation_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not CONSOLIDATION_PATH.exists():
        with open(CONSOLIDATION_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_json(path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_consolidations():
    ensure_consolidation_file()

    with open(CONSOLIDATION_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_consolidations(records):
    ensure_consolidation_file()

    with open(CONSOLIDATION_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def get_poem_map():
    poems = load_json(POEMS_PATH, [])

    return {
        poem.get("id"): poem
        for poem in poems
    }


def find_consolidation(records, user_id: str, poem_id: str):
    for item in records:
        if item.get("user_id") == user_id and item.get("poem_id") == poem_id:
            return item

    return None


def create_consolidation_if_missing(poem_id: str, user_id: str = "test_user"):
    """
    如果某首诗还没有巩固记录，就创建一条。
    如果已经有记录，不覆盖已有进度。
    """
    records = load_consolidations()

    existing = find_consolidation(records, user_id, poem_id)

    if existing:
        return existing

    new_item = {
        "id": len(records) + 1,
        "user_id": user_id,
        "poem_id": poem_id,
        "status": "待巩固",
        "practice_count": 0,
        "next_review_date": today_text(),
        "created_at": now_text(),
        "updated_at": now_text()
    }

    records.append(new_item)
    save_consolidations(records)

    return new_item


def is_due_today(next_review_date: str):
    """
    next_review_date <= 今天，表示今天到期需要复习
    """
    if not next_review_date:
        return True

    return next_review_date <= today_text()


def get_next_interval_days(practice_count: int):
    """
    通过后的复习间隔：
    第 1 次通过：1 天后
    第 2 次通过：3 天后
    第 3 次通过：7 天后，并标记已掌握
    """
    if practice_count <= 1:
        return 1

    if practice_count == 2:
        return 3

    return 7


@router.get("/consolidation/list")
def get_consolidation_list(user_id: str = "test_user"):
    """
    返回所有已学诗的巩固状态列表。
    """
    records = load_consolidations()
    poem_map = get_poem_map()

    user_records = [
        item for item in records
        if item.get("user_id") == user_id
    ]

    result = []

    for item in user_records:
        poem_id = item.get("poem_id")
        poem = poem_map.get(poem_id, {})
        next_review_date = item.get("next_review_date", "")

        result.append({
            "id": item.get("id"),
            "user_id": item.get("user_id"),
            "poem_id": poem_id,
            "title": poem.get("title", "未知古诗"),
            "author": poem.get("author", ""),
            "dynasty": poem.get("dynasty", ""),
            "tags": poem.get("tags", []),
            "status": item.get("status", "待巩固"),
            "practice_count": int(item.get("practice_count", 0) or 0),
            "next_review_date": next_review_date,
            "due_today": is_due_today(next_review_date),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at")
        })

    total_count = len(result)
    mastered_count = len([item for item in result if item.get("status") == "已掌握"])
    pending_count = len([item for item in result if item.get("status") == "待巩固"])
    due_today_count = len([item for item in result if item.get("due_today")])

    return {
        "success": True,
        "user_id": user_id,
        "total_count": total_count,
        "mastered_count": mastered_count,
        "pending_count": pending_count,
        "due_today_count": due_today_count,
        "data": result
    }


@router.get("/consolidation/status/{poem_id}")
def get_consolidation_status(poem_id: str, user_id: str = "test_user"):
    """
    查询单首诗的掌握状态。
    """
    records = load_consolidations()
    poem_map = get_poem_map()

    item = find_consolidation(records, user_id, poem_id)
    poem = poem_map.get(poem_id, {})

    if not item:
        return {
            "success": True,
            "user_id": user_id,
            "poem_id": poem_id,
            "title": poem.get("title", "未知古诗"),
            "author": poem.get("author", ""),
            "dynasty": poem.get("dynasty", ""),
            "status": "未学习",
            "practice_count": 0,
            "next_review_date": None,
            "due_today": False
        }

    next_review_date = item.get("next_review_date", "")

    return {
        "success": True,
        "user_id": user_id,
        "poem_id": poem_id,
        "title": poem.get("title", "未知古诗"),
        "author": poem.get("author", ""),
        "dynasty": poem.get("dynasty", ""),
        "status": item.get("status", "待巩固"),
        "practice_count": int(item.get("practice_count", 0) or 0),
        "next_review_date": next_review_date,
        "due_today": is_due_today(next_review_date),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at")
    }


@router.post("/consolidation/result")
def update_consolidation_result(result: ConsolidationResultIn):
    """
    前端做完跟读或连连看后提交结果。

    passed = true:
    - 练习次数 +1
    - 按 1 天、3 天、7 天更新下次复习时间
    - 练满 3 次后状态变为“已掌握”

    passed = false:
    - 状态不变
    - 下次复习时间改为明天
    """
    records = load_consolidations()

    item = find_consolidation(records, result.user_id, result.poem_id)

    if not item:
        create_consolidation_if_missing(
            poem_id=result.poem_id,
            user_id=result.user_id
        )
        records = load_consolidations()
        item = find_consolidation(records, result.user_id, result.poem_id)

    if result.passed:
        current_count = int(item.get("practice_count", 0) or 0)
        new_count = current_count + 1

        item["practice_count"] = new_count

        if new_count >= 3:
            item["status"] = "已掌握"
            item["next_review_date"] = date_after_days(7)
        else:
            item["status"] = "待巩固"
            item["next_review_date"] = date_after_days(get_next_interval_days(new_count))

    else:
        item["next_review_date"] = date_after_days(1)

    item["updated_at"] = now_text()

    save_consolidations(records)

    return {
        "success": True,
        "message": "巩固结果已更新",
        "data": item
    }