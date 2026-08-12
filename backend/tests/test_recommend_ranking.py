import unittest
from collections import Counter

from recommend import rank_recommendations


def poem(poem_id, title, tags, difficulty=1, author="甲", age="age_3_4"):
    return {
        "id": poem_id, "title": title, "author": author, "dynasty": "唐",
        "content": ["第一句", "第二句"], "translation": "",
        "tags": tags, "theme_tags": tags, "knowledge_tags": [],
        "age_level": age, "age_range": "3-4岁", "difficulty": difficulty,
        "recommend_reason": "",
    }


class RecommendRankingTests(unittest.TestCase):
    def context(self, **updates):
        value = {
            "learned_ids": set(), "recent_ids": [], "reading_scores": {},
            "consolidations": {}, "preference_counts": Counter(),
            "target_difficulty": 1.0,
        }
        value.update(updates)
        return value

    def test_due_review_poem_is_excluded_from_recommendations(self):
        poems = [poem("due", "待温习", ["月亮"]), poem("new", "新诗", ["春天"])]
        context = self.context(
            learned_ids={"due"},
            consolidations={"due": {"status": "待巩固", "next_review_date": ""}},
        )
        result = rank_recommendations(poems, context, "age_3_4")
        self.assertEqual([item["id"] for item in result], ["new"])
        self.assertEqual(result[0]["recommend_type"], "new")

    def test_weak_and_mastered_learned_poems_are_both_excluded(self):
        poems = [poem("weak", "薄弱诗", ["月亮"]), poem("done", "已掌握", ["山水"])]
        context = self.context(
            learned_ids={"weak", "done"}, reading_scores={"weak": 50, "done": 95},
        )
        result = rank_recommendations(poems, context, "age_3_4")
        self.assertEqual(result, [])

    def test_consecutive_same_theme_is_penalized(self):
        poems = [
            poem("last", "刚学", ["春天"], author="甲"),
            poem("same", "同主题", ["春天"], author="乙"),
            poem("varied", "换主题", ["月亮"], author="丙"),
        ]
        context = self.context(learned_ids={"last"}, recent_ids=["last"])
        result = rank_recommendations(poems, context, "age_3_4")
        self.assertEqual(result[0]["id"], "varied")

    def test_exclude_ids_supports_swap(self):
        poems = [poem("one", "一", ["春天"]), poem("two", "二", ["月亮"])]
        result = rank_recommendations(
            poems, self.context(), "age_3_4", exclude_ids={"one"}
        )
        self.assertEqual([item["id"] for item in result], ["two"])

    def test_recommendation_list_avoids_adjacent_same_theme(self):
        poems = [
            poem("spring_one", "春一", ["春天"]),
            poem("spring_two", "春二", ["春天"]),
            poem("moon", "月夜", ["月亮"]),
        ]
        result = rank_recommendations(poems, self.context(), "age_3_4")
        self.assertEqual(result[0]["id"], "moon")
        self.assertIn("spring", result[1]["id"])
        self.assertIn("spring", result[2]["id"])

    def test_debug_explains_list_diversity_penalty(self):
        poems = [
            poem("one", "一", ["春天"]),
            poem("two", "二", ["春天"]),
        ]
        result = rank_recommendations(poems, self.context(), "age_3_4", debug=True)
        self.assertEqual(result[0]["score_components"]["list_diversity_penalty"], 0.0)
        self.assertLess(result[1]["score_components"]["list_diversity_penalty"], 0)


if __name__ == "__main__":
    unittest.main()
