import unittest
from unittest.mock import patch

from poem_completion_api import TerminalAnalysisRequest, complete_terminal_poem


SPRING_DAWN_REQUEST = {
    "content_type": "poem_text",
    "confidence": 0.9,
    "poem": {
        "title": "春晓",
        "author": "孟浩然",
        "dynasty": "唐",
        "content": ["春眠不觉晓", "处处闻啼鸟", "夜来风雨声", "花落知多少"],
        "translation": "",
    },
    "objects": [],
}


class PoemCompletionApiTests(unittest.TestCase):
    def test_confirmed_poem_returns_completed_record(self):
        completed = {"status": "complete", "poem": {"title": "春晓", "content": ["春眠不觉晓"]}}
        with patch("poem_completion_api.complete_poem_from_terminal_analysis", return_value=completed) as mock_complete:
            response = complete_terminal_poem(TerminalAnalysisRequest(**SPRING_DAWN_REQUEST))

        self.assertTrue(response["success"])
        self.assertEqual(response["status"], "complete")
        self.assertEqual(response["poem"]["title"], "春晓")
        mock_complete.assert_called_once()

    def test_scene_never_calls_cloud_completion(self):
        with patch("poem_completion_api.complete_poem_from_terminal_analysis") as mock_complete:
            response = complete_terminal_poem(
                TerminalAnalysisRequest(content_type="scene", objects=["山峰"], confidence=0.9)
            )

        self.assertFalse(response["success"])
        self.assertEqual(response["status"], "not_poem")
        mock_complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
