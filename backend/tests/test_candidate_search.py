import tempfile
import unittest
from pathlib import Path

from candidate_search import ImageAnalysisInput, search_candidates
from poem_catalog import ResolvePoemsRequest, VerifiedPoemCandidate, resolve_verified_poems


class CandidateSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "search.db")
        candidates = [
            VerifiedPoemCandidate(title="静夜思", author="李白", dynasty="唐", content=["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"], tags=["月亮", "思乡"], theme_tags=["夜晚", "思乡"], knowledge_tags=["画面理解"], age_level="age_3_4", age_range="3-4岁", difficulty=1),
            VerifiedPoemCandidate(title="春晓", author="孟浩然", dynasty="唐", content=["春眠不觉晓", "处处闻啼鸟", "夜来风雨声", "花落知多少"], tags=["春天", "鸟"], theme_tags=["春天", "自然"], knowledge_tags=["自然意象"], age_level="age_3_4", age_range="3-4岁", difficulty=1),
            VerifiedPoemCandidate(title="山行", author="杜牧", dynasty="唐", content=["远上寒山石径斜", "白云生处有人家", "停车坐爱枫林晚", "霜叶红于二月花"], tags=["山", "白云", "秋天"], theme_tags=["山林", "秋天"], knowledge_tags=["画面理解"], age_level="age_5_7", difficulty=2),
        ]
        resolve_verified_poems(ResolvePoemsRequest(candidates=candidates), self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_text_fragment_prefers_correct_poem(self):
        result = search_candidates(ImageAnalysisInput(content_type="handwritten", recognized_text="举头望明月低头思故乡", confidence=0.9), self.db_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["poems"][0]["title"], "静夜思")

    def test_new_poem_text_contract(self):
        request = ImageAnalysisInput.model_validate({
            "type": "poem_text",
            "poem_text": "举头望明月低头思故乡",
            "confidence": 0.9,
        })
        result = search_candidates(request, self.db_path)
        self.assertEqual(request.content_type, "poem_text")
        self.assertEqual(request.recognized_text, request.poem_text)
        self.assertEqual(result["poems"][0]["title"], "静夜思")

    def test_nested_poem_contract_returns_one_certain_match(self):
        request = ImageAnalysisInput.model_validate({
            "content_type": "poem_text",
            "poem": {
                "title": "春晓", "author": "孟浩然", "dynasty": "唐",
                "content": ["春眠不觉晓", "处处闻啼鸟"], "translation": "",
            },
            "objects": [],
            "confidence": 0.9,
        })
        result = search_candidates(request, self.db_path)
        self.assertEqual(request.recognized_title, "春晓")
        self.assertEqual(request.recognized_text, "春眠不觉晓处处闻啼鸟")
        self.assertEqual(len(result["poems"]), 1)
        self.assertEqual(result["poems"][0]["title"], "春晓")

    def test_new_nested_scene_contract(self):
        request = ImageAnalysisInput.model_validate({
            "type": "scene",
            "scene": {"objects": ["枫叶", "山"], "season": "autumn"},
            "confidence": 0.88,
        })
        result = search_candidates(request, self.db_path)
        self.assertEqual(request.objects, ["枫叶", "山"])
        self.assertEqual(result["poems"][0]["title"], "山行")

    def test_scene_uses_objects_season_and_tags(self):
        result = search_candidates(ImageAnalysisInput(content_type="scene", objects=["枫叶", "山"], season="autumn", confidence=0.88, debug=True), self.db_path)
        self.assertTrue(result["success"])
        self.assertEqual(result["poems"][0]["title"], "山行")
        self.assertIn("scene", result["poems"][0]["match_sources"])

    def test_low_confidence_scene_requests_retake(self):
        result = search_candidates(ImageAnalysisInput(content_type="scene", objects=["山"], confidence=0.1), self.db_path)
        self.assertEqual(result["status"], "retake")
        self.assertEqual(result["error_code"], "low_confidence")
        self.assertEqual(result["poems"], [])


if __name__ == "__main__":
    unittest.main()
