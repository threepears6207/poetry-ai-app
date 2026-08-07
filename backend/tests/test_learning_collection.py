import tempfile
import unittest
from pathlib import Path

from consolidation import (
    PracticeProgressIn,
    apply_practice_activity,
    collection_wall_data,
)
from database import get_connection
from poem_catalog import ResolvePoemsRequest, VerifiedPoemCandidate, resolve_verified_poems


class LearningCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "learning.db")
        result = resolve_verified_poems(ResolvePoemsRequest(candidates=[
            VerifiedPoemCandidate(
                title="测试诗", author="测试作者", dynasty="唐",
                content=["青山入远目", "白云过小桥"],
                tags=["山水", "白云"], theme_tags=["山水", "自然"],
                knowledge_tags=["画面理解"],
            )
        ]), self.db_path)
        self.poem_id = result["poems"][0]["poem_id"]
        connection = get_connection(self.db_path)
        with connection:
            connection.execute(
                "INSERT INTO users(user_id, age_level, age_range) VALUES ('child', 'age_5_7', '5-7岁')"
            )
            connection.execute(
                "INSERT INTO learning_records(user_id, poem_id) VALUES ('child', ?)",
                (self.poem_id,),
            )
        connection.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def progress(self, activity):
        return apply_practice_activity(PracticeProgressIn(
            poem_id=self.poem_id, user_id="child", activity=activity,
        ), self.db_path)

    def test_learning_starts_as_gray_card(self):
        wall = collection_wall_data("child", self.db_path)
        self.assertEqual(wall["total"], 1)
        self.assertEqual(wall["poems"][0]["collection_state"], "gray")
        self.assertEqual(wall["poems"][0]["flower_count"], 0)

    def test_one_activity_does_not_unlock(self):
        state, unlocked = self.progress("reading")
        self.assertFalse(unlocked)
        self.assertTrue(state["reading_completed"])
        self.assertFalse(state["connection_completed"])
        self.assertEqual(state["collection_state"], "gray")

    def test_both_activities_unlock_and_add_one_flower(self):
        self.progress("reading")
        state, unlocked = self.progress("connection")
        self.assertTrue(unlocked)
        self.assertEqual(state["collection_state"], "color")
        self.assertEqual(state["flower_count"], 1)

    def test_repeated_submission_is_idempotent(self):
        self.progress("reading")
        self.progress("connection")
        state, unlocked = self.progress("connection")
        self.assertFalse(unlocked)
        self.assertEqual(state["flower_count"], 1)
        self.assertEqual(state["practice_count"], 1)


if __name__ == "__main__":
    unittest.main()
