import argparse
import json
import os
import re
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json"
DRAFT_PATH = BACKEND_DIR / "data_sources" / "generated" / "poem_metadata_draft.json"
API_URL = "https://api-ai.vivo.com.cn/v1/chat/completions"
MODEL = "Volc-DeepSeek-V3.2"
BASE_TAG = "背诵积累"
ALLOWED_DETAIL_TAGS = {
    "画面理解", "自然意象", "情感理解", "意象理解", "观察能力", "生活常识",
    "价值启蒙", "简单哲理", "夸张修辞", "比喻感知", "情绪感知", "想象能力",
    "自然认知", "节奏感知", "方位认知", "生活观察", "生活画面", "季节意象",
    "动态意象", "文化常识", "比喻理解",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def strip_wrapper(text):
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    return re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()


def build_messages(batch, catalog_map):
    input_items = []
    for item in batch:
        poem = catalog_map[item["id"]]
        input_items.append({
            "id": item["id"],
            "title": poem["title"],
            "content": poem["content"],
            "translation": item["translation"],
            "tags": item["tags"],
        })
    system_prompt = """你是3至7岁儿童古诗学习内容编辑。
请根据每首诗的正文、译文和主题，从给定词表中选择最适合儿童学习的两个知识标签。
知识标签表示学习重点，不是诗歌内容标签。
每首必须恰好选择两个不同标签，只能使用给定词表，不得创造新词。
选择要有诗句依据，避免所有诗机械使用同一组合。
只输出合法JSON数组，每个输入id必须且只能出现一次，不要解释。"""
    user_prompt = f"""可选知识标签：{json.dumps(sorted(ALLOWED_DETAIL_TAGS), ensure_ascii=False)}

输出格式：
[
  {{"id": "原id", "knowledge_tags": ["标签1", "标签2"]}}
]

古诗数据：
{json.dumps(input_items, ensure_ascii=False, indent=2)}"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_model(batch, catalog_map, app_key):
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_key}",
        },
        json={
            "requestId": str(uuid.uuid4()),
            "model": MODEL,
            "messages": build_messages(batch, catalog_map),
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    result = json.loads(strip_wrapper(content))
    if not isinstance(result, list):
        raise ValueError("模型返回结果不是数组")
    expected_ids = {item["id"] for item in batch}
    result_map = {}
    for item in result:
        poem_id = item.get("id")
        tags = item.get("knowledge_tags") or []
        if poem_id not in expected_ids or poem_id in result_map:
            raise ValueError(f"模型返回未知或重复id：{poem_id}")
        if len(tags) != 2 or len(set(tags)) != 2:
            raise ValueError(f"{poem_id}必须返回两个不同知识标签：{tags}")
        if not set(tags) <= ALLOWED_DETAIL_TAGS:
            raise ValueError(f"{poem_id}出现词表外知识标签：{tags}")
        result_map[poem_id] = [BASE_TAG, *tags]
    missing = expected_ids - set(result_map)
    if missing:
        raise ValueError(f"模型漏掉id：{sorted(missing)}")
    return result_map


def main():
    parser = argparse.ArgumentParser(description="为古诗草稿生成三个knowledge_tags")
    parser.add_argument("--batch-size", type=int, default=15)
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
    pending = [item for item in drafts if len(item.get("knowledge_tags") or []) != 3]
    batch_size = max(1, min(20, args.batch_size))
    batches = [pending[index:index + batch_size] for index in range(0, len(pending), batch_size)]

    updated = 0
    for batch_index, batch in enumerate(batches, start=1):
        for attempt in range(1, max(1, args.retries) + 1):
            try:
                generated = call_model(batch, catalog_map, app_key)
                break
            except Exception as error:
                if attempt >= max(1, args.retries):
                    raise RuntimeError(
                        f"第{batch_index}批连续{attempt}次生成失败：{error}"
                    ) from error
                print(f"第{batch_index}批第{attempt}次失败，准备重试：{error}")
                time.sleep(attempt * 2)
        for poem_id, tags in generated.items():
            draft_map[poem_id]["knowledge_tags"] = tags
        updated += len(generated)
        output = sorted(draft_map.values(), key=lambda item: item["id"])
        DRAFT_PATH.write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"知识标签第{batch_index}/{len(batches)}批完成，累计{updated}首")
        if batch_index < len(batches):
            time.sleep(1)

    print(json.dumps({
        "updated_count": updated,
        "draft_total_count": len(draft_map),
        "remaining_invalid_count": sum(
            1 for item in draft_map.values()
            if len(item.get("knowledge_tags") or []) != 3
        ),
        "merged_into_catalog": False,
        "merged_into_database": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
