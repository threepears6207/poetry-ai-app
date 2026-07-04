import json
import re
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json"
DRAFT_PATH = BACKEND_DIR / "data_sources" / "generated" / "poem_metadata_draft.json"
REPORT_PATH = BACKEND_DIR / "data_sources" / "generated" / "poem_metadata_audit_report.json"
FORBIDDEN_TERMS = {
    "五言", "七言", "绝句", "律诗", "古诗", "文化常识", "情感理解",
    "画面理解", "小学推荐篇目", "教材", "修辞", "比喻", "拟人", "夸张",
    "用典", "借景抒情", "托物言志", "叙事",
}
BAD_STYLE_TAGS = {"浮萍痕迹", "落泪君前", "将士未还", "池边采莲", "思乡悲歌"}
BASE_KNOWLEDGE_TAG = "背诵积累"
ALLOWED_KNOWLEDGE_TAGS = {
    "画面理解", "自然意象", "情感理解", "意象理解", "观察能力", "生活常识",
    "价值启蒙", "简单哲理", "夸张修辞", "比喻感知", "情绪感知", "想象能力",
    "自然认知", "节奏感知", "方位认知", "生活观察", "生活画面", "季节意象",
    "动态意象", "文化常识", "比喻理解",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    catalog = load_json(CATALOG_PATH)
    drafts = load_json(DRAFT_PATH)
    catalog_map = {item["id"]: item for item in catalog}
    expected_ids = {item["id"] for item in catalog if not item.get("translation")}
    draft_ids = [item.get("id") for item in drafts]
    errors = []
    warnings = []
    tag_counts = Counter()
    new_tag_counts = Counter()
    status_counts = Counter()

    if len(draft_ids) != len(set(draft_ids)):
        errors.append("草稿中存在重复id")
    missing_ids = sorted(expected_ids - set(draft_ids))
    extra_ids = sorted(set(draft_ids) - expected_ids)
    if missing_ids:
        errors.append(f"缺少草稿id：{missing_ids}")
    if extra_ids:
        errors.append(f"存在非待补充id：{extra_ids}")

    for item in drafts:
        poem_id = item.get("id")
        source = catalog_map.get(poem_id)
        if not source:
            continue
        if item.get("title") != source.get("title"):
            errors.append(f"{poem_id}标题不一致")
        translation = str(item.get("translation") or "").strip()
        if len(translation) < 10:
            errors.append(f"{poem_id}译文为空或过短")
        tags = item.get("tags") or []
        theme_tags = item.get("theme_tags") or []
        if tags != theme_tags:
            errors.append(f"{poem_id}的tags与theme_tags不一致")
        if not 2 <= len(tags) <= 4:
            errors.append(f"{poem_id}标签数量不是2至4个：{tags}")
        if len(tags) != len(set(tags)):
            errors.append(f"{poem_id}标签重复：{tags}")
        for tag in tags:
            if not isinstance(tag, str) or not re.fullmatch(r"[\u4e00-\u9fff]{1,5}", tag):
                errors.append(f"{poem_id}标签格式错误：{tag}")
                continue
            if tag in BAD_STYLE_TAGS or any(term in tag for term in FORBIDDEN_TERMS):
                errors.append(f"{poem_id}出现禁用标签：{tag}")
            tag_counts[tag] += 1
        knowledge_tags = item.get("knowledge_tags") or []
        if len(knowledge_tags) != 3 or len(set(knowledge_tags)) != 3:
            errors.append(f"{poem_id}的knowledge_tags必须是三个不同标签")
        elif knowledge_tags[0] != BASE_KNOWLEDGE_TAG:
            errors.append(f"{poem_id}的knowledge_tags第一项不是背诵积累")
        elif not set(knowledge_tags[1:]) <= ALLOWED_KNOWLEDGE_TAGS:
            errors.append(f"{poem_id}出现词表外knowledge_tags：{knowledge_tags}")
        for tag in item.get("new_tags") or []:
            new_tag_counts[tag] += 1
        status_counts[item.get("review_status", "未标记")] += 1
        if len(translation) > 220:
            warnings.append(f"{poem_id}译文超过220字")

    report = {
        "catalog_count": len(catalog),
        "expected_draft_count": len(expected_ids),
        "actual_draft_count": len(drafts),
        "missing_id_count": len(missing_ids),
        "extra_id_count": len(extra_ids),
        "error_count": len(errors),
        "errors": errors,
        "warning_count": len(warnings),
        "warnings": warnings,
        "review_status_counts": dict(status_counts),
        "unique_tag_count": len(tag_counts),
        "tag_counts": dict(tag_counts.most_common()),
        "new_tag_count": len(new_tag_counts),
        "new_tag_counts": dict(new_tag_counts.most_common()),
        "ready_for_manual_review": not errors,
        "merged_into_catalog": False,
        "merged_into_database": False,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        key: report[key]
        for key in (
            "catalog_count", "expected_draft_count", "actual_draft_count",
            "missing_id_count", "extra_id_count", "error_count", "warning_count",
            "review_status_counts", "unique_tag_count", "new_tag_count",
            "ready_for_manual_review", "merged_into_catalog", "merged_into_database",
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
