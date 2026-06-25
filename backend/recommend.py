import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

DATA_DIR = Path(__file__).parent / "data"
POEMS_PATH = DATA_DIR / "poems.json"
RECORD_PATH = DATA_DIR / "records.json"
USER_PROFILES_PATH = DATA_DIR / "user_profiles.json"


VALID_AGE_LEVELS = {
    "age_3_4": "3-4岁",
    "age_5_7": "5-7岁"
}


class ReadingScoreIn(BaseModel):
    user_id: str = Field("test_user", description="用户ID")
    poem_id: str = Field(..., description="古诗ID")
    score: float = Field(..., ge=0, le=100, description="跟读评分，范围 0-100")
    source: str = Field("reading", description="评分来源，例如 reading / asr / manual")


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


def unique_list(items):
    result = []
    seen = set()

    for item in items or []:
        if not item:
            continue

        if item not in seen:
            result.append(item)
            seen.add(item)

    return result


def get_poem_learning_tags(poem):
    """
    获取用于用户画像和推荐算法的标签。

    优先使用 theme_tags。
    如果没有 theme_tags，再使用 tags。

    这样可以减少把作者名、朝代等普通标签误当成兴趣强项的问题。
    """
    theme_tags = poem.get("theme_tags", [])

    if theme_tags:
        return unique_list(theme_tags)

    tags = poem.get("tags", [])

    exclude_tags = {
        poem.get("author"),
        poem.get("dynasty"),
        "李白",
        "杜甫",
        "王维",
        "唐",
        "宋",
        "清",
        "汉"
    }

    filtered_tags = [
        tag for tag in tags
        if tag and tag not in exclude_tags
    ]

    return unique_list(filtered_tags)


