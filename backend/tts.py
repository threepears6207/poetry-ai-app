import base64
import os
import time
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
AUDIO_DIR = STATIC_DIR / "audio"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class TTSRequest(BaseModel):
    """
    前端调用 TTS 时传入的数据
    """
    text: str
    voice: Optional[str] = "child"


def save_audio_file(audio_bytes: bytes) -> str:
    """
    保存音频文件，并返回前端可访问的相对路径
    """
    filename = f"tts_{int(time.time() * 1000)}.mp3"
    file_path = AUDIO_DIR / filename

    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    return f"/static/audio/{filename}"


def call_lanxin_tts(text: str, voice: str = "child") -> bytes:
    """
    调用蓝心 TTS 服务。

    当前函数是蓝心 TTS 接入位置。
    需要根据比赛平台提供的接口文档填写真实 URL、鉴权参数和请求格式。
    不要把 API Key 写死在代码中，应通过环境变量读取。
    """

    tts_url = os.getenv("LANXIN_TTS_URL")
    app_id = os.getenv("LANXIN_APP_ID")
    api_key = os.getenv("LANXIN_API_KEY")
    api_secret = os.getenv("LANXIN_API_SECRET")

    if not tts_url or not api_key:
        raise RuntimeError("蓝心 TTS 配置未完成，请检查 LANXIN_TTS_URL 和 LANXIN_API_KEY")

    # 下面 headers 和 payload 需要按照比赛官方提供的蓝心 TTS 文档调整。
    # 如果文档要求 app_id、timestamp、signature，也要在这里补。
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "text": text,
        "voice": voice,
        "format": "mp3"
    }

    response = requests.post(
        tts_url,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    # 常见 TTS 返回形式：
    # 1. 返回 base64 音频字段，例如 audio_base64；
    # 2. 返回音频 URL；
    # 3. 直接返回二进制音频。
    # 这里先按 base64 返回写，后续根据真实文档调整字段名。
    audio_base64 = result.get("audio_base64") or result.get("audio")

    if not audio_base64:
        raise RuntimeError("蓝心 TTS 返回中未找到音频字段")

    return base64.b64decode(audio_base64)


@router.post("/tts")
def generate_tts(request: TTSRequest):
    """
    文字转语音接口。

    请求示例：
    {
      "text": "床前明月光，疑是地上霜。",
      "voice": "child"
    }
    """

    text = request.text.strip()

    if not text:
        return {
            "success": False,
            "message": "text 不能为空"
        }

    try:
        audio_bytes = call_lanxin_tts(text, request.voice)
        audio_url = save_audio_file(audio_bytes)

        return {
            "success": True,
            "message": "语音生成成功",
            "audio_url": audio_url
        }

    except Exception as e:
        return {
            "success": False,
            "message": "TTS 语音生成失败",
            "error": str(e)
        }