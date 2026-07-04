import copy
import json
import re
import time
import urllib.request
from pathlib import Path

try:
    from opencc import OpenCC
except ImportError as error:
    raise SystemExit(
        "缺少候选库构建依赖，请先执行："
        "python -m pip install -r backend/data_sources/requirements.txt"
    ) from error


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data_sources" / "children_poems_75_manifest.json"
CURRENT_POEMS_PATH = ROOT / "data" / "poems.json"
OUTPUT_DIR = ROOT / "data_sources" / "generated"
OUTPUT_PATH = OUTPUT_DIR / "children_poems_candidates.json"
REPORT_PATH = OUTPUT_DIR / "children_poems_report.json"

SOURCE_COMMIT = "b8594f81a89752241442f2ce267d6f66f96704ee"
SOURCE_BASE = (
    "https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/"
    f"{SOURCE_COMMIT}/%E8%92%99%E5%AD%A6/"
)
SOURCE_FILES = ("qianjiashi.json", "tangshisanbaishou.json")
KNOWLEDGE_BASE_COMMIT = "b34b4388cf8d3981571e73a418e3ff24bef38f6b"
KNOWLEDGE_BASE_URL = (
    "https://raw.githubusercontent.com/dudulittle/"
    "ChinesePoetryTreasure-troveKnowledgeBase/"
    f"{KNOWLEDGE_BASE_COMMIT}/troveKnowledgeBase.txt"
)

AGE_3_4_ORDERS = {1, 4, 5, 10, 17, 18, 38, 42, 63, 73, 74}
AGE_5_7_ORDERS = {
    2, 3, 6, 7, 9, 14, 19, 20, 22, 23, 25, 27, 31, 35, 37,
    39, 40, 43, 44, 45, 48, 49, 50, 53, 55, 58, 61, 62, 64,
    65, 68, 69, 70, 72,
}

TOPIC_BY_TITLE = {
    "友情": {"赠汪伦", "别董大", "芙蓉楼送辛渐", "送元二使安西", "黄鹤楼送孟浩然之广陵"},
    "思乡": {"静夜思", "回乡偶书", "泊船瓜洲", "九月九日忆山东兄弟"},
    "亲情": {"游子吟", "九月九日忆山东兄弟"},
    "劳动": {"悯农", "蜂", "乡村四月", "四时田园杂兴"},
    "节日": {"元日", "清明", "九月九日忆山东兄弟"},
    "儿童": {"咏鹅", "池上", "小儿垂钓", "所见", "村居"},
    "成长": {"长歌行", "登鹳雀楼", "观书有感"},
    "品格": {"墨梅", "石灰吟", "竹石", "己亥杂诗"},
    "家国": {"出塞", "凉州词", "塞下曲", "夏日绝句", "示儿", "秋夜将晓出篱门迎凉有感", "题临安邸"},
}

KEYWORD_TAGS = {
    "春天": ("春", "桃花", "柳", "莺"),
    "夏天": ("夏", "荷", "莲", "蜻蜓", "六月"),
    "秋天": ("秋", "枫", "霜"),
    "冬天": ("冬", "雪", "冰"),
    "月亮": ("月",),
    "山水": ("山", "江", "河", "湖", "溪", "泉", "瀑布", "潭"),
    "动物": ("鸟", "鹅", "鱼", "鸭", "蝉", "猿", "黄鹂", "白鹭", "鸳鸯", "牛", "马", "蜂", "蝶"),
    "田园": ("田", "村", "农", "稻", "麦", "桑"),
    "雨景": ("雨",),
    "花草": ("花", "草", "莲", "荷", "梅", "竹", "柳"),
}

EXTENSION_BLOCKED_TERMS = (
    "妓", "妾", "少妇", "美人", "佳人", "红妆", "艳色", "嫁", "妻",
    "醉", "酒", "宴", "宫", "殿", "皇帝", "君王", "陛下", "侍郎",
    "太守", "宰相", "征战", "战场", "将军", "兵", "军", "杀", "血",
    "尸", "鬼", "死", "弓刀", "戈", "剑", "逃", "贬", "谪",
    "哭", "泪", "断肠", "肠断", "怨", "恨", "愁", "禅", "僧", "寺",
)
EXTENSION_PREFERRED_CHARS = (
    "春夏秋冬花草山水风雨月云鸟鱼鹅牛马童柳梅竹松荷莲雪"
    "日星江湖溪泉蝶蝉燕黄鹂白鹭田村"
)
EXTENSION_BLOCKED_TITLES = {
    "与史朗中饮听黄鹤楼上吹笛", "与朱山人", "易水送别", "清平调词",
    "逢侠者", "思君恩", "和晋陵陆承相", "春宿左省", "洛阳道",
    "答李浣", "访袁拾遗不遇", "夜送赵纵", "竹楼", "禹庙",
    "蜀道后期", "秋夜寄丘员外", "送郭司仓", "旅怀", "罢相作",
    "咏史", "直中书省", "真玉堂作", "寄左省杜拾遗", "上高侍郎",
    "宫中题", "题邸间壁", "题淮南寺", "题竹林寺", "宿云门寺阁",
    "送毛伯温", "题壁", "观李固请司马弟山水图", "答五陵太守",
    "春夜别友人", "送天师", "闻笛", "送友人入蜀", "杜少府之任蜀州",
    "游小园不值", "茅檐", "玄都观桃花", "再游玄都观", "旅夜书怀",
}
AUTHOR_CORRECTIONS = {
    "张佑": "张祜",
    "耿𣲗": "耿湋",
    "张文潜": "张耒",
}

