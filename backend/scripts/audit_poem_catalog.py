import json
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = (
    BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json"
)
REPORT_PATH = (
    BACKEND_DIR / "data_sources" / "generated" / "poem_data_quality_report.json"
)
REQUIRED_FIELDS = (
    "id",
    "title",
    "author",
    "dynasty",
    "content",
    "translation",
    "tags",
    "age_level",
    "age_range",
    "difficulty",
    "theme_tags",
    "knowledge_tags",
    "recommend_reason",
)
BASE_KNOWLEDGE_TAG = "背诵积累"
ALLOWED_KNOWLEDGE_TAGS = {
    "画面理解", "自然意象", "情感理解", "意象理解", "观察能力", "生活常识",
    "价值启蒙", "简单哲理", "夸张修辞", "比喻感知", "情绪感知", "想象能力",
    "自然认知", "节奏感知", "方位认知", "生活观察", "生活画面", "季节意象",
    "动态意象", "文化常识", "比喻理解",
}


def load_catalog():
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("候选诗库顶层必须是数组")
    return data


def is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def normalized_content(poem):
    return "".join(str(line) for line in poem.get("content") or [])


def main():
    poems = load_catalog()
    missing_fields = defaultdict(list)
    for poem in poems:
        for field in REQUIRED_FIELDS:
            if field not in poem or is_empty(poem.get(field)):
                missing_fields[field].append({
                    "id": poem.get("id"),
                    "title": poem.get("title"),
                })

    weak_theme_tags = []
    invalid_knowledge_tags = []
    theme_tag_counts = Counter()
    knowledge_tag_counts = Counter()
    for poem in poems:
        theme_tags = poem.get("theme_tags") or []
        knowledge_tags = poem.get("knowledge_tags") or []
        theme_tag_counts.update(theme_tags)
        knowledge_tag_counts.update(knowledge_tags)
        if theme_tags == ["古诗启蒙"]:
            weak_theme_tags.append({
                "id": poem.get("id"),
                "title": poem.get("title"),
                "theme_tags": theme_tags,
            })
        if (
            len(knowledge_tags) != 3
            or knowledge_tags[0] != BASE_KNOWLEDGE_TAG
            or not set(knowledge_tags[1:]) <= ALLOWED_KNOWLEDGE_TAGS
        ):
            invalid_knowledge_tags.append({
                "id": poem.get("id"),
                "title": poem.get("title"),
                "knowledge_tags": knowledge_tags,
            })

    title_groups = defaultdict(list)
    for poem in poems:
        title_groups[poem.get("title", "")].append(poem.get("id"))
    repeated_titles = {
        title: poem_ids
        for title, poem_ids in title_groups.items()
        if title and len(poem_ids) > 1
    }

    near_duplicate_content = []
    for index, left in enumerate(poems):
        left_text = normalized_content(left)
        for right in poems[index + 1:]:
            right_text = normalized_content(right)
            if not left_text or not right_text:
                continue
            ratio = SequenceMatcher(None, left_text, right_text).ratio()
            if ratio >= 0.92:
                near_duplicate_content.append({
                    "left": {"id": left.get("id"), "title": left.get("title")},
                    "right": {"id": right.get("id"), "title": right.get("title")},
                    "similarity": round(ratio, 4),
                })

    report = {
        "catalog_path": str(CATALOG_PATH),
        "total_count": len(poems),
        "age_counts": dict(Counter(poem.get("age_level") for poem in poems)),
        "difficulty_counts": dict(Counter(poem.get("difficulty") for poem in poems)),
        "missing_counts": {
            field: len(items) for field, items in sorted(missing_fields.items())
        },
        "missing_fields": dict(missing_fields),
        "quality_warnings": {
            "weak_theme_tag_count": len(weak_theme_tags),
            "weak_theme_tags": weak_theme_tags,
            "invalid_knowledge_tag_count": len(invalid_knowledge_tags),
            "invalid_knowledge_tags": invalid_knowledge_tags,
            "repeated_titles": repeated_titles,
            "near_duplicate_content": near_duplicate_content,
        },
        "tag_statistics": {
            "theme_tags": dict(theme_tag_counts.most_common()),
            "knowledge_tags": dict(knowledge_tag_counts.most_common()),
        },
        "recommended_next_actions": [
            "正式接口切换数据库前，使用现有接口回归测试150首读取结果。",
            "后续新增古诗时继续执行译文、普通标签和知识标签校验。",
        ],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "total_count": report["total_count"],
        "age_counts": report["age_counts"],
        "difficulty_counts": report["difficulty_counts"],
        "missing_counts": report["missing_counts"],
        "weak_theme_tag_count": len(weak_theme_tags),
        "invalid_knowledge_tag_count": len(invalid_knowledge_tags),
        "repeated_title_count": len(repeated_titles),
        "near_duplicate_pair_count": len(near_duplicate_content),
        "report_path": str(REPORT_PATH),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
