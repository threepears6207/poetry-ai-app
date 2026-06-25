import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()

DATA_DIR = Path(__file__).parent / "data"
POEMS_PATH = DATA_DIR / "poems.json"
RECORD_PATH = DATA_DIR / "records.json"
USER_PROFILES_PATH = DATA_DIR / "user_profiles.json"


VALID_AGE_LEVELS = {
    "age_3_4": "3-4岁",
    "age_5_7": "5-7岁"
}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    DATA_DIR.mkdir(exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_user_profiles_file():
    """
    确保用户画像文件存在。

    第一层推荐目前主要使用：
    1. user_id
    2. age_level
    3. learned_poems

    第二层推荐后续再扩展：
    1. reading_scores：每首诗跟读分数
    2. tag_scores：标签平均分
    3. strong_tags：孩子学得好的标签
    """
    DATA_DIR.mkdir(exist_ok=True)

    if not USER_PROFILES_PATH.exists():
        default_profiles = [
            {
                "user_id": "test_user",
                "age_level": "age_3_4",
                "age_range": "3-4岁",
                "learned_poems": [],
                "reading_scores": {},
                "tag_scores": {},
                "strong_tags": [],
                "created_at": now_text(),
                "updated_at": now_text()
            }
        ]

        save_json(USER_PROFILES_PATH, default_profiles)


def load_user_profiles():
    ensure_user_profiles_file()
    return load_json(USER_PROFILES_PATH, [])


def save_user_profiles(profiles):
    save_json(USER_PROFILES_PATH, profiles)


def get_or_create_user_profile(user_id: str):
    """
    获取用户画像。
    如果没有该用户，则自动创建一个默认 3-4 岁用户画像。
    """
    profiles = load_user_profiles()

    for profile in profiles:
        if profile.get("user_id") == user_id:
            return profile, profiles

    new_profile = {
        "user_id": user_id,
        "age_level": "age_3_4",
        "age_range": "3-4岁",
        "learned_poems": [],
        "reading_scores": {},
        "tag_scores": {},
        "strong_tags": [],
        "created_at": now_text(),
        "updated_at": now_text()
    }

    profiles.append(new_profile)
    save_user_profiles(profiles)

    return new_profile, profiles


def normalize_learned_poem_ids(learned_poems):
    """
    learned_poems 兼容两种格式：

    1. ["poem_001", "poem_002"]
    2. [{"poem_id": "poem_001"}, {"poem_id": "poem_002"}]
    """
    learned_ids = set()

    for item in learned_poems or []:
        if isinstance(item, str):
            learned_ids.add(item)

        elif isinstance(item, dict):
            poem_id = item.get("poem_id") or item.get("id")
            if poem_id:
                learned_ids.add(poem_id)

    return learned_ids


def get_learned_poem_ids_from_records(user_id: str):
    """
    从 records.json 中读取孩子已经学过的诗。

    这样即使 user_profiles.json 还没有完全维护，
    也能根据现有学习记录排除已学过古诗。
    """
    records = load_json(RECORD_PATH, [])

    learned_ids = set()

    for item in records:
        if item.get("user_id") == user_id:
            poem_id = item.get("poem_id")
            if poem_id:
                learned_ids.add(poem_id)

    return learned_ids


def sync_profile_learned_poems(profile, profiles, poems, learned_ids):
    """
    将 records.json 中识别到的已学诗同步到用户画像 learned_poems。

    这样用户画像里会记录：
    这个孩子已经学过哪些古诗。
    """
    poem_map = {
        poem.get("id"): poem
        for poem in poems
    }

    old_learned_ids = normalize_learned_poem_ids(profile.get("learned_poems", []))
    merged_ids = old_learned_ids | learned_ids

    learned_poems = []

    for poem_id in sorted(merged_ids):
        poem = poem_map.get(poem_id, {})

        learned_poems.append({
            "poem_id": poem_id,
            "title": poem.get("title", "未知古诗"),
            "age_level": poem.get("age_level", ""),
            "age_range": poem.get("age_range", ""),
            "theme_tags": poem.get("theme_tags", poem.get("tags", [])),
            "learned_at": now_text()
        })

    profile["learned_poems"] = learned_poems
    profile["updated_at"] = now_text()

    save_user_profiles(profiles)


def validate_age_level(input_age_level: Optional[str], profile_age_level: Optional[str]):
    """
    年龄层优先级：
    1. 如果接口传入合法 age_level，用接口传入的；
    2. 否则用用户画像里的 age_level；
    3. 如果都没有，默认 age_3_4。
    """
    if input_age_level in VALID_AGE_LEVELS:
        return input_age_level

    if profile_age_level in VALID_AGE_LEVELS:
        return profile_age_level

    return "age_3_4"


def build_content_preview(poem):
    content = poem.get("content", [])

    if isinstance(content, list):
        return "，".join(content[:2]) + "。"

    if isinstance(content, str):
        return content[:20]

    return ""


def build_recommend_reason(poem, age_range):
    title = poem.get("title", "这首诗")
    theme_tags = poem.get("theme_tags", poem.get("tags", []))

    if theme_tags:
        theme_text = "、".join(theme_tags[:3])
        return f"《{title}》适合{age_range}儿童学习，主题包含{theme_text}，并且孩子尚未学习过。"

    return f"《{title}》适合{age_range}儿童学习，并且孩子尚未学习过。"


def format_recommend_poem(poem, age_range):
    """
    统一推荐结果格式。
    保留原接口字段，同时增加年龄层和推荐解释字段。
    """
    difficulty = int(poem.get("difficulty", 1) or 1)

    return {
        "id": poem.get("id"),
        "poem_id": poem.get("id"),
        "title": poem.get("title"),
        "author": poem.get("author"),
        "dynasty": poem.get("dynasty"),
        "content": poem.get("content", []),
        "content_preview": build_content_preview(poem),
        "translation": poem.get("translation", ""),
        "tags": poem.get("tags", []),

        "age_level": poem.get("age_level", ""),
        "age_range": poem.get("age_range", ""),
        "difficulty": difficulty,
        "theme_tags": poem.get("theme_tags", poem.get("tags", [])),
        "knowledge_tags": poem.get("knowledge_tags", []),

        # 第一层推荐暂时只根据年龄层和是否已学推荐
        # 分数这里只作为展示用，第二层再根据标签强项调整
        "recommend_score": 100 - difficulty * 5,
        "recommend_reason": build_recommend_reason(poem, age_range)
    }


@router.get("/recommend")
def recommend_poems(
    user_id: str = Query("test_user", description="用户ID"),
    age_level: Optional[str] = Query(None, description="年龄层：age_3_4 或 age_5_7"),
    limit: int = Query(5, ge=1, le=20, description="推荐数量")
):
    """
    第一层个性化推荐。

    当前规则：
    1. 用户画像记录年龄层 age_level；
    2. 读取学习记录 records.json；
    3. 读取用户画像 learned_poems；
    4. 按年龄层筛选古诗；
    5. 排除已经学过的古诗；
    6. 返回候选推荐诗。

    示例：
    GET /recommend?user_id=test_user&age_level=age_3_4
    GET /recommend?user_id=test_user&age_level=age_5_7
    """
    poems = load_json(POEMS_PATH, [])
    profile, profiles = get_or_create_user_profile(user_id)

    current_age_level = validate_age_level(
        input_age_level=age_level,
        profile_age_level=profile.get("age_level")
    )

    current_age_range = VALID_AGE_LEVELS.get(current_age_level, "3-4岁")

    # 如果接口传入了新的年龄层，就同步到用户画像
    if profile.get("age_level") != current_age_level:
        profile["age_level"] = current_age_level
        profile["age_range"] = current_age_range
        profile["updated_at"] = now_text()
        save_user_profiles(profiles)

    learned_from_profile = normalize_learned_poem_ids(profile.get("learned_poems", []))
    learned_from_records = get_learned_poem_ids_from_records(user_id)

    learned_ids = learned_from_profile | learned_from_records

    # 把 records.json 里的已学诗同步进用户画像
    sync_profile_learned_poems(
        profile=profile,
        profiles=profiles,
        poems=poems,
        learned_ids=learned_ids
    )

    candidates = []

    for poem in poems:
        poem_id = poem.get("id")

        if not poem_id:
            continue

        # 第一层规则 1：年龄层必须匹配
        if poem.get("age_level") != current_age_level:
            continue

        # 第一层规则 2：排除已经学过的诗
        if poem_id in learned_ids:
            continue

        candidates.append(poem)

    # 第一层排序：难度低的优先，其次按 id 稳定排序
    candidates.sort(
        key=lambda poem: (
            int(poem.get("difficulty", 1) or 1),
            poem.get("id", "")
        )
    )

    selected = candidates[:limit]

    result_data = [
        format_recommend_poem(poem, current_age_range)
        for poem in selected
    ]

    return {
        "success": True,
        "user_id": user_id,
        "age_level": current_age_level,
        "age_range": current_age_range,

        # 已学过几首
        "learned_count": len(learned_ids),

        # 当前年龄层下，排除已学后的候选数量
        "candidate_count": len(candidates),

        # 兼容原来的前端字段
        "total": len(result_data),
        "data": result_data,

        # 新推荐接口字段，后续前端也可以改用这个
        "recommendations": result_data,

        "message": "已根据年龄层匹配并排除已学古诗，返回第一层推荐结果"
    }