import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from poem_catalog import ResolvePoemsRequest, VerifiedPoemCandidate, resolve_verified_poems


def candidate(**overrides):
    values = {
        "title": "山中示例",
        "author": "示例作者",
        "dynasty": "唐",
        "content": ["青山入远目", "白云过小桥"],
        "tags": ["青山", "白云"],
        "theme_tags": ["青山", "自然"],
        "knowledge_tags": ["画面理解"],
        "source_url": "https://example.test/poem",
    }
    values.update(overrides)
    return VerifiedPoemCandidate(**values)


class PoemCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "catalog.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def resolve(self, *candidates, auto_insert=True):
        request = ResolvePoemsRequest(candidates=list(candidates), auto_insert=auto_insert)
        return resolve_verified_poems(request, self.db_path)

    def test_verified_new_poem_is_inserted_then_reused(self):
        first = self.resolve(candidate())
        self.assertEqual(first["poems"][0]["resolution"], "inserted")
        poem_id = first["poems"][0]["id"]
        self.assertEqual(poem_id, "poem_301")
        self.assertEqual(first["poems"][0]["library_scope"], "core")
        self.assertEqual(first["poems"][0]["poem_id"], poem_id)

        second = self.resolve(candidate(title="另一个标题"))
        self.assertEqual(second["poems"][0]["id"], poem_id)
        self.assertEqual(second["poems"][0]["resolution"], "reused")
        self.assertEqual(second["poems"][0]["match_type"], "content_hash")

    def test_new_poem_ids_increment_from_301(self):
        first = self.resolve(candidate())
        second = self.resolve(candidate(
            title="第二首示例",
            content=["松风吹远壑", "明月照清泉"],
        ))
        self.assertEqual(first["poems"][0]["id"], "poem_301")
        self.assertEqual(second["poems"][0]["id"], "poem_302")

    def test_internal_audit_fields_are_not_part_of_request_contract(self):
        with self.assertRaises(ValidationError):
            candidate(source_name="客户端来源", verification_status="pending")

    def test_internal_audit_fields_are_not_exposed_in_response(self):
        result = self.resolve(candidate())
        self.assertNotIn("source_name", result["poems"][0])
        self.assertNotIn("verification_status", result["poems"][0])

    def test_same_title_author_with_different_content_is_not_overwritten(self):
        self.resolve(candidate())
        result = self.resolve(candidate(content=["完全不同的第一句", "完全不同的第二句"]))
        self.assertFalse(result["success"])
        self.assertIn("禁止自动覆盖", result["rejected"][0]["errors"][0])

    def test_auto_insert_can_be_disabled(self):
        result = self.resolve(candidate(), auto_insert=False)
        self.assertFalse(result["success"])
        self.assertIn("未开启自动入库", result["rejected"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
