import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.import_poems_to_db import CORE_SOURCE_PATH, SUPPLEMENT_SOURCE_PATH
from tag_rules import normalize_poem_metadata, validate_tag_metadata


def enrich_file(path):
    path = Path(path)
    poems = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for index, poem in enumerate(poems):
        enriched = normalize_poem_metadata(poem)
        # 本脚本只负责端侧视觉匹配标签，不改知识点或其他诗歌元数据。
        enriched["knowledge_tags"] = list(poem.get("knowledge_tags") or [])
        errors = validate_tag_metadata(enriched)
        if errors:
            raise ValueError(f"{poem.get('id', index)} 标签校验失败：{'; '.join(errors)}")
        if enriched != poem:
            poems[index] = enriched
            changed += 1
    path.write_text(
        json.dumps(poems, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return changed


def main():
    result = {
        str(path): enrich_file(path)
        for path in (CORE_SOURCE_PATH, SUPPLEMENT_SOURCE_PATH)
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
