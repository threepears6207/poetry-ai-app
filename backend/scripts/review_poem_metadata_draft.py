import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generate_poem_metadata_draft as generator


CATALOG_PATH = generator.CATALOG_PATH
DRAFT_PATH = generator.OUTPUT_PATH
API_URL = generator.API_URL
MODEL = generator.MODEL


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def strip_wrapper(text):
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    return re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()


def build_messages(items, catalog_map, reference_tags):
    review_items = []
    for item in items:
        poem = catalog_map[item["id"]]
        review_items.append({
            "id": item["id"],
            "title": poem["title"],
            "author": poem["author"],
            "dynasty": poem["dynasty"],
            "content": poem["content"],
            "current_translation": item["translation"],
            "current_tags": item["tags"],
        })
    system_prompt = """你是中国古诗数据的复核编辑。请逐句对照原诗，修正当前译文和标签。
译文必须完整、准确、浅显，不增加原诗没有的人物、地点、因果或故事。
遇到存在争议的典故和人物指代，采用中性译法，不能武断指定某个历史人物。
标签使用孩子和家长一眼能懂的通用短词，风格如“春天、自然、月亮、思乡、友情、送别、山水、童趣”。
优先复用参考标签，没有合适词时才新增1至5个汉字的通用标签。
每首2至4个标签；禁止体裁、修辞、教学目标、诗句缩写和晦涩临时短语。
只输出合法JSON数组，每个输入id必须且只能出现一次，不要解释。"""
    user_prompt = f"""参考标签（不是固定白名单）：{json.dumps(reference_tags, ensure_ascii=False)}

输出格式：
[
  {{"id": "原id", "translation": "复核后的译文", "tags": ["标签1", "标签2"]}}
]

待复核数据：
{json.dumps(review_items, ensure_ascii=False, indent=2)}"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_review(items, catalog_map, reference_tags, app_key):
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_key}",
        },
        json={
            "requestId": str(uuid.uuid4()),
            "model": MODEL,
            "messages": build_messages(items, catalog_map, reference_tags),
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    result = json.loads(strip_wrapper(content))
    source_poems = [catalog_map[item["id"]] for item in items]
    validated = generator.validate_result(source_poems, result, reference_tags)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in validated:
        item["generated_at"] = now
        item["review_status"] = "模型二次复核"
    return validated


def main():
    parser = argparse.ArgumentParser(description="对古诗译文和标签草稿进行模型二次复核")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()
    load_dotenv(BACKEND_DIR / ".env")
    app_key = os.getenv("VIVO_APP_KEY", "").strip()
    if not app_key:
        raise SystemExit("缺少 VIVO_APP_KEY")

    catalog = load_json(CATALOG_PATH)
    catalog_map = {item["id"]: item for item in catalog}
    drafts = load_json(DRAFT_PATH)
    draft_map = {item["id"]: item for item in drafts}
    pending = [item for item in drafts if item.get("review_status") == "待人工确认"]
    batch_size = max(1, min(20, args.batch_size))
    batches = [pending[index:index + batch_size] for index in range(0, len(pending), batch_size)]
    reference_tags = generator.reference_tag_vocabulary()

    reviewed_count = 0
    for batch_index, batch in enumerate(batches, start=1):
        for attempt in range(1, max(1, args.retries) + 1):
            try:
                reviewed = call_review(batch, catalog_map, reference_tags, app_key)
                break
            except Exception as error:
                if attempt >= max(1, args.retries):
                    raise RuntimeError(
                        f"第{batch_index}批连续{attempt}次复核失败：{error}"
                    ) from error
                print(f"第{batch_index}批第{attempt}次失败，准备重试：{error}")
                time.sleep(attempt * 2)
        for item in reviewed:
            draft_map[item["id"]] = item
        reviewed_count += len(reviewed)
        output = sorted(draft_map.values(), key=lambda item: item["id"])
        DRAFT_PATH.write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"复核第{batch_index}/{len(batches)}批完成，累计{reviewed_count}首")
        if batch_index < len(batches):
            time.sleep(1)

    print(json.dumps({
        "reviewed_count": reviewed_count,
        "remaining_pending_count": sum(
            1 for item in draft_map.values()
            if item.get("review_status") == "待人工确认"
        ),
        "draft_total_count": len(draft_map),
        "merged_into_catalog": False,
        "merged_into_database": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
