import json
from collections import Counter
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from database import get_connection, initialize_database
from poem_cards import build_poem_card


router = APIRouter()

VALID_AGE_LEVELS = {
    "age_3_4": "3-4岁",
    "age_5_7": "5-7岁",
}

CATEGORY_KEYWORDS = {
    "spring": ("春天", "春日", "春景", "春风", "花", "柳", "燕"),
    "animal": ("动物", "鸟", "鹅", "鸡", "鸭", "蝉", "虫", "鱼", "蜂", "蝶", "雁", "鹭"),
    "nature": ("自然", "山水", "田园", "江河", "湖", "月亮", "花", "树", "草", "雪", "雨", "风", "云"),
}


class ReadingScoreIn(BaseModel):
    user_id: str = Field("test_user", description="用户ID")
    poem_id: str = Field(..., description="古诗ID")
    score: float = Field(..., ge=0, le=100, description="整首跟读平均分，范围0-100")
    source: str = Field("reading", description="评分来源，例如 reading / asr / manual")


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_array(value):
    try:
        data = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def row_to_poem(row):
    return {
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


def load_poems_from_db():
    initialize_database()
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT * FROM poems
            WHERE verification_status = 'verified'
              AND content_complete = 1
              AND recommend_eligible = 1
            ORDER BY id
            """
        ).fetchall()
        return [row_to_poem(row) for row in rows]
    finally:
        connection.close()


def ensure_user(user_id, age_level=None):
    user_id = str(user_id or "test_user").strip() or "test_user"
    connection = get_connection()
    try:
        with connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO users(user_id, age_level, age_range)
                VALUES (?, 'age_3_4', '3-4岁')
                """,
                (user_id,),
            )
            if age_level in VALID_AGE_LEVELS:
                connection.execute(
                    """
                    UPDATE users
                    SET age_level = ?, age_range = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (age_level, VALID_AGE_LEVELS[age_level], now_text(), user_id),
                )
        return dict(connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone())
    finally:
        connection.close()


def unique_list(items):
    result = []
    seen = set()
    for item in items or []:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def get_poem_learning_tags(poem):
    tags = poem.get("theme_tags") or poem.get("tags") or []
    excluded = {poem.get("author"), poem.get("dynasty")}
    return unique_list(tag for tag in tags if tag not in excluded)


def poem_matches_category(poem, category):
    if not category or category == "all":
        return True
    keywords = CATEGORY_KEYWORDS.get(category)
    if not keywords:
        return True
    text = "".join([
        str(poem.get("title", "")),
        "".join(poem.get("content", []) or []),
        "".join(poem.get("tags", []) or []),
        "".join(poem.get("theme_tags", []) or []),
    ])
    return any(keyword in text for keyword in keywords)


def load_user_state(user_id):
    connection = get_connection()
    try:
        score_rows = connection.execute(
            """
            SELECT poem_id, score, source, updated_at
            FROM reading_scores
            WHERE user_id = ?
            ORDER BY poem_id
            """,
            (user_id,),
        ).fetchall()
        reading_scores = {
            row["poem_id"]: {
                "score": round(float(row["score"]), 2),
                "source": row["source"],
                "updated_at": row["updated_at"],
            }
            for row in score_rows
        }

        learned_times = {}
        for row in connection.execute(
            """
            SELECT poem_id, MIN(created_at) AS learned_at
            FROM learning_records
            WHERE user_id = ?
            GROUP BY poem_id
            """,
            (user_id,),
        ).fetchall():
            learned_times[row["poem_id"]] = row["learned_at"]
        for row in score_rows:
            learned_times.setdefault(row["poem_id"], row["updated_at"])
        return reading_scores, learned_times
    finally:
        connection.close()


def calculate_tag_scores(reading_scores, poems):
    poem_map = {poem["id"]: poem for poem in poems}
    grouped = {}
    for poem_id, score_item in reading_scores.items():
        poem = poem_map.get(poem_id)
        if not poem:
            continue
        score = float(score_item["score"])
        for tag in get_poem_learning_tags(poem):
            grouped.setdefault(tag, {"scores": [], "poems": []})
            grouped[tag]["scores"].append(score)
            grouped[tag]["poems"].append({
                "poem_id": poem_id,
                "title": poem["title"],
                "score": round(score, 2),
            })

    result = {}
    for tag, item in grouped.items():
        scores = item["scores"]
        result[tag] = {
            "average_score": round(sum(scores) / len(scores), 2),
            "count": len(scores),
            "poems": item["poems"],
        }
    return result


def calculate_strong_tags(tag_scores, limit=5):
    result = [
        {
            "tag": tag,
            "average_score": item["average_score"],
            "count": item["count"],
        }
        for tag, item in tag_scores.items()
    ]
    result.sort(key=lambda item: (
        -float(item["average_score"]),
        -int(item["count"]),
        item["tag"],
    ))
    return result[:limit]


def build_profile(user_id, poems):
    user = ensure_user(user_id)
    reading_scores, learned_times = load_user_state(user_id)
    poem_map = {poem["id"]: poem for poem in poems}
    learned_poems = []
    for poem_id in sorted(learned_times):
        poem = poem_map.get(poem_id)
        if not poem:
            continue
        learned_poems.append({
            "poem_id": poem_id,
            "title": poem["title"],
            "age_level": poem["age_level"],
            "age_range": poem["age_range"],
            "theme_tags": get_poem_learning_tags(poem),
            "learned_at": learned_times[poem_id],
        })
    tag_scores = calculate_tag_scores(reading_scores, poems)
    strong_tags = calculate_strong_tags(tag_scores)
    return {
        "user_id": user_id,
        "age_level": user["age_level"],
        "age_range": user["age_range"],
        "learned_poems": learned_poems,
        "reading_scores": reading_scores,
        "tag_scores": tag_scores,
        "strong_tags": strong_tags,
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


def build_content_preview(poem):
    return "，".join(poem.get("content", [])[:2]) + "。"


def build_recommend_reason(poem, age_range, matched_tags, tag_scores):
    if matched_tags:
        text = "、".join(
            f"{tag}平均{tag_scores[tag]['average_score']}分"
            for tag in matched_tags[:3]
        )
        return f"孩子在{text}相关内容上表现较好，因此优先推荐同主题的《{poem['title']}》。"
    tags = get_poem_learning_tags(poem)
    if tags:
        return (
            f"《{poem['title']}》适合{age_range}儿童学习，"
            f"主题包含{'、'.join(tags[:3])}，并且孩子尚未学习过。"
        )
    return f"《{poem['title']}》适合{age_range}儿童学习，并且孩子尚未学习过。"


def format_recommend_poem(poem, age_range, tag_scores, strong_tags):
    strong_names = {item["tag"] for item in strong_tags}
    matched_tags = [tag for tag in get_poem_learning_tags(poem) if tag in strong_names]
    tag_match_score = sum(
        float(tag_scores[tag]["average_score"]) for tag in matched_tags
    )
    difficulty = int(poem.get("difficulty", 1) or 1)
    return {
        **poem,
        "poem_id": poem["id"],
        "content_preview": build_content_preview(poem),
        "matched_strong_tags": matched_tags,
        "tag_match_count": len(matched_tags),
        "tag_match_score": round(tag_match_score, 2),
        "recommend_score": round(100 - difficulty * 5 + min(40, tag_match_score / 5), 2),
        "recommend_reason": build_recommend_reason(
            poem, age_range, matched_tags, tag_scores
        ),
    }


def load_recommend_context(user_id, poems):
    poem_map = {poem["id"]: poem for poem in poems}
    connection = get_connection()
    try:
        recent_ids = [
            row["poem_id"]
            for row in connection.execute(
                """
                SELECT poem_id, MAX(created_at) AS latest
                FROM learning_records
                WHERE user_id = ?
                GROUP BY poem_id
                ORDER BY latest DESC
                LIMIT 8
                """,
                (user_id,),
            ).fetchall()
        ]
        reading_scores = {
            row["poem_id"]: float(row["score"])
            for row in connection.execute(
                "SELECT poem_id, score FROM reading_scores WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        }
        consolidations = {
            row["poem_id"]: {
                "status": row["status"],
                "next_review_date": row["next_review_date"],
            }
            for row in connection.execute(
                """
                SELECT poem_id, status, next_review_date
                FROM consolidations WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()
        }
    finally:
        connection.close()

    learned_ids = set(recent_ids) | set(reading_scores) | set(consolidations)
    preference_counts = Counter()
    for poem_id in recent_ids:
        poem = poem_map.get(poem_id)
        if poem:
            preference_counts.update(get_poem_learning_tags(poem))
    learned_difficulties = [
        int(poem_map[poem_id].get("difficulty", 1))
        for poem_id in learned_ids if poem_id in poem_map
    ]
    target_difficulty = (
        min(5, sum(learned_difficulties) / len(learned_difficulties) + 0.35)
        if learned_difficulties else 1.0
    )
    return {
        "learned_ids": learned_ids,
        "recent_ids": recent_ids,
        "reading_scores": reading_scores,
        "consolidations": consolidations,
        "preference_counts": preference_counts,
        "target_difficulty": target_difficulty,
    }


