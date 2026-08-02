import base64
import json
import os
import unittest
from unittest.mock import patch

import asr


class FakeWebSocket:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent_text = []
        self.sent_binary = []
        self.closed = False

    def recv(self):
        return self.responses.pop(0)

    def send(self, value):
        self.sent_text.append(value)

    def send_binary(self, value):
        self.sent_binary.append(value)

    def close(self):
        self.closed = True


class VivoShortASRTests(unittest.TestCase):
    def setUp(self):
        self.request = asr.ASRRequest(
            pcm_base64=base64.b64encode(b"\x00\x00" * 800).decode("ascii"),
            net_type=1,
            user_id="test_user",
        )

    def test_rejects_non_pcm_base64(self):
        with self.assertRaises(asr.VivoASRError):
            asr._decode_pcm("not-base64")

    def test_preserves_existing_no_proxy_hosts_when_adding_vivo(self):
        value = asr._with_vivo_no_proxy("localhost,127.0.0.1")

        self.assertEqual(value, "localhost,127.0.0.1,api-ai.vivo.com.cn")
        self.assertEqual(
            asr._with_vivo_no_proxy(value),
            "localhost,127.0.0.1,api-ai.vivo.com.cn",
        )

    def test_validates_realtime_pcm_frames_and_limit(self):
        frame = b"\x00\x00" * 640

        self.assertEqual(asr._validate_pcm_stream_frame(frame, 0), 1280)
        with self.assertRaises(asr.VivoASRError):
            asr._validate_pcm_stream_frame(b"\x00", 0)
        with self.assertRaises(asr.VivoASRError) as error:
            asr._validate_pcm_stream_frame(frame, asr.MAX_PCM_BYTES)
        self.assertEqual(error.exception.code, 10008)

    def test_sends_started_packet_and_returns_final_text(self):
        fake_socket = FakeWebSocket([
            json.dumps({"action": "started", "code": 0, "sid": "sid-1"}),
            json.dumps({
                "action": "result",
                "type": "asr",
                "code": 0,
                "data": {"result_id": 1, "text": "春眠不觉晓", "is_last": True},
            }),
        ])
        with patch.dict(os.environ, {"VIVO_APP_KEY": "test-key"}, clear=False), patch.object(
            asr.websocket, "create_connection", return_value=fake_socket
        ):
            result = asr.recognize_pcm_with_vivo(self.request)

        self.assertEqual(result.text, "春眠不觉晓")
        self.assertEqual(result.sid, "sid-1")
        self.assertEqual(len(fake_socket.sent_text), 1)
        started_packet = json.loads(fake_socket.sent_text[0])
        self.assertEqual(started_packet["type"], "started")
        self.assertEqual(started_packet["asr_info"]["audio_type"], "pcm")
        self.assertIn(b"--end--", fake_socket.sent_binary)
        self.assertTrue(fake_socket.closed)

    def test_maps_vivo_error_code(self):
        fake_socket = FakeWebSocket([
            json.dumps({"action": "error", "code": 10008, "desc": "audio too long"}),
        ])
        with patch.dict(os.environ, {"VIVO_APP_KEY": "test-key"}, clear=False), patch.object(
            asr.websocket, "create_connection", return_value=fake_socket
        ), self.assertRaises(asr.VivoASRError) as error:
            asr.recognize_pcm_with_vivo(self.request)

        self.assertEqual(error.exception.code, 10008)
        self.assertIn("音频超长", str(error.exception))


if __name__ == "__main__":
    unittest.main()
