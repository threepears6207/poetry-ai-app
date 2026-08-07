import tempfile
import unittest
from pathlib import Path

from consolidation import PracticeProgressIn, apply_practice_activity
from database import get_connection
from learning_dashboard import parent_overview, reminder_status, suppress_prompt_today
from poem_catalog import ResolvePoemsRequest, VerifiedPoemCandidate, resolve_verified_poems


class ReminderParentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "dashboard.db")
        result = resolve_verified_poems(ResolvePoemsRequest(candidates=[
            VerifiedPoemCandidate(
                title="测试诗", author="测试作者", dynasty="唐",
                content=["青山入远目", "白云过小桥"], tags=["山水", "白云"],
                theme_tags=["山水", "自然"], knowledge_tags=["画面理解"],
            )
        ]), self.db_path)
        self.poem_id = result["poems"][0]["poem_id"]
        connection = get_connection(self.db_path)
        with connection:
            connection.execute(
                "INSERT INTO users(user_id, age_level, age_range) VALUES ('child', 'age_5_7', '5-7岁')"
            )
            connection.execute(
                """
                INSERT INTO learning_records(user_id, poem_id, duration_seconds, created_at)
                VALUES ('child', ?, 90, '2026-08-06 10:00:00')
                """,
                (self.poem_id,),
            )
        connection.close()
        apply_practice_activity(PracticeProgressIn(
            user_id="child", poem_id=self.poem_id,
            activity="reading", completed=True,
        ), self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_prompt_and_badge_are_available_after_learning(self):
        status = reminder_status("child", self.db_path, "2026-08-06")
        self.assertTrue(status["show_practice_prompt"])
        self.assertTrue(status["practice_entry_badge"])

    def test_suppress_hides_prompt_but_keeps_badge(self):
        status = suppress_prompt_today("child", self.db_path, "2026-08-06")
        self.assertFalse(status["show_practice_prompt"])
        self.assertTrue(status["practice_entry_badge"])

    def test_suppression_expires_next_day(self):
        suppress_prompt_today("child", self.db_path, "2026-08-06")
        next_day = reminder_status("child", self.db_path, "2026-08-07")
        self.assertFalse(next_day["practice_prompt_suppressed"])

    def test_parent_overview_aggregates_learning_and_reading(self):
        result = parent_overview("child", self.db_path, "2026-08-06")
        self.assertEqual(result["today_learning"]["poem_count"], 1)
        self.assertEqual(result["today_learning"]["duration_seconds"], 90)
        self.assertEqual(result["pending_review_count"], 1)
        self.assertEqual(result["reading_completion"]["completed_count"], 1)
        self.assertEqual(result["recent_records"][0]["poem_id"], self.poem_id)


if __name__ == "__main__":
    unittest.main()