converter = OpenCC("t2s")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def fetch_bytes(url: str):
    last_error = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "poetry-ai-app-data-builder"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as error:
            last_error = error
            time.sleep(attempt + 1)
    raise RuntimeError(f"下载开源数据失败：{url}，{last_error}") from last_error


def fetch_json(url: str):
    return json.loads(fetch_bytes(url).decode("utf-8"))


def normalized(value: str) -> str:
    value = converter.convert(str(value or ""))
    value = value.replace("古朗月行节选", "古朗月行")
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def collect_strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(collect_strings(item))
        return result
    if isinstance(value, dict):
        if "paragraphs" in value:
            return collect_strings(value["paragraphs"])
        result = []
        for item in value.values():
            result.extend(collect_strings(item))
        return result
    return []


def split_poem_lines(paragraphs):
    lines = []
    for paragraph in collect_strings(paragraphs):
        paragraph = converter.convert(paragraph)
        paragraph = re.sub(r"[（(][^）)]*(?:一作|又作|原作)[^）)]*[）)]", "", paragraph)
        for line in re.split(r"[，。！？；：,.!?;:]", paragraph):
            line = line.strip().strip("“”‘’\"'")
            if line:
                lines.append(line)
    return lines


def extract_source_entries(source_file: str, data):
    entries = []

    def walk(value):
        if isinstance(value, dict):
            if "author" in value and "paragraphs" in value:
                lines = split_poem_lines(value.get("paragraphs", []))
                if lines:
                    entries.append({
                        "collection": source_file,
                        "repository": "chinese-poetry/chinese-poetry",
                        "license": "MIT",
                        "commit": SOURCE_COMMIT,
                        "path": f"蒙学/{source_file}",
                        "title": converter.convert(str(value.get("chapter", ""))).strip(),
                        "author": converter.convert(str(value.get("author", ""))).strip(),
                        "lines": lines,
                    })
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return entries


def extract_knowledge_base_entries(text: str):
    entries = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("启用"):
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) != 3:
            continue
        _, title, content = parts
        lines = split_poem_lines([content])
        if not lines or content.startswith("请问"):
            continue
        entries.append({
            "collection": "troveKnowledgeBase.txt",
            "repository": "dudulittle/ChinesePoetryTreasure-troveKnowledgeBase",
            "license": "MIT",
            "commit": KNOWLEDGE_BASE_COMMIT,
            "path": "troveKnowledgeBase.txt",
            "title": title,
            "author": "",
            "lines": lines,
        })
    return entries


def choose_source(manifest_item, entries):
    expected_first = normalized(manifest_item["first_line"])
    expected_author = normalized(manifest_item["author"])
    expected_title = normalized(manifest_item["title"])
    candidates = []

    for entry in entries:
        if not entry["lines"]:
            continue
        actual_first = normalized(entry["lines"][0])
        actual_author = normalized(entry["author"])
        actual_title = normalized(entry["title"])
        if expected_first != actual_first:
            continue
        if actual_author and expected_author not in actual_author and actual_author not in expected_author:
            continue
        title_matches = expected_title in actual_title or actual_title in expected_title
        if not actual_author and not title_matches:
            continue
        source_score = 2 if actual_author else 1
        title_score = 1 if title_matches else 0
        candidates.append((source_score, title_score, entry))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def age_metadata(order: int):
    if order in AGE_3_4_ORDERS:
        return "age_3_4", "3-4岁", 1
    if order in AGE_5_7_ORDERS:
        return "age_5_7", "5-7岁", 2
    return "age_8_12", "8-12岁", 3


