import unittest
from unittest.mock import patch

from candidate_search import _poem_card
from poems import search_poems
from recommend import rank_recommendations


POEM = {
    "id": "poem_001",
    "title": "春晓",
    "author": "孟浩然",
    "dynasty": "唐",
    "content": ["春眠不觉晓", "处处闻啼鸟"],
    "tags": ["春天", "鸟鸣"],
    "theme_tags": ["春天", "自然"],
    "knowledge_tags": ["自然意象"],
    "age_level": "age_3_4",
    "difficulty": 1,
}
CORE_CARD_FIELDS = {
    "poem_id", "id", "title", "author", "dynasty", "cover_url",
    "age_level", "difficulty", "learned_state",
}


class PoemCardContractTests(unittest.TestCase):
    def test_search_candidate_and_recommendation_share_core_fields(self):
        with patch("poems.load_poems", return_value=[POEM]):
            search_card = search_poems(
                keyword="春晓", author="", dynasty="", tag="", page=1, page_size=10,
            )["data"][0]

        candidate_card = _poem_card({
            "poem": POEM, "score": 1.0, "text_score": 1.0,
            "scene_score": 0.0, "sources": ["text"],
        })
        context = {
            "learned_ids": set(), "recent_ids": [], "reading_scores": {},
            "consolidations": {}, "preference_counts": {}, "target_difficulty": 1.0,
        }
        recommend_card = rank_recommendations(
            [POEM], context, "age_3_4",
        )[0]

        for card in (search_card, candidate_card, recommend_card):
            self.assertTrue(CORE_CARD_FIELDS.issubset(card))
            self.assertEqual(card["poem_id"], "poem_001")
            self.assertEqual(card["id"], card["poem_id"])

        self.assertEqual(recommend_card["learned_state"], "unlearned")


if __name__ == "__main__":
    unittest.main()
