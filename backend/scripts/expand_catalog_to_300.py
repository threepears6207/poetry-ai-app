import argparse
import json
import re
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(BACKEND_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR / "scripts"))

import build_children_poem_catalog as builder
from poem_catalog import normalize_poem_text, poem_content_hash
from tag_rules import normalize_poem_metadata


CORE_PATH = BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json"
SUPPLEMENT_PATH = BACKEND_DIR / "data_sources" / "classic_poems" / "tang_poems_candidates.json"
DRAFT_PATH = BACKEND_DIR / "data_sources" / "generated" / "poem_metadata_draft.json"
REPORT_PATH = BACKEND_DIR / "data_sources" / "generated" / "catalog_300_expansion_report.json"
TARGET_COUNT = 300
FULL_TANG_FILES = tuple(f"poet.tang.{offset}.json" for offset in range(0, 10000, 1000))
FULL_TANG_BASE = (
    "https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/"
    f"{builder.SOURCE_COMMIT}/%E5%85%A8%E5%94%90%E8%AF%97/"
)

# 人教社《小学生必备古诗词112首》与统编教材常见篇目优先；已在库中的
# 篇目会被正文哈希自动跳过。其余名额再按短篇、自然意象和儿童可理解度排序。
TEXTBOOK_PRIORITY_POEMS = {
    ("风", "李峤"), ("咏柳", "贺知章"), ("出塞", "王昌龄"),
    ("鹿柴", "王维"), ("送元二使安西", "王维"),
    ("九月九日忆山东兄弟", "王维"), ("古朗月行", "李白"),
    ("望庐山瀑布", "李白"), ("赠汪伦", "李白"),
    ("黄鹤楼送孟浩然之广陵", "李白"), ("早发白帝城", "李白"),
    ("望天门山", "李白"), ("别董大", "高适"), ("春夜喜雨", "杜甫"),
    ("枫桥夜泊", "张继"), ("滁州西涧", "韦应物"), ("游子吟", "孟郊"),
    ("早春呈水部张十八员外", "韩愈"), ("池上", "白居易"),
    ("小儿垂钓", "胡令能"), ("江雪", "柳宗元"),
    ("寻隐者不遇", "贾岛"), ("山行", "杜牧"), ("清明", "杜牧"),
    ("蜂", "罗隐"), ("三衢道中", "曾几"), ("春日", "朱熹"),
    ("所见", "袁枚"), ("村居", "高鼎"),
}