def build_theme_tags(title: str, lines):
    text = title + "".join(lines)
    tags = []
    plain_title = title.replace("（节选）", "")
    for tag, titles in TOPIC_BY_TITLE.items():
        if plain_title in titles:
            tags.append(tag)
    for tag, keywords in KEYWORD_TAGS.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    if not tags:
        tags.append("古诗启蒙")
    return list(dict.fromkeys(tags))[:6]


def build_knowledge_tags(lines):
    lengths = [len(normalized(line)) for line in lines]
    if len(lines) == 4 and lengths and len(set(lengths)) == 1:
        if lengths[0] == 5:
            return ["五言绝句", "小学推荐篇目"]
        if lengths[0] == 7:
            return ["七言绝句", "小学推荐篇目"]
    return ["古诗词", "小学推荐篇目"]


def parse_source_author(value: str):
    value = converter.convert(value).strip()
    match = re.match(r"[（(]([^）)]+)[）)]\s*(.+)", value)
    if match:
        author = match.group(2).strip()
        return AUTHOR_CORRECTIONS.get(author, author), match.group(1).strip()
    return AUTHOR_CORRECTIONS.get(value, value), ""


def build_extension_pool(entries, used_keys, needed_count):
    pool = []
    for entry in entries:
        if entry.get("collection") != "qianjiashi.json":
            continue
        lines = entry.get("lines") or []
        lengths = [len(normalized(line)) for line in lines]
        if len(lines) not in {4, 8}:
            continue
        if not lengths or len(set(lengths)) != 1 or lengths[0] not in {5, 7}:
            continue

        author, dynasty = parse_source_author(entry.get("author", ""))
        if not author or not dynasty:
            continue
        key = normalized(lines[0])
        if key in used_keys:
            continue

        text = entry.get("title", "") + "".join(lines)
        if entry.get("title", "") in EXTENSION_BLOCKED_TITLES:
            continue
        if any(term in text for term in EXTENSION_BLOCKED_TERMS):
            continue

        image_score = sum(text.count(char) for char in EXTENSION_PREFERRED_CHARS)
        short_bonus = 5 if len(lines) == 4 else 0
        five_char_bonus = 2 if lengths[0] == 5 else 0
        score = image_score + short_bonus + five_char_bonus
        pool.append((score, entry.get("title", ""), author, dynasty, entry, key))

    pool.sort(key=lambda item: (-item[0], item[1], item[2], item[4]["lines"][0]))
    return pool[:needed_count]


def existing_match(manifest_item, current_poems):
    first_line = normalized(manifest_item["first_line"])
    author = normalized(manifest_item["author"])
    for poem in current_poems:
        content = poem.get("content") or []
        if not content:
            continue
        if normalized(content[0]) != first_line:
            continue
        poem_author = normalized(poem.get("author", ""))
        if author in poem_author or poem_author in author:
            return poem
    return None


