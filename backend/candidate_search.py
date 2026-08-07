import json
import re
from difflib import SequenceMatcher
from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from database import get_connection, initialize_database
from poem_catalog import normalize_poem_text
from poem_cards import build_poem_card
from poems import row_to_poem


router = APIRouter()

SCENE_EXPANSIONS = {
    "月": ("月亮", "夜晚", "思乡"), "夜": ("夜晚", "月亮"),
    "山": ("山水", "山林", "登高", "自然"), "云": ("云", "山水", "自然"),
    "湖": ("湖景", "水面", "山水", "自然"), "河": ("江河", "水", "自然"),
    "江": ("江河", "水", "山水"), "水": ("水", "水面", "自然"),
    "花": ("花", "花草", "春天", "自然"), "春": ("春天", "花", "鸟"),
    "鸟": ("鸟鸣", "动物", "自然"), "树": ("树", "山林", "自然"),
    "草": ("草", "花草", "春天"), "雪": ("雪", "冬天", "自然"),
    "雨": ("雨景", "雨", "自然"), "夕阳": ("夕阳", "傍晚"),
    "太阳": ("日", "日出", "景色"), "田": ("田园", "乡村", "农事"),
    "船": ("船帆", "江河", "旅行"), "瀑布": ("瀑布", "山水"),
}
SEASON_MAP = {
    "spring": "春天", "summer": "夏天", "autumn": "秋天", "winter": "冬天",
    "春": "春天", "夏": "夏天", "秋": "秋天", "冬": "冬天",
}
MOOD_MAP = {
    "peaceful": "宁静", "quiet": "宁静", "happy": "轻快心情",
    "sad": "忧愁", "homesick": "思乡", "lonely": "孤独",
    "宁静": "宁静", "快乐": "轻快心情", "思乡": "思乡", "孤独": "孤独",
}


class SceneAnalysisInput(BaseModel):
    objects: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    season: str = ""
    mood: str = ""


class PoemAnalysisInput(BaseModel):
    title: str = ""
    author: str = ""
    dynasty: str = ""
    content: List[str] = Field(default_factory=list)
    translation: str = ""


class ImageAnalysisInput(BaseModel):
    content_type: Literal["poem_text", "scene"]
    poem: Optional[PoemAnalysisInput] = None
    poem_text: str = ""
    recognized_text: str = ""
    recognized_title: str = ""
    recognized_author: str = ""
    objects: List[str] = Field(default_factory=list)
    scene_tags: List[str] = Field(default_factory=list)
    scene: Optional[SceneAnalysisInput] = None
    season: str = ""
    mood: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    age_level: Optional[Literal["age_3_4", "age_5_7"]] = None
    limit: int = Field(default=3, ge=1, le=3)
    debug: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_input_contract(cls, raw):
        """Accept the compact contract while preserving existing client payloads."""
        values = dict(raw or {})
        raw_type = values.get("content_type") or values.get("type")
        raw_type = {
            "text_poem": "poem_text",
            "handwritten": "poem_text",
            "poem": "poem_text",
        }.get(raw_type, raw_type)

        poem = values.get("poem")
        if isinstance(poem, BaseModel):
            poem = poem.model_dump()
        poem = poem if isinstance(poem, dict) else {}
        poem_content = poem.get("content") or []
        poem_text = (
            values.get("poem_text") or values.get("recognized_text")
            or "".join(str(line) for line in poem_content if line)
        )
        values["poem_text"] = poem_text
        values["recognized_text"] = values.get("recognized_text") or poem_text
        values["recognized_title"] = values.get("recognized_title") or poem.get("title") or ""
        values["recognized_author"] = values.get("recognized_author") or poem.get("author") or ""

        scene = values.get("scene")
        if isinstance(scene, dict):
            values["objects"] = values.get("objects") or scene.get("objects") or []
            values["scene_tags"] = (
                values.get("scene_tags") or scene.get("tags") or scene.get("scene_tags") or []
            )
            values["season"] = values.get("season") or scene.get("season") or ""
            values["mood"] = values.get("mood") or scene.get("mood") or ""

        has_text = bool(poem_text or values.get("recognized_title") or values.get("recognized_author"))
        if not raw_type:
            raw_type = "poem_text" if has_text else "scene"
        values["content_type"] = raw_type
        return values


def _unique(values):
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _load_recommendable_poems(db_path=None):
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            """
            SELECT * FROM poems
            WHERE verification_status='verified' AND content_complete=1
              AND recommend_eligible=1
            ORDER BY id
            """
        ).fetchall()
        return [row_to_poem(row) for row in rows]
    finally:
        connection.close()


