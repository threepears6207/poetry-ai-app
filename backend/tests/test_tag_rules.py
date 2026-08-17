import unittest

from tag_rules import (
    ALLOWED_KNOWLEDGE_TAGS,
    extract_visual_object_tags,
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

    def test_visual_tags_include_parent_and_specific_object(self):
        value = self.poem(content=["鹅鹅鹅，曲项向天歌", "白毛浮绿水，红掌拨清波"])
        self.assertEqual(extract_visual_object_tags(value)[:2], ["动物", "白鹅"])
        result = normalize_poem_metadata(value)
        self.assertIn("动物", result["tags"])
        self.assertIn("白鹅", result["tags"])

    def test_visual_tags_cover_terminal_scene_vocabulary(self):
        value = self.poem(content=["白鹭飞过雪山", "渔舟停在溪边柳下"])
        visual = extract_visual_object_tags(value)
        for expected in ("动物", "白鹭", "水", "溪水", "山", "雪山", "树", "柳树", "船", "渔船"):
            self.assertIn(expected, visual)

    def test_visual_tags_do_not_treat_galaxy_or_niulang_as_scene_objects(self):
        value = self.poem(content=["疑是银河落九天", "牛郎织女遥相望"])
        visual = extract_visual_object_tags(value)
        self.assertNotIn("河流", visual)
        self.assertNotIn("耕牛", visual)

    def test_fishing_action_and_boat_across_lines_produce_fishing_boat(self):
        value = self.poem(content=["孤舟蓑笠翁", "独钓寒江雪"])
        visual = extract_visual_object_tags(value)
        self.assertIn("船", visual)
        self.assertIn("渔船", visual)


if __name__ == "__main__":
    unittest.main()
