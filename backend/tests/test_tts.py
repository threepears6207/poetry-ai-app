import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tts


class TTSUnitTests(unittest.TestCase):
    def test_fixed_prompts_use_short_prebuilt_copy(self):
        response = tts.list_fixed_prompts()
        self.assertEqual(response["prompts"]["camera"]["text"], "拍一拍找古诗")
        self.assertEqual(response["prompts"]["today"]["text"], "学一首新诗")
        self.assertEqual(response["prompts"]["search"]["text"], "找你喜欢的诗")
        self.assertTrue(response["prompts"]["today"]["audio_url"].endswith(".mp3"))

    def test_prepare_poem_text_keeps_chinese_and_adds_pauses(self):
        result = tts.prepare_poem_text("床前明月光，疑是地上霜。举头望明月，低头思故乡。")
        self.assertEqual(result, "床前明月光，疑是地上霜。……举头望明月，低头思故乡。")

    def test_invalid_rate_and_pitch_fall_back_to_safe_defaults(self):
        self.assertEqual(tts.get_poem_rate("fast"), "-18%")
        self.assertEqual(tts.get_poem_pitch("high"), "-2Hz")

    def test_cache_key_changes_with_reading_options(self):
        base = tts.build_audio_filename("春晓", "child", "poem", "-18%", "-2Hz")
        changed = tts.build_audio_filename("春晓", "male", "poem", "-18%", "-2Hz")
        self.assertNotEqual(base, changed)

    def test_generate_tts_reuses_existing_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            audio_dir = Path(directory)
            request = tts.TTSRequest(text="春眠不觉晓。", voice="child")
            prepared = tts.prepare_poem_text(request.text)
            filename = tts.build_audio_filename(prepared, "child", "poem", "-18%", "-2Hz")
            (audio_dir / filename).write_bytes(b"cached audio")
            with patch.object(tts, "AUDIO_DIR", audio_dir), patch.object(tts, "call_edge_tts") as mocked:
                response = tts.generate_tts(request)
            self.assertTrue(response["success"])
            self.assertTrue(response["cache_hit"])
            mocked.assert_not_called()

    def test_empty_text_returns_compatible_failure(self):
        response = tts.generate_tts(tts.TTSRequest(text="   "))
        self.assertFalse(response["success"])
        self.assertEqual(response["audio_url"], "")


if __name__ == "__main__":
    unittest.main()
