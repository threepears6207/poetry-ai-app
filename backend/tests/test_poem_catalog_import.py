import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_poems_to_db import import_catalog

SAMPLE = {
    "id": "poem_001", "title": "测试诗", "author": "测试作者", "dynasty": "唐",
    "content": ["青山入远目", "白云过小桥"], "translation": "测试译文",
    "tags": ["青山", "白云"], "age_level": "age_5_7", "age_range": "5-7岁",
    "difficulty": 2, "theme_tags": ["青山", "自然"], "knowledge_tags": ["画面理解"],
    "recommend_reason": "画面清楚。",
}


class CatalogImportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db_path = root / "catalog.db"
        self.source_path = root / "catalog.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, poems):
        self.source_path.write_text(json.dumps(poems, ensure_ascii=False), encoding="utf-8")

    def test_dry_run_does_not_insert(self):
        self.write([SAMPLE])
        result = import_catalog(False, self.db_path, self.source_path)
        self.assertFalse(result["applied"])
        self.assertEqual(result["planned_insert_count"], 1)
        self.assertEqual(result["after_count"], 0)

    def test_apply_is_idempotent_and_marks_recommendable(self):
        self.write([SAMPLE])
        first = import_catalog(True, self.db_path, self.source_path)
        second = import_catalog(True, self.db_path, self.source_path)
        self.assertEqual(first["after_count"], 1)
        self.assertEqual(first["recommend_eligible_count"], 1)
        self.assertEqual(second["planned_insert_count"], 0)
        self.assertEqual(second["after_count"], 1)

    def test_duplicate_content_fails_quality_gate(self):
        duplicate = copy.deepcopy(SAMPLE)
        duplicate["id"] = "poem_002"
        duplicate["title"] = "另一个标题"
        self.write([SAMPLE, duplicate])
        with self.assertRaisesRegex(ValueError, "正文重复"):
            import_catalog(False, self.db_path, self.source_path)

    def test_missing_metadata_fails_quality_gate(self):
        invalid = copy.deepcopy(SAMPLE)
        invalid["theme_tags"] = []
        self.write([invalid])
        with self.assertRaisesRegex(ValueError, "theme_tags"):
            import_catalog(False, self.db_path, self.source_path)


if __name__ == "__main__":
    unittest.main()
