import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# 当前文件 poems.py 所在目录：backend
# 所以数据文件路径是 backend/data/poems.json
DATA_PATH = Path(__file__).parent / "data" / "poems.json"


def load_poems():
    """
    从 poems.json 中读取古诗数据。
    第一周先用 JSON 文件，后面再升级成数据库。
    """
    if not DATA_PATH.exists():
        return []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/poems/search")
def search_poems(
    keyword: str = Query("", description="搜索关键词，支持标题、作者、朝代、诗句、标签"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量")
):
    """
    古诗搜索接口

    示例：
    /poems/search?keyword=春
    /poems/search?keyword=李白
    /poems/search?keyword=月光
    """
    poems = load_poems()

    if keyword:
        result = []

        for poem in poems:
            title = poem.get("title", "")
            author = poem.get("author", "")
            dynasty = poem.get("dynasty", "")
            content_text = "".join(poem.get("content", []))
            tags_text = "".join(poem.get("tags", []))

            searchable_text = title + author + dynasty + content_text + tags_text

            if keyword in searchable_text:
                result.append(poem)
    else:
        result = poems

    total = len(result)

    start = (page - 1) * page_size
    end = start + page_size
    page_data = result[start:end]

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": poem.get("id"),
                "title": poem.get("title"),
                "author": poem.get("author"),
                "dynasty": poem.get("dynasty"),
                "content_preview": "，".join(poem.get("content", [])[:2]) + "。"
            }
            for poem in page_data
        ]
    }


@router.get("/poems/{poem_id}")
def get_poem_detail(poem_id: str):
    """
    古诗详情接口

    示例：
    /poems/poem_001
    /poems/poem_002
    """
    poems = load_poems()

    for poem in poems:
        if poem.get("id") == poem_id:
            return {
                "success": True,
                "data": poem
            }

    raise HTTPException(status_code=404, detail="诗词不存在")