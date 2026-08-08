import json
import unittest
from unittest.mock import Mock, patch

from poem_completion import (
    PoemCompletionError,
    _extract_json_object,
    _validate_model_result,
    build_completion_messages,
    build_completion_prompt,
    complete_poem_from_terminal_analysis,
)


TERMINAL_SPRING_DAWN = {
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

SPRING_DAWN_RECORD = {
    "title": "春晓",
    "author": "孟浩然",
    "dynasty": "唐朝",
    "content": ["春眠不觉晓，", "处处闻啼鸟。", "夜来风雨声，", "花落知多少。"],
    "translation": "春天睡醒时天已经亮了，到处能听见鸟儿啼叫。夜里有风雨声，不知道落花有多少。",
    "tags": ["春天", "自然", "鸟鸣", "落花"],
    "age_level": "age_3_4",
    "age_range": "3-4岁",
    "difficulty": 1,
    "theme_tags": ["春天", "自然", "生活观察"],
    "knowledge_tags": ["背诵积累", "画面理解", "自然意象"],
}


class PoemCompletionTests(unittest.TestCase):
    def test_valid_database_aligned_record_is_normalized(self):
        result = _validate_model_result(SPRING_DAWN_RECORD, TERMINAL_SPRING_DAWN)
        self.assertEqual(result["dynasty"], "唐")
        self.assertEqual(result["content"][0], "春眠不觉晓")
        self.assertEqual(result["knowledge_tags"], ["背诵积累", "画面理解", "自然意象"])

    def test_model_cannot_replace_confirmed_title(self):
        invalid = {**SPRING_DAWN_RECORD, "title": "静夜思", "author": "李白"}
        with self.assertRaisesRegex(PoemCompletionError, "title"):
            _validate_model_result(invalid, TERMINAL_SPRING_DAWN)

    def test_model_cannot_replace_confirmed_content(self):
        invalid = {
            **SPRING_DAWN_RECORD,
            "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
        }
        with self.assertRaisesRegex(PoemCompletionError, "content"):
            _validate_model_result(invalid, TERMINAL_SPRING_DAWN)

    def test_translation_copying_poem_is_rejected(self):
        invalid = {
            **SPRING_DAWN_RECORD,
            "translation": "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。",
        }
        with self.assertRaises(PoemCompletionError):
            _validate_model_result(invalid, TERMINAL_SPRING_DAWN)

    def test_unknown_knowledge_tag_is_rejected(self):
        invalid = {**SPRING_DAWN_RECORD, "knowledge_tags": ["古诗赏析"]}
        with self.assertRaises(PoemCompletionError):
            _validate_model_result(invalid, TERMINAL_SPRING_DAWN)

    def test_age_level_and_range_must_match(self):
        invalid = {**SPRING_DAWN_RECORD, "age_range": "5-7岁"}
        with self.assertRaises(PoemCompletionError):
            _validate_model_result(invalid, TERMINAL_SPRING_DAWN)

    def test_unexpected_status_field_is_rejected(self):
        invalid = {**SPRING_DAWN_RECORD, "status": "complete"}
        with self.assertRaises(PoemCompletionError):
            _validate_model_result(invalid, TERMINAL_SPRING_DAWN)

    def test_markdown_and_think_tags_are_removed_before_json_parse(self):
        content = '<think>分析过程</think>\n```json\n{"title":"春晓"}\n```'
        self.assertEqual(_extract_json_object(content), {"title": "春晓"})

    def test_cloud_request_returns_database_aligned_record(self):
        fake_response = Mock()
        fake_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(SPRING_DAWN_RECORD, ensure_ascii=False)}}]
        }
        with patch.dict("os.environ", {"VIVO_APP_KEY": "test-key"}), patch(
            "poem_completion.requests.post", return_value=fake_response
        ) as mocked_post:
            result = complete_poem_from_terminal_analysis(TERMINAL_SPRING_DAWN)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["poem"]["title"], "春晓")
        self.assertEqual(result["poem"]["tags"], ["春天", "自然", "鸟鸣", "落花"])
        messages = mocked_post.call_args.kwargs["json"]["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("诗名：春晓", messages[1]["content"])

    def test_prompt_contains_full_poems_record_rules(self):
        prompt = build_completion_prompt(TERMINAL_SPRING_DAWN)
        self.assertIn('"knowledge_tags"', prompt)
        self.assertIn("诗名：春晓", prompt)
        self.assertIn("1. 春眠不觉晓", prompt)
        self.assertIn("使用原子化的核心名词、动作或概念标签", prompt)
        self.assertIn("直接复用 tags 中的 1 到 2 项", prompt)
        self.assertIn("二字和四字标签仅用于展示写法", prompt)
        self.assertIn("珍惜粮食", prompt)
        self.assertNotIn("静夜思", prompt)

    def test_messages_use_short_system_and_dynamic_user_content(self):
        messages = build_completion_messages(TERMINAL_SPRING_DAWN)
        self.assertEqual(len(messages), 2)
        self.assertIn("只输出一个符合要求的 JSON 对象", messages[0]["content"])
        self.assertIn("作者：孟浩然", messages[1]["content"])

    def test_scene_is_rejected_before_cloud_request(self):
        with self.assertRaises(PoemCompletionError):
            build_completion_prompt({"content_type": "scene", "objects": ["山峰"]})


if __name__ == "__main__":
    unittest.main()
