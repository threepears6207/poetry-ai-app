import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tag_rules import normalize_poem_metadata, validate_tag_metadata


SOURCE_PATHS = (
    BACKEND_DIR / "data_sources" / "generated" / "children_poems_candidates.json",
    BACKEND_DIR / "data_sources" / "classic_poems" / "tang_poems_candidates.json",
)


def normalize_sources(apply_changes=False, source_paths=SOURCE_PATHS):
    report = {"applied": apply_changes, "files": [], "total_changed": 0}
    for path in map(Path, source_paths):
        poems = json.loads(path.read_text(encoding="utf-8"))
        normalized = [normalize_poem_metadata(poem) for poem in poems]
        errors = []
        for poem in normalized:
            item_errors = validate_tag_metadata(poem)
            if item_errors:
                errors.append({"id": poem.get("id"), "errors": item_errors})
        changed = sum(left != right for left, right in zip(poems, normalized))
        if errors:
            raise ValueError(json.dumps(errors, ensure_ascii=False, indent=2))
        if apply_changes:
            path.write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        report["files"].append({
            "path": str(path), "count": len(poems), "changed": changed,
        })
        report["total_changed"] += changed
    return report


def main():
    parser = argparse.ArgumentParser(description="按统一标签规则清洗诗库元数据")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(normalize_sources(args.apply), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
