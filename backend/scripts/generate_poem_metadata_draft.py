import argparse
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = (
    BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json"
)
REFERENCE_POEMS_PATH = BACKEND_DIR / "data" / "poems.json"
OUTPUT_PATH = (
    BACKEND_DIR / "data_sources" / "generated" / "poem_metadata_draft.json"
)
API_URL = "https://api-ai.vivo.com.cn/v1/chat/completions"
MODEL = "Volc-DeepSeek-V3.2"
FORBIDDEN_TAG_TERMS = {
    "五言", "七言", "绝句", "律诗", "古诗", "文化常识", "情感理解",
    "画面理解", "小学推荐篇目", "教材", "修辞", "比喻", "拟人", "夸张",
    "用典", "借景抒情", "托物言志", "叙事",
}
BAD_STYLE_TAGS = {"浮萍痕迹", "落泪君前", "将士未还", "池边采莲", "思乡悲歌"}


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def strip_model_wrapper(text):
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    return re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()


def reference_tag_vocabulary():
    poems = load_json(REFERENCE_POEMS_PATH, [])
    excluded = {"儿童启蒙"}
    for poem in poems:
        excluded.add(str(poem.get("author") or ""))
        excluded.add(str(poem.get("dynasty") or ""))
    return sorted({
        tag
        for poem in poems
        for tag in (poem.get("tags") or [])
        if tag and tag not in excluded
    })


