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


def safe_int(value, default=0):
    """
    安全转整数，避免 None、空字符串导致报错
    """
    try:
        return int(value or default)
    except Exception:
        return default


def parse_time(time_text):
    """
    将 created_at 转为可比较的时间。
    如果老记录没有时间或格式异常，就给一个最小时间，避免报错。
    """
    if not time_text:
        return datetime.min

    try:
        return datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.min


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
      "duration_seconds": 30
    }
    """
    records = load_records()

    new_record = {
        "id": len(records) + 1,
        "user_id": record.user_id,
        "poem_id": record.poem_id,
        "duration_seconds": safe_int(record.duration_seconds, 0),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    records.append(new_record)
    save_records(records)

    return {
        "success": True,
        "message": "记录成功",
        "data": new_record
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

    家长端重点使用：
    1. 每首古诗的最新学习时长 latest_duration_seconds
    2. 每首古诗的总计学习时长 total_duration_seconds
    """
    records = load_json(RECORD_PATH, [])
    poems = load_json(POEMS_PATH, [])

    user_records = [
        record for record in records
        if record.get("user_id") == user_id
    ]

    poem_map = {
        poem.get("id"): poem
        for poem in poems
    }

    # 按 poem_id 汇总同一首诗的学习情况
    poem_summary_map = {}

    for record in user_records:
        poem_id = record.get("poem_id")

        if not poem_id:
            continue

        duration = safe_int(record.get("duration_seconds"), 0)
        created_at = record.get("created_at", "")
        created_time = parse_time(created_at)

        poem = poem_map.get(poem_id, {})

        if poem_id not in poem_summary_map:
            poem_summary_map[poem_id] = {
                "id": poem_id,
                "poem_id": poem_id,
                "title": poem.get("title", "未知古诗"),
                "author": poem.get("author", ""),
                "dynasty": poem.get("dynasty", ""),
                "tags": poem.get("tags", []),

                # 新增：家长端需要的两个核心指标
                "latest_duration_seconds": duration,
                "total_duration_seconds": duration,

                # 额外保留：方便展示和排序
                "study_count": 1,
                "latest_time": created_at,
                "_latest_datetime": created_time
            }
        else:
            item = poem_summary_map[poem_id]

            item["total_duration_seconds"] += duration
            item["study_count"] += 1

            # 如果当前记录时间更新，就更新“最新学习时长”
            if created_time >= item["_latest_datetime"]:
                item["latest_duration_seconds"] = duration
                item["latest_time"] = created_at
                item["_latest_datetime"] = created_time

    learned_poems = list(poem_summary_map.values())

    # 按最近学习时间倒序排列
    learned_poems.sort(
        key=lambda item: item.get("_latest_datetime", datetime.min),
        reverse=True
    )

    # 删除内部排序字段，避免前端看到多余内容
    for item in learned_poems:
        item.pop("_latest_datetime", None)

    total_duration_seconds = sum(
        safe_int(record.get("duration_seconds"), 0)
        for record in user_records
    )

    recent_records = sorted(
        user_records,
        key=lambda item: parse_time(item.get("created_at", "")),
        reverse=True
    )[:5]

    return {
        "success": True,
        "user_id": user_id,

        # 学过几首不同的诗
        "learned_count": len(learned_poems),

        # 总学习记录条数
        "record_count": len(user_records),

        # 所有诗的总学习时长
        "total_duration_seconds": total_duration_seconds,

        # 家长端主要用这个字段
        "learned_poems": learned_poems,

        # 最近 5 条原始学习记录
        "recent_records": recent_records
    }