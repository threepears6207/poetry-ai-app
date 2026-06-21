import base64
import hashlib
import io
import json
import os
import time
import uuid
import wave
from urllib.parse import urlencode

import websocket


VIVO_TTS_DOMAIN = "wss://api-ai.vivo.com.cn"
VIVO_TTS_PATH = "/tts"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1


class VivoTTSError(RuntimeError):
    """蓝心 TTS 调用失败。"""


def pcm_to_wav(pcm_bytes: bytes) -> bytes:
    """把蓝心返回的 24kHz/16bit/单声道 PCM 封装为 WAV。"""
    if not pcm_bytes:
        raise VivoTTSError("蓝心 TTS 未返回音频数据")

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)

    return output.getvalue()


def _build_user_id(app_id: str) -> str:
    raw = f"poetry-ai-app:{app_id or 'anonymous'}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_websocket_url(engineid: str, app_id: str) -> str:
    params = {
        "engineid": engineid,
        "system_time": int(time.time()),
        "user_id": _build_user_id(app_id),
        "model": "unknown",
        "product": "poetry-ai-app",
        "package": "poetry-ai-app",
        "client_version": "1.0",
        "system_version": "unknown",
        "sdk_version": "1.0",
        "android_version": "unknown",
        "requestId": str(uuid.uuid4()),
    }
    return f"{VIVO_TTS_DOMAIN}{VIVO_TTS_PATH}?{urlencode(params)}"


def synthesize_vivo_tts(
    text: str,
    engineid: str,
    vcn: str,
    speed: int = 50,
    volume: int = 50,
    timeout_seconds: int = 30,
) -> bytes:
    """调用蓝心 WebSocket TTS，并返回 WAV bytes。"""
    app_key = os.getenv("VIVO_APP_KEY", "").strip()
    app_id = os.getenv("VIVO_APP_ID", "").strip()
    clean_text = str(text or "").strip()

    if not app_key:
        raise VivoTTSError("缺少 VIVO_APP_KEY")
    if not clean_text:
        raise VivoTTSError("合成文本不能为空")
    if len(clean_text.encode("utf-8")) > 2048:
        raise VivoTTSError("合成文本超过蓝心 TTS 单次 2048 字节限制")

    url = _build_websocket_url(engineid, app_id)
    headers = [
        f"Authorization: Bearer {app_key}",
        "X-AI-GATEWAY-SIGNATURE: developers-aigc",
    ]
    payload = {
        "aue": 0,
        "auf": f"audio/L16;rate={SAMPLE_RATE}",
        "vcn": vcn,
        "speed": max(0, min(100, int(speed))),
        "volume": max(1, min(100, int(volume))),
        "text": base64.b64encode(clean_text.encode("utf-8")).decode("ascii"),
        "encoding": "utf8",
        "sfl": 1,
        "reqId": int(time.time() * 1000),
    }

    ws = None
    audio_buffer = bytearray()
    try:
        ws = websocket.create_connection(url, header=headers, timeout=timeout_seconds)

        handshake = ws.recv()
        if handshake:
            handshake_data = json.loads(handshake)
            if int(handshake_data.get("error_code", 0)) != 0:
                raise VivoTTSError(
                    f"蓝心 TTS 连接失败：{handshake_data.get('error_msg', handshake)}"
                )

        ws.send(json.dumps(payload, ensure_ascii=False))

        while True:
            message = ws.recv()
            if not message:
                raise VivoTTSError("蓝心 TTS 连接提前关闭")
            if isinstance(message, bytes):
                message = message.decode("utf-8")

            response = json.loads(message)
            error_code = int(response.get("error_code", 0))
            if error_code != 0:
                raise VivoTTSError(
                    f"蓝心 TTS 返回错误 {error_code}：{response.get('error_msg', '')}"
                )

            data = response.get("data")
            if not data:
                continue

            audio_base64 = data.get("audio", "")
            if audio_base64:
                audio_buffer.extend(base64.b64decode(audio_base64))

            if int(data.get("status", 1)) == 2:
                break

        return pcm_to_wav(bytes(audio_buffer))

    except VivoTTSError:
        raise
    except Exception as exc:
        raise VivoTTSError(f"蓝心 TTS 调用异常：{exc}") from exc
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