def diversify_recommendations(ranked, debug=False):
    """Greedily avoid adjacent cards with the same theme or author.

    Base relevance remains dominant. The penalty only chooses a more varied
    neighbour when candidates have reasonably close recommendation scores.
    """
    remaining = list(ranked)
    result = []
    while remaining:
        if not result:
            best_index = 0
            penalty = 0.0
        else:
            previous = result[-1]
            previous_tags = set(get_poem_learning_tags(previous))
            scored = []
            for index, item in enumerate(remaining):
                overlap = len(previous_tags & set(get_poem_learning_tags(item)))
                theme_penalty = min(18.0, overlap * 9.0)
                author_penalty = 7.0 if item.get("author") == previous.get("author") else 0.0
                current_penalty = theme_penalty + author_penalty
                adjusted = float(item["recommend_score"]) - current_penalty
                scored.append((adjusted, -current_penalty, -index, index, current_penalty))
            _, _, _, best_index, penalty = max(scored)
        selected = dict(remaining.pop(best_index))
        if debug:
            selected.setdefault("score_components", {})
            selected["score_components"]["list_diversity_penalty"] = round(-penalty, 2)
        result.append(selected)
    return result


def rank_recommendations(
    poems, context, age_level, category=None, exclude_ids=None, debug=False,
):
    exclude_ids = set(exclude_ids or [])
    poem_map = {poem["id"]: poem for poem in poems}
    last_poem = poem_map.get(context["recent_ids"][0]) if context["recent_ids"] else None
    last_tags = set(get_poem_learning_tags(last_poem)) if last_poem else set()
    last_author = last_poem.get("author") if last_poem else None
    today = date.today().isoformat()
    ranked = []

    for poem in poems:
        poem_id = poem["id"]
        if (
            poem.get("age_level") != age_level
            or poem_id in exclude_ids
            or not poem_matches_category(poem, category)
        ):
            continue
        learned = poem_id in context["learned_ids"]
        reading_score = context["reading_scores"].get(poem_id)
        consolidation = context["consolidations"].get(poem_id, {})
        next_review = consolidation.get("next_review_date") or ""
        due_review = bool(
            learned and (
                consolidation.get("status") == "待巩固"
                or (next_review and next_review <= today)
            )
        )
        weak = reading_score is not None and reading_score < 75
        if learned and not due_review and not weak:
            continue

        components = {"age_fit": 25.0}
        if not learned:
            components["new_content"] = 30.0
        if due_review:
            components["due_review"] = 45.0
        if weak:
            components["weak_item"] = min(35.0, 12.0 + (75 - reading_score) * 0.7)

        tags = get_poem_learning_tags(poem)
        preference = min(15.0, sum(context["preference_counts"].get(tag, 0) * 3 for tag in tags))
        if preference:
            components["recent_preference"] = preference
        difficulty = int(poem.get("difficulty", 1) or 1)
        components["difficulty_progression"] = max(
            0.0, 15.0 - abs(difficulty - context["target_difficulty"]) * 7.0
        )
        overlap = len(last_tags & set(tags))
        if overlap:
            components["repeat_theme_penalty"] = -min(24.0, overlap * 12.0)
        if last_author and poem.get("author") == last_author:
            components["repeat_author_penalty"] = -8.0

        total = sum(components.values())
        item = {
            **poem,
            **build_poem_card(poem, learned_state="learned" if learned else "unlearned"),
            "content_preview": build_content_preview(poem),
            "recommend_score": round(total, 2),
            "recommend_type": "review" if due_review or weak else "new",
            "review_state": "due" if due_review else ("weak" if weak else "none"),
        }
        if debug:
            item["score_components"] = {
                key: round(value, 2) for key, value in components.items()
            }
        ranked.append(item)

    ranked.sort(key=lambda item: (
        -float(item["recommend_score"]),
        int(item.get("difficulty", 5)),
        item["id"],
    ))
    return diversify_recommendations(ranked, debug)