def _text_score(poem, request):
    recognized = normalize_poem_text(request.recognized_text)
    title_hint = normalize_poem_text(request.recognized_title)
    author_hint = normalize_poem_text(request.recognized_author)
    title = normalize_poem_text(poem.get("title", ""))
    author = normalize_poem_text(poem.get("author", ""))
    lines = [normalize_poem_text(line) for line in poem.get("content", [])]
    content = "".join(lines)
    score = 0.0
    evidence = []

    if title_hint and title:
        similarity = SequenceMatcher(None, title_hint, title).ratio()
        if title_hint == title:
            score += 0.42
            evidence.append("title_exact")
        elif similarity >= 0.8:
            score += 0.25 * similarity
            evidence.append("title_similar")
    if author_hint and author and (author_hint == author or author_hint in author or author in author_hint):
        score += 0.08
        evidence.append("author")
    if recognized:
        if title and title in recognized:
            score += 0.25
            evidence.append("title_in_text")
        if author and author in recognized:
            score += 0.05
            evidence.append("author_in_text")
        if len(recognized) >= 4 and recognized in content:
            score += 0.72
            evidence.append("text_fragment")
        elif content and content in recognized:
            score += 0.78
            evidence.append("full_content")
        else:
            matched_lines = sum(bool(line and line in recognized) for line in lines)
            if matched_lines:
                score += min(0.65, matched_lines * 0.22)
                evidence.append("poem_lines")
            similarity = SequenceMatcher(None, recognized, content).ratio() if content else 0
            if similarity >= 0.42:
                score += min(0.45, similarity * 0.5)
                evidence.append("fuzzy_text")
    return min(score, 1.0), evidence


def _scene_terms(request):
    raw = _unique(request.objects + request.scene_tags)
    expanded = list(raw)
    for tag in raw:
        for key, values in SCENE_EXPANSIONS.items():
            if key in tag:
                expanded.extend(values)
    season = SEASON_MAP.get(request.season.lower(), SEASON_MAP.get(request.season, request.season))
    mood = MOOD_MAP.get(request.mood.lower(), MOOD_MAP.get(request.mood, request.mood))
    if season:
        expanded.append(season)
    if mood:
        expanded.append(mood)
    return _unique(expanded), season, mood


def _scene_score(poem, request):
    terms, season, mood = _scene_terms(request)
    if not terms:
        return 0.0, []
    tags = _unique(
        poem.get("tags", []) + poem.get("theme_tags", []) + poem.get("knowledge_tags", [])
    )
    normalized_tags = [normalize_poem_text(tag) for tag in tags]
    title = normalize_poem_text(poem.get("title", ""))
    content = normalize_poem_text("".join(poem.get("content", [])))
    matched = []
    score = 0.0
    for term in terms:
        clean = normalize_poem_text(term)
        if not clean:
            continue
        if any(clean == tag for tag in normalized_tags):
            score += 0.13
            matched.append(term)
        elif any(clean in tag or tag in clean for tag in normalized_tags if len(tag) >= 2):
            score += 0.08
            matched.append(term)
        elif clean in title:
            score += 0.11
            matched.append(term)
        elif len(clean) >= 2 and clean in content:
            score += 0.04
            matched.append(term)
    if season and normalize_poem_text(season) in normalized_tags:
        score += 0.08
    if mood and normalize_poem_text(mood) in normalized_tags:
        score += 0.06
    return min(score, 1.0), _unique(matched)


def _poem_card(item, debug=False):
    poem = item["poem"]
    card = build_poem_card(poem)
    if debug:
        card.update({
            "match_score": round(item["score"], 4),
            "text_score": round(item["text_score"], 4),
            "scene_score": round(item["scene_score"], 4),
            "match_sources": item["sources"],
        })
    return card


def search_candidates(request: ImageAnalysisInput, db_path=None):
    has_text = bool(normalize_poem_text(
        request.recognized_text + request.recognized_title + request.recognized_author
    ))
    has_scene = bool(request.objects or request.scene_tags or request.season or request.mood)
    if not has_text and not has_scene:
        return {"success": False, "status": "retake", "error_code": "insufficient_input", "poems": []}
    if request.confidence < 0.3 and not has_text:
        return {"success": False, "status": "retake", "error_code": "low_confidence", "poems": []}

    use_text = request.content_type == "poem_text" and has_text
    use_scene = request.content_type == "scene" and has_scene
    text_weight = 1.0
    scene_weight = 1.0
    ranked = []
    for poem in _load_recommendable_poems(db_path):
        text_score, text_evidence = _text_score(poem, request) if use_text else (0.0, [])
        scene_score, scene_evidence = _scene_score(poem, request) if use_scene else (0.0, [])
        score = text_score * text_weight + scene_score * scene_weight
        if request.age_level and poem.get("age_level") == request.age_level:
            score += 0.04
        sources = []
        if text_evidence:
            sources.append("text")
        if scene_evidence:
            sources.append("scene")
        if score >= 0.18 and sources:
            ranked.append({
                "poem": poem, "score": min(score, 1.0), "text_score": text_score,
                "scene_score": scene_score, "sources": sources,
            })
    ranked.sort(key=lambda item: (
        -item["score"], item["poem"].get("difficulty", 5), item["poem"]["id"]
    ))
    selected = ranked[:request.limit]
    if not selected or selected[0]["score"] < 0.28:
        return {"success": False, "status": "retake", "error_code": "no_reliable_match", "poems": []}
    if request.content_type == "poem_text" and selected[0]["text_score"] >= 0.7:
        second_score = selected[1]["text_score"] if len(selected) > 1 else 0.0
        if selected[0]["text_score"] - second_score >= 0.12:
            selected = selected[:1]
    return {
        "success": True, "status": "ok", "error_code": None,
        "poems": [_poem_card(item, request.debug) for item in selected],
    }


@router.post("/poems/candidates")
def find_poem_candidates(request: ImageAnalysisInput):
    return search_candidates(request)
