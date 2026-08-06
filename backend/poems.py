import json

from fastapi import APIRouter, HTTPException, Query

from database import get_connection

router = APIRouter()

def json_array(value):
    try:
        data = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def row_to_poem(row):
    """将 SQLite 行转换成与原 poems.json 相同的响应结构。"""
    result = {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "dynasty": row["dynasty"],
        "content": json_array(row["content_json"]),
        "translation": row["translation"],
        "tags": json_array(row["tags_json"]),
        "age_level": row["age_level"],
        "age_range": row["age_range"],
        "difficulty": row["difficulty"],
        "theme_tags": json_array(row["theme_tags_json"]),
        "knowledge_tags": json_array(row["knowledge_tags_json"]),
        "recommend_reason": row["recommend_reason"],
    }
    optional_fields = (
        "content_hash", "library_scope", "source_name", "source_url",
        "source_version", "verification_status", "content_complete",
        "recommend_eligible",
    )
    available = set(row.keys())
    for field in optional_fields:
        if field in available:
            result[field] = row[field]
    return result


def load_poems():
    """从 SQLite 读取全部古诗，按稳定 ID 排序。"""
    connection = get_connection()
    try:
        rows = connection.execute("SELECT * FROM poems ORDER BY id").fetchall()
        return [row_to_poem(row) for row in rows]
    finally:
        connection.close()

@router.get("/poems/search")
def search_poems(
    keyword: str = Query("", description="搜索关键词，支持标题、作者、朝代、诗句、标签"),
    author: str = Query("", description="作者筛选，例如：李白"),
    dynasty: str = Query("", description="朝代筛选，例如：唐"),
    tag: str = Query("", description="标签筛选，例如：月亮、思乡、儿童启蒙"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量")
):
    """
    古诗搜索接口

    支持：
    1. keyword 综合搜索：标题、作者、朝代、诗句、标签
    2. author 作者筛选
    3. dynasty 朝代筛选
    4. tag 标签筛选
    5. 分页

    示例：
    /poems/search?keyword=春
    /poems/search?author=李白
    /poems/search?dynasty=唐
    /poems/search?tag=思乡
    /poems/search?keyword=月&author=李白&dynasty=唐
    """
    poems = load_poems()

    result = []

    for poem in poems:
        title = poem.get("title", "")
        poem_author = poem.get("author", "")
        poem_dynasty = poem.get("dynasty", "")
        content = poem.get("content", [])
        tags = poem.get("tags", [])

        content_text = "".join(content) if isinstance(content, list) else str(content)
        tags_text = "".join(tags) if isinstance(tags, list) else str(tags)

        searchable_text = title + poem_author + poem_dynasty + content_text + tags_text

        # 关键词综合搜索
        if keyword and keyword not in searchable_text:
            continue

        # 作者筛选
        if author and author not in poem_author:
            continue

        # 朝代筛选
        if dynasty and dynasty not in poem_dynasty:
            continue

        # 标签筛选
        if tag and tag not in tags_text:
            continue

        result.append(poem)

    total = len(result)

    start = (page - 1) * page_size
    end = start + page_size
    page_data = result[start:end]

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "filters": {
            "keyword": keyword,
            "author": author,
            "dynasty": dynasty,
            "tag": tag
        },
        "data": [
            {
                "id": poem.get("id"),
                "title": poem.get("title"),
                "author": poem.get("author"),
                "dynasty": poem.get("dynasty"),
                "content_preview": "，".join(poem.get("content", [])[:2]) + "。",
                "tags": poem.get("tags", [])
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
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM poems WHERE id = ?",
            (poem_id,),
        ).fetchone()
        canonical_id = poem_id
        if row is None:
            alias = connection.execute(
                "SELECT poem_id FROM poem_aliases WHERE alias_id = ?",
                (poem_id,),
            ).fetchone()
            if alias:
                canonical_id = alias["poem_id"]
                row = connection.execute(
                    "SELECT * FROM poems WHERE id = ?",
                    (canonical_id,),
                ).fetchone()
    finally:
        connection.close()

    if row:
        return {
            "success": True,
            "data": {
                **row_to_poem(row),
                "poem_id": canonical_id,
                "requested_poem_id": poem_id,
            }
        }

    raise HTTPException(status_code=404, detail="诗词不存在")
