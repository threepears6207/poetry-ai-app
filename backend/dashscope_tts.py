import base64
import os

import requests


DEFAULT_TTS_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/"
    "aigc/multimodal-generation/generation"
)
DEFAULT_TTS_MODEL = "qwen3-tts-instruct-flash"


class DashScopeTTSError(RuntimeError):
    """百炼语音合成调用失败。"""


def synthesize_dashscope_tts(
    text: str,
    voice: str,
    instructions: str,
    timeout_seconds: int = 60,
) -> bytes:
    """调用千问3-TTS并下载完整 WAV 音频。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    clean_text = str(text or "").strip()
    clean_voice = str(voice or "").strip()
    clean_instructions = str(instructions or "").strip()

    if not api_key:
        raise DashScopeTTSError("缺少 DASHSCOPE_API_KEY")
    if not clean_text:
        raise DashScopeTTSError("合成文本不能为空")
    if not clean_voice:
        raise DashScopeTTSError("诗人音色不能为空")
    if len(clean_text) > 600:
        raise DashScopeTTSError("合成文本超过千问3-TTS单次600字符限制")

    api_url = os.getenv("DASHSCOPE_TTS_URL", DEFAULT_TTS_URL).strip() or DEFAULT_TTS_URL
    model = os.getenv("DASHSCOPE_TTS_MODEL", DEFAULT_TTS_MODEL).strip() or DEFAULT_TTS_MODEL
    payload = {
        "model": model,
        "input": {
            "text": clean_text,
            "voice": clean_voice,
            "language_type": "Chinese",
        },
    }
    if clean_instructions:
        payload["input"]["instructions"] = clean_instructions
        payload["input"]["optimize_instructions"] = True

    try:
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise DashScopeTTSError(f"千问语音合成请求异常：{exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise DashScopeTTSError(
            f"千问语音合成返回非JSON响应（HTTP {response.status_code}）"
        ) from exc

    if response.status_code != 200:
        message = result.get("message") or result.get("error", {}).get("message") or response.text
        raise DashScopeTTSError(
            f"千问语音合成失败（HTTP {response.status_code}）：{message}"
        )

    audio = result.get("output", {}).get("audio") or {}
    audio_data = str(audio.get("data") or "").strip()
    if audio_data:
        try:
            decoded = base64.b64decode(audio_data, validate=True)
        except Exception as exc:
            raise DashScopeTTSError("千问语音合成返回了无效的Base64音频") from exc
        if decoded:
            return decoded

    audio_url = str(audio.get("url") or "").strip()
    if not audio_url:
        raise DashScopeTTSError("千问语音合成未返回音频数据或下载地址")

    try:
        audio_response = requests.get(audio_url, timeout=timeout_seconds)
        audio_response.raise_for_status()
    except requests.RequestException as exc:
        raise DashScopeTTSError(f"下载千问语音失败：{exc}") from exc

    if not audio_response.content:
        raise DashScopeTTSError("下载到的千问语音文件为空")
    return audio_response.content