@router.post("/profile/reading-score")
def update_reading_score(data: ReadingScoreIn):
    poems = load_poems_from_db()
    poem = next((item for item in poems if item["id"] == data.poem_id), None)
    if not poem:
        return {"success": False, "message": f"未找到古诗：{data.poem_id}"}

    user_id = str(data.user_id or "test_user").strip() or "test_user"
    ensure_user(user_id)
    score = round(float(data.score), 2)
    source = str(data.source or "reading").strip() or "reading"
    updated_at = now_text()
    connection = get_connection()
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO reading_scores(user_id, poem_id, score, source, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, poem_id) DO UPDATE SET
                    score = excluded.score,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (user_id, data.poem_id, score, source, updated_at),
            )
            connection.execute(
                "UPDATE users SET updated_at = ? WHERE user_id = ?",
                (updated_at, user_id),
            )
    finally:
        connection.close()

    profile = build_profile(user_id, poems)
    return {
        "success": True,
        "message": "跟读评分已写入数据库，并已更新用户画像标签分数",
        "user_id": user_id,
        "poem_id": data.poem_id,
        "title": poem["title"],
        "score": score,
        "tag_scores": profile["tag_scores"],
        "strong_tags": profile["strong_tags"],
    }


@router.get("/profile/{user_id}")
def get_user_profile(user_id: str):
    poems = load_poems_from_db()
    return {"success": True, "data": build_profile(user_id, poems)}


