import re

from poem_catalog import normalize_poem_text


ALLOWED_KNOWLEDGE_TAGS = {
    "价值启蒙", "动态意象", "夸张修辞", "季节意象", "情感理解", "情绪感知",
    "想象能力", "意象理解", "文化常识", "方位认知", "比喻感知", "比喻理解",
    "生活常识", "生活画面", "生活观察", "画面理解", "简单哲理", "背诵积累",
    "自然意象", "自然认知", "节奏感知", "观察能力",
}
FORBIDDEN_TAGS = {"古诗", "诗词", "优美", "传统文化", "好诗", "儿童启蒙"}
TAG_ALIASES = {
    "月": "月亮", "江": "江河", "儿童": "童趣", "小娃": "童趣",
    "小孩": "童趣", "鸟叫": "鸟鸣", "春景": "春天景象",
    "秋景": "秋天景象", "雪景": "冬天景象", "情感": "情感表达",
    "观察": "自然观察", "生活场景": "生活画面",
}
CONTENT_TAG_RULES = (
    (("月",), "月亮"), (("莲", "荷", "芙蓉"), "莲花"),
    (("钓",), "钓鱼"), (("舟", "船", "艇"), "划船"),
    (("鸟", "莺", "鹂", "鹭", "雁", "燕"), "鸟鸣"),
    (("雨",), "风雨"), (("雪", "霜"), "冰雪"),
    (("山", "峰", "岭"), "山峰"), (("江", "河", "湖", "溪", "潭"), "江河湖泊"),
    (("花", "梅", "桃", "菊"), "花朵"), (("春",), "春天"),
    (("夏",), "夏天"), (("秋",), "秋天"), (("冬",), "冬天"),
    (("思乡", "故乡", "乡关", "乡心"), "思乡"),
    (("送", "别", "离"), "送别"), (("农", "田", "禾", "耕"), "劳动"),
)
SEASON_TAGS = {"春天", "夏天", "秋天", "冬天", "春天景象", "秋天景象", "冬天景象"}
NATURE_MARKERS = {"月亮", "莲花", "鸟鸣", "风雨", "冰雪", "山峰", "江河湖泊", "花朵", "自然", "山水", "山林"}
EMOTION_MARKERS = {"思乡", "送别", "友情", "亲情", "孤独", "忧愁", "情感表达"}
ACTION_MARKERS = {"钓鱼", "划船", "劳动", "登高", "旅行", "观察", "自然观察"}


def _clean_tag(tag, poem):
    value = re.sub(r"\s+", "", str(tag or "").strip())
    value = TAG_ALIASES.get(value, value)
    if not value or value in FORBIDDEN_TAGS:
        return ""
    if value in {poem.get("author"), poem.get("dynasty")}:
        return ""
    normalized = normalize_poem_text(value)
    content = normalize_poem_text("".join(poem.get("content") or []))
    if len(normalized) >= 3 and normalized in content:
        return ""
    return value


def normalize_tags(poem):
    result = []
    for tag in poem.get("tags") or []:
        value = _clean_tag(tag, poem)
        if value and value not in result:
            result.append(value)
    if len(result) < 2:
        content = "".join(poem.get("content") or [])
        for needles, label in CONTENT_TAG_RULES:
            if any(needle in content for needle in needles) and label not in result:
                result.append(label)
            if len(result) >= 2:
                break
    for tag in poem.get("theme_tags") or []:
        value = _clean_tag(tag, poem)
        if value and value not in result:
            result.append(value)
        if len(result) >= 2:
            break
    return result[:5]


def normalize_theme_tags(poem, tags):
    result = list(tags[:2])
    existing = []
    for tag in poem.get("theme_tags") or []:
        value = _clean_tag(tag, poem)
        if value and value not in tags and value not in existing:
            existing.append(value)
    marker = None
    if set(tags) & EMOTION_MARKERS:
        marker = "情感理解"
    elif set(tags) & ACTION_MARKERS:
        marker = "生活观察"
    elif set(tags) & (NATURE_MARKERS | SEASON_TAGS):
        marker = "自然观察"
    if marker in tags:
        marker = next(
            (value for value in ("画面理解", "观察能力", "情感表达") if value not in tags),
            None,
        )
    if marker and marker not in result:
        result.append(marker)
    for value in existing:
        if value not in result:
            result.append(value)
        if len(result) >= 4:
            break
    if len(result) < 3:
        result.append(next(
            value for value in ("画面理解", "观察能力", "情感表达")
            if value not in tags and value not in result
        ))
    return result[:4]


def normalize_knowledge_tags(poem, tags, theme_tags):
    evidence = set(tags) | set(theme_tags)
    result = []
    if evidence & SEASON_TAGS:
        result.append("季节意象")
    if evidence & NATURE_MARKERS:
        result.append("自然意象")
    if evidence & EMOTION_MARKERS:
        result.append("情感理解")
    if evidence & ACTION_MARKERS:
        result.append("生活观察")
    text = "".join(poem.get("tags") or []) + "".join(poem.get("theme_tags") or [])
    if "比喻" in text:
        result.append("比喻理解")
    if "夸张" in text:
        result.append("夸张修辞")
    if any(word in text for word in ("节日", "重阳", "清明", "文化", "典故")):
        result.append("文化常识")
    for old in poem.get("knowledge_tags") or []:
        if old in ALLOWED_KNOWLEDGE_TAGS:
            result.append(old)
    if not result:
        result.append("背诵积累")
    return list(dict.fromkeys(result))[:3]


def normalize_poem_metadata(poem):
    result = dict(poem)
    tags = normalize_tags(result)
    themes = normalize_theme_tags(result, tags)
    result["tags"] = tags
    result["theme_tags"] = themes
    result["knowledge_tags"] = normalize_knowledge_tags(result, tags, themes)
    return result


def validate_tag_metadata(poem):
    errors = []
    tags = poem.get("tags") or []
    themes = poem.get("theme_tags") or []
    knowledge = poem.get("knowledge_tags") or []
    if not 2 <= len(tags) <= 5:
        errors.append("tags 必须包含 2-5 项")
    if len(tags) != len(set(tags)):
        errors.append("tags 不得重复")
    if any(tag in FORBIDDEN_TAGS for tag in tags):
        errors.append("tags 含空泛或禁用标签")
    if not 2 <= len(themes) <= 4:
        errors.append("theme_tags 必须包含 2-4 项")
    reused = len(set(tags) & set(themes))
    if not 1 <= reused <= 2:
        errors.append("theme_tags 必须直接复用 tags 中的 1-2 项")
    if any(tag in FORBIDDEN_TAGS for tag in themes):
        errors.append("theme_tags 含空泛或禁用标签")
    if not 1 <= len(knowledge) <= 3:
        errors.append("knowledge_tags 必须包含 1-3 项")
    invalid = set(knowledge) - ALLOWED_KNOWLEDGE_TAGS
    if invalid:
        errors.append(f"knowledge_tags 含非法值：{','.join(sorted(invalid))}")
    if poem.get("age_level") not in {"age_3_4", "age_5_7"}:
        errors.append("age_level 无效")
    expected_range = {"age_3_4": "3-4岁", "age_5_7": "5-7岁"}.get(poem.get("age_level"))
    if expected_range and poem.get("age_range") != expected_range:
        errors.append("age_range 与 age_level 不对应")
    if poem.get("difficulty") not in {1, 2, 3}:
        errors.append("difficulty 只能是 1、2、3")
    return errors
