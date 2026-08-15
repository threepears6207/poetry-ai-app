import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_generate


def make_group(group_id, poem_id, task_id, created_at, updated_at, status="succeeded"):
    return {
        "group_id": group_id,
        "cache_key": poem_id,
        "poem_id": poem_id,
        "poem_title": "test poem",
        "status": status,
        "segment_task_ids": [task_id],
        "created_at": created_at,
        "updated_at": updated_at,
    }


def make_task(task_id, poem_id, status, video_url=""):
    return {
        "task_id": task_id,
        "cache_key": poem_id,
        "poem_id": poem_id,
        "status": status,
        "video_url": video_url,
        "updated_at": "2026-08-14T10:00:00+08:00",
    }


class VideoCacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = {
            "poems": {"poem_test": {"group_id": "new_failed"}},
            "groups": {
                "old_success": make_group(
                    "old_success", "poem_test", "task_old",
                    "2026-08-14T09:00:00+08:00", "2026-08-14T09:00:00+08:00",
                ),
                "new_failed": make_group(
                    "new_failed", "poem_test", "task_new",
                    "2026-08-14T10:00:00+08:00", "2026-08-14T10:00:00+08:00", "failed",
                ),
            },
            "tasks": {
                "task_old": make_task("task_old", "poem_test", "succeeded", "/static/videos/old.mp4"),
                "task_new": make_task("task_new", "poem_test", "failed"),
            },
        }

    def test_submit_reuses_latest_success_when_pointer_is_failed(self):
        request = video_generate.VideoGenerateRequest(
            poem_id="poem_test",
            poem_title="test poem",
            poem_content=["line one", "line two"],
        )

        with patch.object(video_generate, "_load_cache", return_value=self.cache), patch.object(
            video_generate, "_submit_segment_task"
        ) as submit_task:
            result = video_generate.submit_poem_video(request)

        self.assertTrue(result["success"])
        self.assertTrue(result["from_cache"])
        self.assertEqual(result["group_id"], "old_success")
        submit_task.assert_not_called()

    def test_ready_poem_list_returns_one_latest_success_per_poem(self):
        with patch.object(video_generate, "_load_cache", return_value=self.cache):
            result = video_generate.list_ready_poem_videos()

        self.assertTrue(result["success"])
        self.assertEqual(result["videos"], [{
            "poem_id": "poem_test",
            "poem_title": "test poem",
            "group_id": "old_success",
            "status": "succeeded",
            "video_url": "/static/videos/old.mp4",
            "updated_at": "2026-08-14T09:00:00+08:00",
            "created_at": "2026-08-14T09:00:00+08:00",
        }])

    def test_shared_video_cache_is_reused_after_a_fresh_start(self):
        cache = {
            "poems": {"poem_shared": {"group_id": "shared_video"}},
            "groups": {
                "shared_video": make_group(
                    "shared_video", "poem_shared", "video_shared",
                    "2026-08-15T10:00:00+08:00", "2026-08-15T10:00:00+08:00",
                )
            },
            "tasks": {
                "video_shared": make_task(
                    "video_shared", "poem_shared", "succeeded",
                    "/static/videos/poems/poem_shared/video.mp4",
                )
            },
        }
        request = video_generate.VideoGenerateRequest(
            poem_id="poem_shared",
            poem_title="shared poem",
            poem_content=["line one", "line two"],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "video_cache.json"
            cache_file.write_text(json.dumps(cache), encoding="utf-8")
            with patch.object(video_generate, "CACHE_FILE", cache_file), patch.object(
                video_generate, "_submit_segment_task"
            ) as submit_task:
                result = video_generate.submit_poem_video(request)

        self.assertTrue(result["success"])
        self.assertTrue(result["from_cache"])
        self.assertEqual(result["segments"][0]["video_url"], "/static/videos/poems/poem_shared/video.mp4")
        submit_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
