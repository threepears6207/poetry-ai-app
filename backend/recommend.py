import json
import random
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter()

DATA_DIR = Path(__file__).parent / "data"
POEMS_PATH = DATA_DIR / "poems.json"
RECORD_PATH = DATA_DIR / "records.json"


def load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/recommend")
def recommend_poems(
    user_id: str = Query("test_user", description="用户ID"),
    limit: int = Query(5, ge=1, le=20, description="推荐数量")
):
    """
    推荐用户没有看过的古诗。
    简单逻辑：
    1. 读取全部古诗
    2. 读取用户学习记录
    3. 排除用户已经看过的诗
    4. 随机返回若干首
    """
    poems = load_json(POEMS_PATH, [])
    records = load_json(RECORD_PATH, [])

    viewed_poem_ids = {
        item.get("poem_id")
        for item in records
        if item.get("user_id") == user_id
    }

    unviewed_poems = [
        poem for poem in poems
        if poem.get("id") not in viewed_poem_ids
    ]

    # 如果都看过了，就从全部诗里推荐，避免前端空白
    candidates = unviewed_poems if unviewed_poems else poems

    random.shuffle(candidates)
    selected = candidates[:limit]

    return {
        "success": True,
        "user_id": user_id,
        "total": len(selected),
        "data": [
            {
                "id": poem.get("id"),
                "title": poem.get("title"),
                "author": poem.get("author"),
                "dynasty": poem.get("dynasty"),
                "content_preview": "，".join(poem.get("content", [])[:2]) + "。",
                "tags": poem.get("tags", [])
            }
            for poem in selected
        ]
    }