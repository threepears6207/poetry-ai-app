"""用官方 PCM 样例验证本地 /asr/stream 实时通道。"""

import json
import sys
import time
from pathlib import Path

import websocket


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PCM_PATH = PROJECT_ROOT / "tmp" / "vivo_asr_demo" / "test-16k-16bit-mono.pcm"
STREAM_URL = "ws://127.0.0.1:8000/asr/stream"
PCM_FRAME_BYTES = 1280  # 16kHz / 16bit / 单声道 / 40ms


def main() -> int:
    pcm_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_PCM_PATH
    if not pcm_path.is_file():
        print(f"找不到 PCM 测试文件：{pcm_path}")
        return 2

    pcm_bytes = pcm_path.read_bytes()
    client = websocket.create_connection(STREAM_URL, timeout=30)
    try:
        client.send(json.dumps({
            "type": "start",
            "user_id": "stream_test_user",
            "net_type": 1,
            "end_vad_time": 1400,
        }, ensure_ascii=False))

        while True:
            event = json.loads(client.recv())
            print(json.dumps(event, ensure_ascii=False))
            if event.get("event") == "ready":
                break
            if event.get("event") == "error":
                return 1

        for offset in range(0, len(pcm_bytes), PCM_FRAME_BYTES):
            client.send_binary(pcm_bytes[offset: offset + PCM_FRAME_BYTES])
            if offset + PCM_FRAME_BYTES < len(pcm_bytes):
                time.sleep(0.04)
        client.send(json.dumps({"type": "end"}))

        while True:
            event = json.loads(client.recv())
            print(json.dumps(event, ensure_ascii=False))
            if event.get("event") == "final":
                return 0
            if event.get("event") == "error":
                return 1
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
