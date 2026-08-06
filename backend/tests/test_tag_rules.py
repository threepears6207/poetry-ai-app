import unittest

from tag_rules import (
    ALLOWED_KNOWLEDGE_TAGS,
    normalize_poem_metadata,
    validate_tag_metadata,
)


class TagRulesTests(unittest.TestCase):
    def poem(self, **updates):
        value = {
            "title": "测试诗", "author": "李白", "dynasty": "唐",
            "content": ["江上明月照归舟", "故乡遥在白云边"],
            "tags": ["李白", "月", "思乡"],
            "theme_tags": ["古诗", "情感"],
            "knowledge_tags": ["唐诗", "李白"],
            "age_level": "age_5_7", "age_range": "5-7岁", "difficulty": 2,
        }
        value.update(updates)
        return value

    def test_normalization_removes_author_and_invalid_knowledge(self):
        result = normalize_poem_metadata(self.poem())
        self.assertNotIn("李白", result["tags"])
        self.assertNotIn("古诗", result["theme_tags"])
        self.assertTrue(set(result["knowledge_tags"]) <= ALLOWED_KNOWLEDGE_TAGS)
        self.assertEqual(validate_tag_metadata(result), [])

    def test_theme_reuses_one_or_two_core_tags(self):
        result = normalize_poem_metadata(self.poem())
        reused = set(result["tags"]) & set(result["theme_tags"])
        self.assertGreaterEqual(len(reused), 1)
        self.assertLessEqual(len(reused), 2)

    def test_strict_validation_rejects_bad_counts_and_values(self):
        invalid = self.poem(
            tags=["月亮"], theme_tags=["自然"], knowledge_tags=["唐诗"],
            difficulty=4,
        )
        errors = validate_tag_metadata(invalid)
        self.assertTrue(any("tags 必须" in error for error in errors))
        self.assertTrue(any("knowledge_tags" in error for error in errors))
        self.assertTrue(any("difficulty" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