@router.get("/recommend")
def recommend_poems(
    user_id: str = Query("test_user", description="用户ID"),
    age_level: Optional[str] = Query(None, description="年龄层：age_3_4 或 age_5_7"),
    limit: int = Query(5, ge=1, le=20, description="推荐数量"),
    category: Optional[str] = Query(None, description="可选分类：spring / animal / nature"),
    exclude_ids: str = Query("", description="换一首时排除的 poem_id，逗号分隔"),
    debug: bool = Query(False, description="是否返回内部评分明细"),
):
    poems = load_poems_from_db()
    user = ensure_user(user_id, age_level if age_level in VALID_AGE_LEVELS else None)
    current_age_level = (
        age_level if age_level in VALID_AGE_LEVELS else user["age_level"]
    )
    current_age_range = VALID_AGE_LEVELS[current_age_level]
    profile = build_profile(user_id, poems)
    context = load_recommend_context(user_id, poems)
    learned_ids = context["learned_ids"]
    excluded = {value.strip() for value in exclude_ids.split(",") if value.strip()}
    candidates = rank_recommendations(
        poems, context, current_age_level, category, excluded, debug,
    )
    selected = candidates[:limit]
    return {
        "success": True,
        "user_id": user_id,
        "age_level": current_age_level,
        "age_range": current_age_range,
        "category": category or "all",
        "learned_count": len(learned_ids),
        "candidate_count": len(candidates),
        "tag_scores": profile["tag_scores"],
        "strong_tags": profile["strong_tags"],
        "total": len(selected),
        "poems": selected,
        "data": selected,
        "recommendations": selected,
        "message": "已按适龄、待温习/薄弱项、近期偏好、难度递进和内容多样性排序",
    }


@router.get("/recommend/today")
def recommend_today(
    user_id: str = Query("test_user", description="用户ID"),
    age_level: Optional[str] = Query(None, description="年龄层"),
    exclude_poem_id: str = Query("", description="换一首时排除当前 poem_id"),
    debug: bool = Query(False, description="是否返回评分明细"),
):
    result = recommend_poems(
        user_id=user_id,
        age_level=age_level,
        limit=1,
        category=None,
        exclude_ids=exclude_poem_id,
        debug=debug,
    )
    selected = result["poems"]
    return {
        "success": bool(selected),
        "poem": selected[0] if selected else None,
        "poems": selected,
        "user_id": result["user_id"],
        "age_level": result["age_level"],
    }
