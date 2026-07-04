import json
import re
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR / "scripts"))

import build_children_poem_catalog as legacy


CURRENT_PATH = BACKEND_DIR / "data" / "poems.json"
MANIFEST_PATH = BACKEND_DIR / "data_sources" / "children_poems_75_manifest.json"
OUTPUT_DIR = BACKEND_DIR / "data_sources" / "generated"
OUTPUT_PATH = OUTPUT_DIR / "children_poems_candidates.json"
REPORT_PATH = OUTPUT_DIR / "children_poems_report.json"
METADATA_DRAFT_PATH = OUTPUT_DIR / "poem_metadata_draft.json"
TARGET_COUNT = 150
FINAL_FIELDS = (
    "id", "title", "author", "dynasty", "content", "translation", "tags",
    "age_level", "age_range", "difficulty", "theme_tags", "knowledge_tags",
    "recommend_reason",
)
TARGET_AGE_COUNTS = {
    "age_3_4": 50,
    "age_5_7": 100,
}
# 3-4岁组不是从总榜按分数生切前50名，而是在项目原有8首基础上，
# 补充42首篇幅短、画面或叙事清楚、适合亲子讲解的经典作品。
# 题材不作为排除条件，因此仍保留战争、死亡、离别等有教育意义的内容。
PRESCHOOL_GUIDED_FIRST_LINES = {
    "小娃撑小艇",
    "松下问童子",
    "空山不见人",
    "春种一粒粟",
    "不论平地与山尖",
    "京口瓜洲一水间",
    "清明时节雨纷纷",
    "绿遍山原满白川",
    "众鸟高飞尽",
    "向晚意不适",
    "白发三千丈",
    "横看成岭侧成峰",
    "毕竟西湖六月中",
    "秦时明月汉时关",
    "少小离家老大回",
    "何处秋风至",
    "湖光秋月两相和",
    "死去元知万事空",
    "咬定青山不放松",
    "黄师塔前江水东",
    "黄梅时节家家雨",
    "昼出耘田夜绩麻",
    "寒雨连江夜入吴",
    "诗家清景在新春",
    "故园东望路漫漫",
    "朱雀桥边野草花",
    "黑云翻墨未遮山",
    "寒夜客来茶当酒",
    "林暗草惊风",
    "九曲黄河万里沙",
    "月落乌啼霜满天",
    "千锤万凿出深山",
    "半亩方塘一鉴开",
    "雨前初见花间蕊",
    "天街小雨润如酥",
    "故人西辞黄鹤楼",
    "春城无处不飞花",
    "我家洗砚池头树",
    "千里莺啼绿映红",
    "荷尽已无擎雨盖",
    "梅子流酸溅齿牙",
    "好雨知时节",
}
PRESCHOOL_FOUNDATION_FIRST_LINES = {
    "小娃撑小艇",
    "松下问童子",
    "空山不见人",
    "春种一粒粟",
    "不论平地与山尖",
    "清明时节雨纷纷",
    "绿遍山原满白川",
    "众鸟高飞尽",
    "向晚意不适",
    "白发三千丈",
    "毕竟西湖六月中",
    "少小离家老大回",
    "何处秋风至",
    "湖光秋月两相和",
    "黄师塔前江水东",
    "黄梅时节家家雨",
    "昼出耘田夜绩麻",
    "黑云翻墨未遮山",
    "荷尽已无擎雨盖",
    "梅子流酸溅齿牙",
}
NEAR_DUPLICATE_FIRST_LINE = "绿遍山原白满川"
DEDUP_REPLACEMENT_FIRST_LINE = "爆竹声中一岁除"
COMMON_CHARS_URL = (
    "https://gist.githubusercontent.com/jjgod/1432945/raw/"
    "90cd5fe7f3fc112823f7a5542632040f641ca487/common3500.txt"
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def chinese_chars(text):
    return [char for char in text if "\u4e00" <= char <= "\u9fff"]


def common_character_sets():
    text = legacy.fetch_bytes(COMMON_CHARS_URL).decode("utf-8-sig")
    ordered = []
    for char in chinese_chars(text):
        if char not in ordered:
            ordered.append(char)
    if len(ordered) < 3000:
        raise ValueError(f"常用字表数量异常：{len(ordered)}")
    return set(ordered[:2500]), set(ordered)


def source_entries():
    entries = []
    for source_file in legacy.SOURCE_FILES:
        data = legacy.fetch_json(legacy.SOURCE_BASE + source_file)
        entries.extend(legacy.extract_source_entries(source_file, data))
    text = legacy.fetch_bytes(legacy.KNOWLEDGE_BASE_URL).decode("utf-8")
    entries.extend(legacy.extract_knowledge_base_entries(text))
    return entries


def canonical_manifest_map(manifest):
    return {legacy.normalized(item["first_line"]): item for item in manifest}


def structural_candidate(entry, manifest_map):
    lines = entry.get("lines") or []
    lengths = [len(legacy.normalized(line)) for line in lines]
    if len(lines) not in {4, 8}:
        return None
    if not lengths or len(set(lengths)) != 1 or lengths[0] not in {5, 7}:
        return None

    first_key = legacy.normalized(lines[0])
    manifest_item = manifest_map.get(first_key)
    author, dynasty = legacy.parse_source_author(entry.get("author", ""))
    if entry.get("collection") == "tangshisanbaishou.json" and author and not dynasty:
        dynasty = "唐"
    if manifest_item:
        title = manifest_item["title"]
        author = manifest_item["author"]
        dynasty = manifest_item["dynasty"]
        if manifest_item.get("line_limit"):
            lines = lines[: manifest_item["line_limit"]]
    else:
        title = entry.get("title", "").strip()

    if not title or not author or not dynasty:
        return None
    return {
        "title": title,
        "author": author,
        "dynasty": dynasty,
        "content": lines,
        "is_core": bool(manifest_item),
        "source": {
            "selection": "语言难度筛选儿童古诗",
            "repository": entry.get("repository", ""),
            "license": entry.get("license", ""),
            "commit": entry.get("commit", ""),
            "file": entry.get("path", ""),
            "source_title": entry.get("title", ""),
        },
    }


def manifest_overrides(manifest):
    result = []
    for item in manifest:
        if not item.get("content_override"):
            continue
        result.append({
            "title": item["title"],
            "author": item["author"],
            "dynasty": item["dynasty"],
            "content": item["content_override"],
            "is_core": True,
            "source": {
                "selection": "小学古诗词75首候选目录",
                "repository": "geo.bnu.edu.cn",
                "license": "public_domain_poem_text",
                "commit": "",
                "file": "docs/2019-05/20190507204624528014.pdf",
                "source_title": item["title"],
            },
        })
    return result


def readability(candidate, common_2500, common_3500):
    text = "".join(candidate["content"])
    chars = chinese_chars(text)
    unique_chars = set(chars)
    tier2 = {char for char in unique_chars if char not in common_2500 and char in common_3500}
    uncommon = {char for char in unique_chars if char not in common_3500}
    line_count = len(candidate["content"])
    title_length = len(chinese_chars(candidate["title"]))
    score = (
        len(uncommon) * 120
        + len(tier2) * 9
        + len(unique_chars) * 0.8
        + len(chars) * 0.7
        + max(0, line_count - 4) * 10
        + max(0, title_length - 5) * 2
        - (12 if candidate["is_core"] else 0)
    )
    return {
        "score": round(score, 2),
        "uncommon_chars": "".join(sorted(uncommon)),
        "tier2_chars": "".join(sorted(tier2)),
        "unique_char_count": len(unique_chars),
        "total_char_count": len(chars),
        "line_count": line_count,
    }


def build_poem(candidate, poem_id, metrics, age_level):
    age_range = "3-4岁" if age_level == "age_3_4" else "5-7岁"
    if age_level == "age_3_4":
        first_line = legacy.normalized(candidate["content"][0])
        difficulty = 1 if first_line in PRESCHOOL_FOUNDATION_FIRST_LINES else 2
        learning_mode = "亲子讲解和画面辅助"
    else:
        difficulty = 2 if metrics["score"] < 75 else 3
        learning_mode = "讲解辅助"
    tags = legacy.build_theme_tags(candidate["title"], candidate["content"])
    return {
        "id": poem_id,
        "title": candidate["title"],
        "author": candidate["author"],
        "dynasty": candidate["dynasty"],
        "content": candidate["content"],
        "translation": "",
        "tags": tags,
        "age_level": age_level,
        "age_range": age_range,
        "difficulty": difficulty,
        "theme_tags": tags,
        "knowledge_tags": [],
        "recommend_reason": f"篇幅和表达适合{age_range}儿童在{learning_mode}下学习。",
    }


def main():
    current = load_json(CURRENT_PATH)
    manifest = load_json(MANIFEST_PATH)
    common_2500, common_3500 = common_character_sets()
    manifest_map = canonical_manifest_map(manifest)

    pool_by_first = {}
    for entry in source_entries():
        candidate = structural_candidate(entry, manifest_map)
        if not candidate:
            continue
        key = legacy.normalized(candidate["content"][0])
        old = pool_by_first.get(key)
        if old is None or (candidate["is_core"] and not old["is_core"]):
            pool_by_first[key] = candidate
    for candidate in manifest_overrides(manifest):
        pool_by_first[legacy.normalized(candidate["content"][0])] = candidate

    locked_first = {legacy.normalized(poem["content"][0]) for poem in current}
    ranked = []
    for key, candidate in pool_by_first.items():
        if key in locked_first:
            continue
        metrics = readability(candidate, common_2500, common_3500)
        ranked.append((metrics["score"], candidate["title"], key, candidate, metrics))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    selected = ranked[: TARGET_COUNT - len(current)]
    if len(selected) != TARGET_COUNT - len(current):
        raise ValueError("符合结构要求的候选诗数量不足")

    selected_keys = {item[2] for item in selected}
    duplicate_index = next(
        (
            index for index, item in enumerate(selected)
            if item[2] == NEAR_DUPLICATE_FIRST_LINE
        ),
        None,
    )
    replacement = next(
        (
            item for item in ranked
            if item[2] == DEDUP_REPLACEMENT_FIRST_LINE
            and item[2] not in selected_keys
        ),
        None,
    )
    if duplicate_index is None or replacement is None:
        raise ValueError("近似重复诗替换配置与候选池不一致")
    selected[duplicate_index] = replacement

    output = []
    for poem in current:
        item = dict(poem)
        output.append(item)

    existing_preschool = sum(1 for poem in output if poem.get("age_level") == "age_3_4")
    preschool_slots = max(0, TARGET_AGE_COUNTS["age_3_4"] - existing_preschool)
    preschool_keys = {
        key for _, _, key, _, _ in selected
        if key in PRESCHOOL_GUIDED_FIRST_LINES
    }
    if len(preschool_keys) != preschool_slots:
        raise ValueError(
            f"3-4岁亲子讲解清单与候选库不一致：需要{preschool_slots}首，"
            f"实际只有{len(preschool_keys)}首"
        )

    details = []
    next_id = 22
    for _, _, key, candidate, metrics in selected:
        age_level = "age_3_4" if key in preschool_keys else "age_5_7"
        poem = build_poem(candidate, f"poem_{next_id:03d}", metrics, age_level)
        output.append(poem)
        details.append({
            "id": poem["id"],
            "title": poem["title"],
            "author": poem["author"],
            "age_level": age_level,
            **metrics,
        })
        next_id += 1

    first_lines = [legacy.normalized(poem["content"][0]) for poem in output]
    metadata_drafts = load_json(METADATA_DRAFT_PATH)
    metadata_map = {item["id"]: item for item in metadata_drafts}
    expected_metadata_ids = {poem["id"] for poem in output if poem["id"] not in {
        current_poem["id"] for current_poem in current
    }}
    if set(metadata_map) != expected_metadata_ids:
        missing = sorted(expected_metadata_ids - set(metadata_map))
        extra = sorted(set(metadata_map) - expected_metadata_ids)
        raise ValueError(f"译文标签草稿与候选诗不一致，缺少{missing}，多出{extra}")

    for poem in output:
        metadata = metadata_map.get(poem["id"])
        if metadata:
            if metadata.get("title") != poem["title"]:
                raise ValueError(f"{poem['id']}的草稿标题与候选诗标题不一致")
            for field in ("translation", "tags", "theme_tags", "knowledge_tags"):
                poem[field] = metadata[field]
        if set(poem) != set(FINAL_FIELDS):
            raise ValueError(
                f"{poem['id']}最终字段不符合要求：{sorted(set(poem) - set(FINAL_FIELDS))}"
            )

    report = {
        "method": "language_readability_without_topic_exclusion",
        "age_assignment": "3-4岁经典入门清单加亲子讲解；5-7岁按语言难度分级",
        "target_count": TARGET_COUNT,
        "output_count": len(output),
        "unique_id_count": len({poem["id"] for poem in output}),
        "unique_first_line_count": len(set(first_lines)),
        "age_counts": {
            level: sum(1 for poem in output if poem.get("age_level") == level)
            for level in ("age_3_4", "age_5_7")
        },
        "pool_count": len(pool_by_first),
        "selected_new_count": len(selected),
        "merged_metadata_count": len(metadata_map),
        "selected_core_count": sum(1 for item in selected if item[3]["is_core"]),
        "max_selected_score": max(item[4]["score"] for item in selected),
        "selected_details": details,
    }
    if len(output) != TARGET_COUNT or len(set(first_lines)) != TARGET_COUNT:
        raise ValueError("最终候选库数量或首句唯一性校验失败")
    if report["age_counts"] != TARGET_AGE_COUNTS:
        raise ValueError(
            f"年龄分布校验失败：期望{TARGET_AGE_COUNTS}，实际{report['age_counts']}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "selected_details"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
