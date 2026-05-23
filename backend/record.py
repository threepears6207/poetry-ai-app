import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

DATA_DIR = Path(__file__).parent / "data"
RECORD_PATH = DATA_DIR / "records.json"
POEMS_PATH = DATA_DIR / "poems.json"


class RecordIn(BaseModel):
    """
    前端进入古诗详情页时，传给后端的数据
    """
    poem_id: str
    user_id: Optional[str] = "test_user"
    duration_seconds: Optional[int] = 0


def ensure_record_file():
    """
    确保 data 文件夹和 records.json 文件存在
    """
    DATA_DIR.mkdir(exist_ok=True)

    if not RECORD_PATH.exists():
        with open(RECORD_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_records():
    """
    读取学习记录
    """
    ensure_record_file()

    with open(RECORD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_json(path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_records(records):
    """
    保存学习记录
    """
    ensure_record_file()

    with open(RECORD_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


@router.post("/record")
def add_record(record: RecordIn):
    """
    添加学习记录

    前端进入古诗详情页时调用：
    POST /record

    请求体示例：
    {
      "poem_id": "poem_001",
      "user_id": "test_user",
      "duration_seconds": 0
    }
    """
    records = load_records()

    new_record = {
        "id": len(records) + 1,
        "user_id": record.user_id,
        "poem_id": record.poem_id,
        "duration_seconds": record.duration_seconds,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    records.append(new_record)
    save_records(records)

    return {
        "success": True,
        "message": "记录成功",
    }


@router.get("/record")
def get_records(user_id: Optional[str] = "test_user"):
    """
    查询某个用户的学习记录

    示例：
    GET /record?user_id=test_user
    """
    records = load_records()

    user_records = [
        item for item in records
        if item.get("user_id") == user_id
    ]

    return {
        "success": True,
        "total": len(user_records),
        "data": user_records
    }

@router.get("/record/summary")
def get_learning_summary(user_id: str = "test_user"):
    """
    获取用户学习统计信息。

    用途：
    1. 给家长页展示学习情况
    2. 给推荐算法提供基础数据
    3. 给后续学习报告功能使用
    """
    records = load_json(RECORD_PATH, [])
    poems = load_json(POEMS_PATH, [])

    user_records = [
        record for record in records
        if record.get("user_id") == user_id
    ]

    learned_poem_ids = []
    for record in user_records:
        poem_id = record.get("poem_id")
        if poem_id and poem_id not in learned_poem_ids:
            learned_poem_ids.append(poem_id)

    poem_map = {
        poem.get("id"): poem
        for poem in poems
    }

    learned_poems = []
    for poem_id in learned_poem_ids:
        poem = poem_map.get(poem_id)
        if poem:
            learned_poems.append({
                "id": poem.get("id"),
                "title": poem.get("title"),
                "author": poem.get("author"),
                "dynasty": poem.get("dynasty"),
                "tags": poem.get("tags", [])
            })

    total_duration_seconds = sum(
        int(record.get("duration_seconds", 0) or 0)
        for record in user_records
    )

    recent_records = user_records[-5:]
    recent_records.reverse()

    return {
        "success": True,
        "user_id": user_id,
        "learned_count": len(learned_poem_ids),
        "record_count": len(user_records),
        "total_duration_seconds": total_duration_seconds,
        "learned_poems": learned_poems,
        "recent_records": recent_records
    }