def next_id_number(poems):
    numbers = []
    for poem in poems:
        match = re.fullmatch(r"poem_(\d+)", str(poem.get("id", "")))
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def main():
    manifest = load_json(MANIFEST_PATH)
    current_poems = load_json(CURRENT_POEMS_PATH)
    source_entries = []
    source_counts = {}

    for source_file in SOURCE_FILES:
        data = fetch_json(SOURCE_BASE + source_file)
        entries = extract_source_entries(source_file, data)
        source_entries.extend(entries)
        source_counts[source_file] = len(entries)

    knowledge_entries = extract_knowledge_base_entries(
        fetch_bytes(KNOWLEDGE_BASE_URL).decode("utf-8")
    )
    source_entries.extend(knowledge_entries)
    source_counts["troveKnowledgeBase.txt"] = len(knowledge_entries)

    candidates = copy.deepcopy(current_poems)
    next_number = next_id_number(candidates)
    matched_existing = 0
    added = 0
    missing = []

    for item in manifest:
        existing = existing_match(item, candidates)
        source = choose_source(item, source_entries)
        if item.get("content_override"):
            source = {
                "collection": "primary_poems_75.pdf",
                "repository": "geo.bnu.edu.cn",
                "license": "public_domain_poem_text",
                "commit": "",
                "path": "docs/2019-05/20190507204624528014.pdf",
                "title": item["title"],
                "author": item["author"],
                "lines": item["content_override"],
            }

        if existing:
            existing["source"] = {
                "selection": "小学古诗词75首候选目录",
                "selection_order": item["order"],
                "repository": source["repository"] if source else "poetry-ai-app",
                "license": source["license"] if source else "project_existing_data",
                "commit": source["commit"] if source else "",
                "file": source["path"] if source else "backend/data/poems.json",
                "source_title": source["title"] if source else existing.get("title", ""),
            }
            existing["review_status"] = "existing_metadata_preserved"
            matched_existing += 1
            continue

        if source is None:
            missing.append(item)
            continue

        lines = source["lines"][: item.get("line_limit") or None]
        source_info = {
            "selection": "小学古诗词75首候选目录",
            "selection_order": item["order"],
            "repository": source["repository"],
            "license": source["license"],
            "commit": source["commit"],
            "file": source["path"],
            "source_title": source["title"],
        }

        age_level, age_range, difficulty = age_metadata(item["order"])
        theme_tags = build_theme_tags(item["title"], lines)
        poem = {
            "id": f"poem_{next_number:03d}",
            "title": item["title"],
            "author": item["author"],
            "dynasty": item["dynasty"],
            "content": lines,
            "translation": "",
            "tags": theme_tags,
            "age_level": age_level,
            "age_range": age_range,
            "difficulty": difficulty,
            "theme_tags": theme_tags,
            "knowledge_tags": build_knowledge_tags(lines),
            "recommend_reason": f"入选儿童古诗候选目录，适合{age_range}阶段循序学习。",
            "source": source_info,
            "review_status": "metadata_draft_needs_review",
        }
        candidates.append(poem)
        next_number += 1
        added += 1

    for poem in candidates:
        poem.setdefault("source", {
            "selection": "项目原有儿童古诗",
            "repository": "poetry-ai-app",
            "license": "project_existing_data",
            "commit": "",
            "file": "backend/data/poems.json",
            "source_title": poem.get("title", ""),
        })
        poem.setdefault("review_status", "existing_metadata_preserved")
        poem.pop("min_age", None)
        poem.pop("max_age", None)

    core_keys = set()
    for poem in candidates:
        content = poem.get("content") or []
        if content:
            core_keys.add(normalized(content[0]))

    extension_existing_count = len(candidates) - len(manifest)
    extension_needed = 150 - len(candidates)
    extension_selected = build_extension_pool(
        source_entries,
        used_keys=core_keys,
        needed_count=extension_needed,
    )

    for _, title, author, dynasty, source, key in extension_selected:
        lines = source["lines"]
        theme_tags = build_theme_tags(title, lines)
        visual_score = sum(
            (title + "".join(lines)).count(char)
            for char in EXTENSION_PREFERRED_CHARS
        )
        simple_for_preschool = (
            len(lines) == 4
            and len(normalized(lines[0])) == 5
            and visual_score >= 4
        )
        if simple_for_preschool:
            age_level, age_range, difficulty = "age_3_4", "3-4岁", 1
        elif len(lines) == 4 and visual_score >= 2:
            age_level, age_range, difficulty = "age_5_7", "5-7岁", 2
        else:
            age_level, age_range, difficulty = "age_8_12", "8-12岁", 3

        candidates.append({
            "id": f"poem_{next_number:03d}",
            "title": title,
            "author": author,
            "dynasty": dynasty,
            "content": lines,
            "translation": "",
            "tags": theme_tags,
            "age_level": age_level,
            "age_range": age_range,
            "difficulty": difficulty,
            "theme_tags": theme_tags,
            "knowledge_tags": build_knowledge_tags(lines),
            "recommend_reason": f"画面清晰、篇幅适中，适合{age_range}儿童拓展学习。",
            "source": {
                "selection": "儿童适宜扩展篇目",
                "repository": source["repository"],
                "license": source["license"],
                "commit": source["commit"],
                "file": source["path"],
                "source_title": source["title"],
            },
            "review_status": "metadata_draft_needs_review",
        })
        core_keys.add(key)
        next_number += 1

    duplicate_keys = []
    seen = {}
    for poem in candidates:
        content = poem.get("content") or []
        key = normalized(content[0] if content else "")
        if key in seen:
            duplicate_keys.append({"first_id": seen[key], "second_id": poem.get("id"), "key": key})
        else:
            seen[key] = poem.get("id")

    report = {
        "target_count": 150,
        "target_met": len(candidates) == 150,
        "manifest_count": len(manifest),
        "source_counts": source_counts,
        "matched_existing_count": matched_existing,
        "added_count": added,
        "core_output_count": len(candidates) - len(extension_selected),
        "extension_existing_count": extension_existing_count,
        "extension_added_count": len(extension_selected),
        "output_count": len(candidates),
        "missing_count": len(missing),
        "missing": missing,
        "duplicate_count": len(duplicate_keys),
        "duplicates": duplicate_keys,
        "production_file_changed": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(candidates, file, ensure_ascii=False, indent=2)
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing or duplicate_keys or len(candidates) != 150:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