def ensure_user_profiles_file():
    """
    确保用户画像文件存在。

    用户画像结构：
    1. user_id：用户ID
    2. age_level：年龄层
    3. age_range：年龄范围
    4. learned_poems：已学古诗
    5. reading_scores：每首诗跟读评分
    6. tag_scores：由跟读评分反推出的标签平均分
    7. strong_tags：孩子表现较好的标签
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
    如果不存在该用户，就自动创建一个默认 3-4 岁用户画像。
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


def normalize_reading_scores(reading_scores):
    """
    reading_scores 兼容两种格式：

    1. {"poem_001": 85}
    2. {"poem_001": {"score": 85, "source": "manual", "updated_at": "..."}}
    """
    result = {}

    for poem_id, value in (reading_scores or {}).items():
        score = None

        if isinstance(value, (int, float)):
            score = float(value)

        elif isinstance(value, dict):
            raw_score = value.get("score")

            if isinstance(raw_score, (int, float)):
                score = float(raw_score)

        if score is None:
            continue

        if score < 0:
            score = 0

        if score > 100:
            score = 100

        result[poem_id] = score

    return result


def get_learned_poem_ids_from_records(user_id: str):
    """
    从 records.json 中读取孩子已经学过的诗。

    这样即使 user_profiles.json 还没有完整维护，
    也能根据现有学习记录排除已学古诗。
    """
    records = load_json(RECORD_PATH, [])
    learned_ids = set()

    for item in records:
        if item.get("user_id") == user_id:
            poem_id = item.get("poem_id")
            if poem_id:
                learned_ids.add(poem_id)

    return learned_ids


def sync_profile_learned_poems(profile, poems, learned_ids):
    """
    将已学诗同步到用户画像 learned_poems。
    """
    poem_map = {
        poem.get("id"): poem
        for poem in poems
    }

    old_items = profile.get("learned_poems", [])
    old_learned_ids = normalize_learned_poem_ids(old_items)

    old_learned_map = {}

    for item in old_items:
        if isinstance(item, dict):
            poem_id = item.get("poem_id") or item.get("id")
            if poem_id:
                old_learned_map[poem_id] = item

    merged_ids = old_learned_ids | learned_ids

    learned_poems = []

    for poem_id in sorted(merged_ids):
        poem = poem_map.get(poem_id, {})
        old_item = old_learned_map.get(poem_id, {})

        learned_poems.append({
            "poem_id": poem_id,
            "title": poem.get("title", old_item.get("title", "未知古诗")),
            "age_level": poem.get("age_level", old_item.get("age_level", "")),
            "age_range": poem.get("age_range", old_item.get("age_range", "")),
            "theme_tags": get_poem_learning_tags(poem),
            "learned_at": old_item.get("learned_at", now_text())
        })

    profile["learned_poems"] = learned_poems


def calculate_tag_scores(profile, poems):
    """
    根据孩子学过的每首诗的跟读评分，反推出每个标签的平均分。

    例子：
    《静夜思》85分，标签：月亮、思乡
    《古朗月行》72分，标签：月亮、童趣

    得到：
    月亮 = (85 + 72) / 2 = 78.5
    思乡 = 85
    童趣 = 72
    """
    poem_map = {
        poem.get("id"): poem
        for poem in poems
    }

    reading_scores = normalize_reading_scores(profile.get("reading_scores", {}))

    tag_score_temp = {}

    for poem_id, score in reading_scores.items():
        poem = poem_map.get(poem_id)

        if not poem:
            continue

        tags = get_poem_learning_tags(poem)

        for tag in tags:
            if tag not in tag_score_temp:
                tag_score_temp[tag] = {
                    "scores": [],
                    "poems": []
                }

            tag_score_temp[tag]["scores"].append(score)
            tag_score_temp[tag]["poems"].append({
                "poem_id": poem_id,
                "title": poem.get("title", ""),
                "score": score
            })

    tag_scores = {}

    for tag, item in tag_score_temp.items():
        scores = item["scores"]

        if not scores:
            continue

        average_score = sum(scores) / len(scores)

        tag_scores[tag] = {
            "average_score": round(average_score, 2),
            "count": len(scores),
            "poems": item["poems"]
        }

    return tag_scores


def calculate_strong_tags(tag_scores, limit=5):
    """
    根据标签平均分找出强项标签。

    这里取平均分最高的前几个标签。
    数据少的时候也能正常给出推荐依据。
    """
    strong_tags = []

    for tag, item in tag_scores.items():
        strong_tags.append({
            "tag": tag,
            "average_score": item.get("average_score", 0),
            "count": item.get("count", 0)
        })

    strong_tags.sort(
        key=lambda item: (
            -float(item.get("average_score", 0)),
            -int(item.get("count", 0)),
            item.get("tag", "")
        )
    )

    return strong_tags[:limit]


def refresh_profile_tag_scores(profile, profiles, poems):
    """
    更新用户画像中的 tag_scores 和 strong_tags。
    """
    tag_scores = calculate_tag_scores(profile, poems)
    strong_tags = calculate_strong_tags(tag_scores)

    profile["tag_scores"] = tag_scores
    profile["strong_tags"] = strong_tags
    profile["updated_at"] = now_text()

    save_user_profiles(profiles)

    return tag_scores, strong_tags


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


def build_recommend_reason(poem, age_range, matched_tags, tag_scores):
    title = poem.get("title", "这首诗")

    if matched_tags:
        tag_parts = []

        for tag in matched_tags:
            score_info = tag_scores.get(tag, {})
            average_score = score_info.get("average_score")

            if average_score is not None:
                tag_parts.append(f"{tag}平均{average_score}分")
            else:
                tag_parts.append(tag)

        tag_text = "、".join(tag_parts[:3])

        return f"孩子在{tag_text}相关内容上表现较好，因此优先推荐同主题的《{title}》。"

    theme_tags = get_poem_learning_tags(poem)

    if theme_tags:
        theme_text = "、".join(theme_tags[:3])
        return f"《{title}》适合{age_range}儿童学习，主题包含{theme_text}，并且孩子尚未学习过。"

    return f"《{title}》适合{age_range}儿童学习，并且孩子尚未学习过。"


def format_recommend_poem(poem, age_range, tag_scores, strong_tags):
    """
    统一推荐结果格式。

    保留原接口字段：
    data / total / content_preview

    新增第二层推荐字段：
    matched_strong_tags
    tag_match_count
    tag_match_score
    recommend_score
    recommend_reason
    """
    difficulty = int(poem.get("difficulty", 1) or 1)

    poem_tags = get_poem_learning_tags(poem)

    strong_tag_names = {
        item.get("tag")
        for item in strong_tags
        if item.get("tag")
    }

    matched_tags = [
        tag
        for tag in poem_tags
        if tag in strong_tag_names
    ]

    tag_match_score = 0

    for tag in matched_tags:
        tag_match_score += float(tag_scores.get(tag, {}).get("average_score", 0))

    base_score = 100 - difficulty * 5

    # recommend_score 主要用于展示。
    # tag_match_score 主要用于排序。
    recommend_score = base_score + min(40, tag_match_score / 5)

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

        "matched_strong_tags": matched_tags,
        "tag_match_count": len(matched_tags),
        "tag_match_score": round(tag_match_score, 2),
        "recommend_score": round(recommend_score, 2),
        "recommend_reason": build_recommend_reason(
            poem=poem,
            age_range=age_range,
            matched_tags=matched_tags,
            tag_scores=tag_scores
        )
    }


@router.post("/profile/reading-score")
def update_reading_score(data: ReadingScoreIn):
    """
    记录用户对某首诗的跟读评分。

    这个接口是第二层推荐的数据来源。

    示例：
    {
      "user_id": "test_user",
      "poem_id": "poem_002",
      "score": 85,
      "source": "manual"
    }
    """
    poems = load_json(POEMS_PATH, [])

    poem_map = {
        poem.get("id"): poem
        for poem in poems
    }

    poem = poem_map.get(data.poem_id)

    if not poem:
        return {
            "success": False,
            "message": f"未找到古诗：{data.poem_id}"
        }

    profile, profiles = get_or_create_user_profile(data.user_id)

    reading_scores = profile.get("reading_scores", {})

    reading_scores[data.poem_id] = {
        "score": round(float(data.score), 2),
        "source": data.source,
        "updated_at": now_text()
    }

    profile["reading_scores"] = reading_scores

    # 有跟读评分的诗，自动视为已学过
    learned_ids = normalize_learned_poem_ids(profile.get("learned_poems", []))
    learned_ids.add(data.poem_id)

    sync_profile_learned_poems(
        profile=profile,
        poems=poems,
        learned_ids=learned_ids
    )

    tag_scores, strong_tags = refresh_profile_tag_scores(
        profile=profile,
        profiles=profiles,
        poems=poems
    )

    return {
        "success": True,
        "message": "跟读评分已记录，并已更新用户画像标签分数",
        "user_id": data.user_id,
        "poem_id": data.poem_id,
        "title": poem.get("title", ""),
        "score": round(float(data.score), 2),
        "tag_scores": tag_scores,
        "strong_tags": strong_tags
    }


@router.get("/profile/{user_id}")
def get_user_profile(user_id: str):
    """
    查看用户画像，方便调试第二层推荐。
    """
    poems = load_json(POEMS_PATH, [])

    profile, profiles = get_or_create_user_profile(user_id)

    learned_from_profile = normalize_learned_poem_ids(profile.get("learned_poems", []))
    learned_from_records = get_learned_poem_ids_from_records(user_id)
    learned_from_scores = set(
        normalize_reading_scores(profile.get("reading_scores", {})).keys()
    )

    learned_ids = learned_from_profile | learned_from_records | learned_from_scores

    sync_profile_learned_poems(
        profile=profile,
        poems=poems,
        learned_ids=learned_ids
    )

    refresh_profile_tag_scores(
        profile=profile,
        profiles=profiles,
        poems=poems
    )

    return {
        "success": True,
        "data": profile
    }


@router.get("/recommend")
def recommend_poems(
    user_id: str = Query("test_user", description="用户ID"),
    age_level: Optional[str] = Query(None, description="年龄层：age_3_4 或 age_5_7"),
    limit: int = Query(5, ge=1, le=20, description="推荐数量")
):
    """
    第二层个性化推荐。

    推荐规则：

    第一层：
    1. 根据年龄层 age_level 筛选候选诗；
    2. 排除已经学过的诗。

    第二层：
    3. 根据已学诗的跟读评分，反推标签平均分；
    4. 找出孩子表现较好的 strong_tags；
    5. 在候选诗中，优先推荐与 strong_tags 重合的古诗。
    """
    poems = load_json(POEMS_PATH, [])

    profile, profiles = get_or_create_user_profile(user_id)

    current_age_level = validate_age_level(
        input_age_level=age_level,
        profile_age_level=profile.get("age_level")
    )

    current_age_range = VALID_AGE_LEVELS.get(current_age_level, "3-4岁")

    # 如果接口传入新的年龄层，就同步到用户画像
    if profile.get("age_level") != current_age_level:
        profile["age_level"] = current_age_level
        profile["age_range"] = current_age_range

    learned_from_profile = normalize_learned_poem_ids(profile.get("learned_poems", []))
    learned_from_records = get_learned_poem_ids_from_records(user_id)
    learned_from_scores = set(
        normalize_reading_scores(profile.get("reading_scores", {})).keys()
    )

    learned_ids = learned_from_profile | learned_from_records | learned_from_scores

    # 同步已学诗
    sync_profile_learned_poems(
        profile=profile,
        poems=poems,
        learned_ids=learned_ids
    )

    # 根据跟读评分计算标签平均分和强项标签
    tag_scores, strong_tags = refresh_profile_tag_scores(
        profile=profile,
        profiles=profiles,
        poems=poems
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

        candidates.append(
            format_recommend_poem(
                poem=poem,
                age_range=current_age_range,
                tag_scores=tag_scores,
                strong_tags=strong_tags
            )
        )

    # 第二层排序：
    # 1. 标签匹配分越高越靠前；
    # 2. 匹配标签数量越多越靠前；
    # 3. 难度越低越靠前；
    # 4. id 稳定排序。
    candidates.sort(
        key=lambda item: (
            -float(item.get("tag_match_score", 0)),
            -int(item.get("tag_match_count", 0)),
            int(item.get("difficulty", 1)),
            item.get("id", "")
        )
    )

    selected = candidates[:limit]

    return {
        "success": True,
        "user_id": user_id,
        "age_level": current_age_level,
        "age_range": current_age_range,

        "learned_count": len(learned_ids),
        "candidate_count": len(candidates),

        "tag_scores": tag_scores,
        "strong_tags": strong_tags,

        # 兼容原来的前端字段
        "total": len(selected),
        "data": selected,

        # 新推荐字段，后续前端也可以使用
        "recommendations": selected,

        "message": "已根据年龄层、已学记录和跟读强项标签返回第二层推荐结果"
    }