POPULAR_TANG_AUTHORS = {
    "李白", "杜甫", "王维", "孟浩然", "白居易", "刘禹锡", "柳宗元",
    "贺知章", "王昌龄", "杜牧", "李商隐", "贾岛", "韦应物", "岑参",
    "高适", "孟郊", "韩愈", "王勃", "骆宾王", "李峤", "张九龄",
    "陈子昂", "卢纶", "张继", "刘长卿", "王之涣", "王建", "张祜",
}
FULL_TANG_BLOCKED_TITLE_TERMS = {
    "奉和", "应制", "杂曲", "乐府", "宫", "宴", "挽歌", "离婚", "道士",
    "侍", "敕", "酬", "答", "寄", "赠", "送", "别", "同", "和", "曲辞",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def poem_key(poem):
    return poem_content_hash(poem.get("content") or [])


def title_author_key(title, author):
    return normalize_poem_text(title), normalize_poem_text(author)


def source_entries():
    entries = []
    for source_file in builder.SOURCE_FILES:
        data = builder.fetch_json(builder.SOURCE_BASE + source_file)
        entries.extend(builder.extract_source_entries(source_file, data))
    for source_file in FULL_TANG_FILES:
        data = builder.fetch_json(FULL_TANG_BASE + source_file)
        for poem in data:
            lines = builder.split_poem_lines(poem.get("paragraphs") or [])
            if not lines:
                continue
            entries.append({
                "collection": source_file,
                "repository": "chinese-poetry/chinese-poetry",
                "license": "MIT",
                "commit": builder.SOURCE_COMMIT,
                "path": f"全唐诗/{source_file}",
                "title": builder.converter.convert(str(poem.get("title") or "")).strip(),
                "author": f"（唐）{builder.converter.convert(str(poem.get('author') or '')).strip()}",
                "lines": lines,
            })
    return entries


def replacement_pool(entries, used_hashes, used_titles):
    pool = []
    pool_hashes = set()
    pool_titles = set()
    for source in entries:
        lines = source.get("lines") or []
        lengths = [len(normalize_poem_text(line)) for line in lines]
        if len(lines) not in {4, 8} or not lengths or len(set(lengths)) != 1:
            continue
        if lengths[0] not in {5, 7}:
            continue
        title = source.get("title", "")
        author, dynasty = builder.parse_source_author(source.get("author", ""))
        if not title or not author or not dynasty:
            continue
        text = title + "".join(lines)
        if title in builder.EXTENSION_BLOCKED_TITLES:
            continue
        if any(term in text for term in builder.EXTENSION_BLOCKED_TERMS):
            continue
        if source.get("collection", "").startswith("poet.tang."):
            if author not in POPULAR_TANG_AUTHORS:
                continue
            if len(normalize_poem_text(title)) > 10:
                continue
            if any(term in title for term in FULL_TANG_BLOCKED_TITLE_TERMS):
                continue
        content_hash = poem_content_hash(lines)
        title_key = title_author_key(title, author)
        if (
            not content_hash or content_hash in used_hashes or content_hash in pool_hashes
            or title_key in used_titles or title_key in pool_titles
        ):
            continue
        pool_hashes.add(content_hash)
        pool_titles.add(title_key)
        collection = source.get("collection", "")
        if (title.replace("（节选）", ""), author) in TEXTBOOK_PRIORITY_POEMS:
            priority = 3
        elif collection == "qianjiashi.json":
            priority = 2
        elif collection == "tangshisanbaishou.json":
            priority = 1
        else:
            priority = 0
        image_score = sum(text.count(char) for char in builder.EXTENSION_PREFERRED_CHARS)
        short_bonus = 5 if len(lines) == 4 else 0
        five_char_bonus = 2 if lengths[0] == 5 else 0
        score = image_score + short_bonus + five_char_bonus
        pool.append((priority, score, title, author, dynasty, source, content_hash, title_key))
    pool.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
    return pool


def build_poem(poem_id, title, author, dynasty, source):
    lines = source["lines"]
    theme_tags = builder.build_theme_tags(title, lines)
    visual_score = sum((title + "".join(lines)).count(char) for char in builder.EXTENSION_PREFERRED_CHARS)
    preschool = len(lines) == 4 and len(normalize_poem_text(lines[0])) == 5 and visual_score >= 4
    age_level, age_range, difficulty = (
        ("age_3_4", "3-4岁", 1) if preschool else ("age_5_7", "5-7岁", 2)
    )
    return {
        "id": poem_id,
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
        "knowledge_tags": builder.build_knowledge_tags(lines),
        "recommend_reason": f"篇幅适中、意象清晰，适合{age_range}儿童拓展学习。",
    }


def expand_catalog(write=False):
    core = load_json(CORE_PATH)
    supplement = load_json(SUPPLEMENT_PATH)
    seen_hashes = set()
    used_titles = set()
    canonical_versions = []
    duplicate_indexes = []

    for poem in core:
        seen_hashes.add(poem_key(poem))
        title_key = title_author_key(poem.get("title", ""), poem.get("author", ""))
        used_titles.add(title_key)
        canonical_versions.append((title_key, normalize_poem_text("".join(poem.get("content") or []))))
    for index, poem in enumerate(supplement):
        key = poem_key(poem)
        title_key = title_author_key(poem.get("title", ""), poem.get("author", ""))
        # “不重复”按规范化正文判定。相同题目可能存在不同版本或同题诗，
        # 不能仅凭“题目 + 作者”误删正文不同的作品。
        normalized_content = normalize_poem_text("".join(poem.get("content") or []))
        is_shorter_contained_version = any(
            title_key == canonical_title
            and len(normalized_content) < len(canonical_content)
            and normalized_content in canonical_content
            for canonical_title, canonical_content in canonical_versions
        )
        if not key or key in seen_hashes or is_shorter_contained_version:
            duplicate_indexes.append(index)
            continue
        seen_hashes.add(key)
        used_titles.add(title_key)
        canonical_versions.append((title_key, normalized_content))

    pool = replacement_pool(source_entries(), seen_hashes, used_titles)
    if len(pool) < len(duplicate_indexes):
        raise RuntimeError(f"可信候选不足：需要{len(duplicate_indexes)}首，仅找到{len(pool)}首")

    replacements = []
    for index, selected in zip(duplicate_indexes, pool):
        priority, _, title, author, dynasty, source, content_hash, title_key = selected
        old = supplement[index]
        new_poem = build_poem(old["id"], title, author, dynasty, source)
        supplement[index] = new_poem
        seen_hashes.add(content_hash)
        used_titles.add(title_key)
        replacements.append({
            "poem_id": old["id"],
            "old_title": old.get("title", ""),
            "old_line_count": len(old.get("content") or []),
            "new_title": title,
            "author": author,
            "selection_tier": priority,
            "textbook_priority": priority == 3,
            "source_file": source.get("path", ""),
        })

    combined = core + supplement
    content_hashes = [poem_key(poem) for poem in combined]
    title_keys = [title_author_key(poem.get("title", ""), poem.get("author", "")) for poem in combined]
    report = {
        "target_count": TARGET_COUNT,
        "total_count": len(combined),
        "unique_content_count": len(set(content_hashes)),
        "unique_title_author_count": len(set(title_keys)),
        "replaced_duplicate_count": len(replacements),
        "textbook_priority_replacement_count": sum(item["textbook_priority"] for item in replacements),
        "authoritative_basis": [
            "教育部《义务教育语文课程标准（2022年版）》",
            "人民教育出版社《小学生必备古诗词112首》",
        ],
        "text_source": {
            "repository": "chinese-poetry/chinese-poetry",
            "commit": builder.SOURCE_COMMIT,
            "files": list(builder.SOURCE_FILES),
            "full_tang_files": list(FULL_TANG_FILES),
        },
        "metadata_complete": all(bool(poem.get("translation")) for poem in combined),
        "replacements": replacements,
    }
    if len(combined) != TARGET_COUNT or len(set(content_hashes)) != TARGET_COUNT:
        raise RuntimeError(f"300首唯一性检查失败：{report}")
    if write:
        SUPPLEMENT_PATH.write_text(json.dumps(supplement, ensure_ascii=False, indent=2), encoding="utf-8")
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def apply_metadata(write=False):
    supplement = load_json(SUPPLEMENT_PATH)
    drafts = {item["id"]: item for item in load_json(DRAFT_PATH)}
    applied = []
    for poem in supplement:
        if not poem.get("translation"):
            draft = drafts.get(poem["id"])
            if not draft or not draft.get("translation"):
                raise RuntimeError(f"{poem['id']} 缺少已校验的元数据草稿")
            poem["translation"] = draft["translation"]
            poem["tags"] = draft["tags"]
            poem["theme_tags"] = draft.get("theme_tags") or draft["tags"]
            poem["knowledge_tags"] = draft.get("knowledge_tags") or poem["knowledge_tags"]
            applied.append(poem["id"])
        poem.update(normalize_poem_metadata(poem))
    if write:
        SUPPLEMENT_PATH.write_text(json.dumps(supplement, ensure_ascii=False, indent=2), encoding="utf-8")
        if REPORT_PATH.exists():
            report = load_json(REPORT_PATH)
            report["metadata_complete"] = all(bool(poem.get("translation")) for poem in supplement)
            REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"applied_count": len(applied), "poem_ids": applied}


def main():
    parser = argparse.ArgumentParser(description="将两个诗库批次整理为300首不重复儿童诗库")
    parser.add_argument("--write", action="store_true", help="写入补充批次和质检报告")
    parser.add_argument("--apply-metadata", action="store_true", help="把已校验元数据草稿合并到补充批次")
    args = parser.parse_args()
    result = apply_metadata(args.write) if args.apply_metadata else expand_catalog(args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