def build_messages(poems, reference_tags):
    input_items = [{
        "id": poem["id"],
        "title": poem["title"],
        "author": poem["author"],
        "dynasty": poem["dynasty"],
        "content": poem["content"],
        "age_range": poem["age_range"],
    } for poem in poems]
    system_prompt = """你是严谨的中国古诗教育数据编辑，服务对象是3至7岁儿童。
请忠实理解诗意，不能编造人物、动作、背景或作者经历。
题材不作价值排除：战争、死亡、爱情、宫廷、饮酒等内容都可以准确标注。
译文要完整对应原诗，语言浅白自然，但不能把复杂含义改成错误的儿童故事。
遇到学界存在争议的人名、典故和指代，使用中性译法，不要擅自认定某一种解释。
译文使用客观表述，不要无依据增加“我”“你”等叙述人称。
标签必须是对诗歌本身的简短概括，可以概括题材、景物、人物、事件、意境、主题或情绪。
标签风格参考项目已有数据：“春天、自然、儿童、童趣、月亮、思乡、劳动、友情、送别、山水、旅途、亲情、感恩”。
优先复用参考标签；确实没有合适的词时，可以新增浅显易懂、能用于其他诗歌的通用标签。
每首生成2至4个标签，每个标签1至5个汉字。孩子或家长看见标签就应大致明白诗写了什么或有什么感情。
不要截取诗句临时拼成让人看不懂的短语，例如禁止“浮萍痕迹、落泪君前、将士未还、池边采莲、思乡悲歌”。
不得输出体裁、修辞、学习目标或教材信息，例如“五言绝句、文化常识、情感理解、画面理解、用典、小学推荐篇目”。
只输出合法JSON数组，不要Markdown，不要解释。"""
    user_prompt = f"""请为下面古诗生成译文和标签。

项目现有标签参考（不是强制白名单）：{json.dumps(reference_tags, ensure_ascii=False)}

输出格式：
[
  {{
    "id": "原id",
    "translation": "逐句含义完整、连贯的白话译文",
    "tags": ["标签1", "标签2", "标签3"]
  }}
]

古诗数据：
{json.dumps(input_items, ensure_ascii=False, indent=2)}"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_model(poems, app_key):
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_key}",
        },
        json={
            "requestId": str(uuid.uuid4()),
            "model": MODEL,
            "messages": build_messages(poems, reference_tag_vocabulary()),
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    result = json.loads(strip_model_wrapper(content))
    if not isinstance(result, list):
        raise ValueError("模型返回结果不是JSON数组")
    return result


def validate_result(source_poems, result, reference_tags):
    source_map = {poem["id"]: poem for poem in source_poems}
    result_map = {}
    for item in result:
        if not isinstance(item, dict):
            raise ValueError("模型结果中存在非对象元素")
        poem_id = item.get("id")
        if poem_id not in source_map or poem_id in result_map:
            raise ValueError(f"模型返回未知或重复id：{poem_id}")
        translation = str(item.get("translation") or "").strip()
        tags = item.get("tags") or []
        if len(translation) < 10:
            raise ValueError(f"{poem_id}译文过短")
        if not 2 <= len(tags) <= 4:
            raise ValueError(f"{poem_id}标签数量必须是2至4个：{tags}")
        if len(tags) != len(set(tags)):
            raise ValueError(f"{poem_id}存在重复标签：{tags}")
        for tag in tags:
            if not isinstance(tag, str) or not re.fullmatch(
                r"[\u4e00-\u9fff]{1,5}", tag.strip()
            ):
                raise ValueError(f"{poem_id}标签必须是1至5个汉字：{tag}")
            if any(term in tag for term in FORBIDDEN_TAG_TERMS):
                raise ValueError(f"{poem_id}出现非诗意标签：{tag}")
            if tag in BAD_STYLE_TAGS:
                raise ValueError(f"{poem_id}出现难以理解或不可复用的标签：{tag}")
        tags = [tag.strip() for tag in tags]
        result_map[poem_id] = {
            "id": poem_id,
            "title": source_map[poem_id]["title"],
            "translation": translation,
            "tags": tags,
            "theme_tags": list(tags),
            "knowledge_tags": [],
            "new_tags": [tag for tag in tags if tag not in reference_tags],
            "provider": "vivo",
            "model": MODEL,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "review_status": "待人工确认",
        }
    missing = set(source_map) - set(result_map)
    if missing:
        raise ValueError(f"模型漏掉诗歌：{sorted(missing)}")
    return list(result_map.values())


def main():
    parser = argparse.ArgumentParser(description="调用蓝心平台模型生成古诗译文和标签草稿")
    parser.add_argument("--ids", nargs="*", help="仅生成指定诗歌id")
    parser.add_argument("--limit", type=int, default=3, help="最多处理数量，默认3首")
    parser.add_argument("--all", action="store_true", help="生成所有尚未进入草稿的诗歌")
    parser.add_argument("--batch-size", type=int, default=10, help="批量模式每次请求数量")
    parser.add_argument("--retries", type=int, default=3, help="单批校验失败后的重试次数")
    parser.add_argument("--catalog-path", type=Path, default=CATALOG_PATH, help="待补全元数据的诗库 JSON")
    args = parser.parse_args()

    load_dotenv(BACKEND_DIR / ".env")
    app_key = os.getenv("VIVO_APP_KEY", "").strip()
    if not app_key:
        raise SystemExit("缺少 VIVO_APP_KEY，无法调用比赛平台大模型")

    catalog = load_json(args.catalog_path, [])
    old = load_json(OUTPUT_PATH, [])
    old_map = {item["id"]: item for item in old}
    selected_ids = set(args.ids or [])
    poems = [
        poem for poem in catalog
        if not poem.get("translation")
        and (not selected_ids or poem.get("id") in selected_ids)
        and (not args.all or poem.get("id") not in old_map)
    ]
    if not args.all:
        poems = poems[: max(1, args.limit)]
    if not poems:
        print(json.dumps({
            "generated_count": 0,
            "draft_total_count": len(old),
            "message": "没有尚未生成的诗歌",
        }, ensure_ascii=False, indent=2))
        return
    if selected_ids and {poem["id"] for poem in poems} != selected_ids:
        missing = selected_ids - {poem["id"] for poem in poems}
        raise SystemExit(f"指定诗歌不存在或已有译文：{sorted(missing)}")

    reference_tags = reference_tag_vocabulary()
    batch_size = max(1, min(20, args.batch_size if args.all else len(poems)))
    batches = [poems[index:index + batch_size] for index in range(0, len(poems), batch_size)]
    generated_all = []
    merged = dict(old_map)
    for batch_index, batch in enumerate(batches, start=1):
        last_error = None
        for attempt in range(1, max(1, args.retries) + 1):
            try:
                generated = validate_result(
                    batch,
                    call_model(batch, app_key),
                    reference_tags,
                )
                break
            except Exception as error:
                last_error = error
                if attempt >= max(1, args.retries):
                    raise RuntimeError(
                        f"第{batch_index}批连续{attempt}次生成或校验失败：{error}"
                    ) from error
                print(f"第{batch_index}批第{attempt}次失败，准备重试：{error}")
                time.sleep(attempt * 2)
        else:
            raise RuntimeError(f"第{batch_index}批生成失败：{last_error}")

        for item in generated:
            merged[item["id"]] = item
        generated_all.extend(generated)
        output = sorted(merged.values(), key=lambda item: item["id"])
        OUTPUT_PATH.write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"完成第{batch_index}/{len(batches)}批："
            f"{', '.join(item['id'] for item in generated)}；草稿累计{len(output)}首"
        )
        if batch_index < len(batches):
            time.sleep(1)

    output = sorted(merged.values(), key=lambda item: item["id"])
    print(json.dumps({
        "generated_count": len(generated_all),
        "generated_ids": [item["id"] for item in generated_all],
        "draft_total_count": len(output),
        "output_path": str(OUTPUT_PATH),
        "review_status": "待人工确认，尚未写入候选库和数据库",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
