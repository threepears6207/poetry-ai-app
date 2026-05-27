import asyncio
import time
from pathlib import Path
from typing import Optional

import edge_tts
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


def map_voice_to_edge_voice(voice: str) -> str:
    """
    将前端传入的 voice 映射为 edge-tts 支持的中文音色。
    """
    voice_map = {
        "child": "zh-CN-XiaoxiaoNeural",
        "female": "zh-CN-XiaoxiaoNeural",
        "male": "zh-CN-YunxiNeural",
        "default": "zh-CN-XiaoxiaoNeural",
        "xiaoxiao": "zh-CN-XiaoxiaoNeural",
        "yunxi": "zh-CN-YunxiNeural",
        "xiaoyi": "zh-CN-XiaoyiNeural",
        "yunjian": "zh-CN-YunjianNeural"
    }

    return voice_map.get(voice or "default", "zh-CN-XiaoxiaoNeural")


def save_audio_file(audio_bytes: bytes) -> str:
    """
    保存 mp3 音频文件，并返回前端可访问的相对路径。
    """
    filename = f"tts_{int(time.time() * 1000)}.mp3"
    file_path = AUDIO_DIR / filename

    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    return f"/static/audio/{filename}"


async def call_edge_tts_async(text: str, voice: str = "child") -> bytes:
    """
    调用 edge-tts 生成语音，返回 mp3 音频 bytes。
    """
    edge_voice = map_voice_to_edge_voice(voice)

    communicate = edge_tts.Communicate(
        text=text,
        voice=edge_voice
    )

    audio_bytes = b""

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]

    if not audio_bytes:
        raise RuntimeError("edge-tts 未返回音频数据")

    return audio_bytes


def call_edge_tts(text: str, voice: str = "child") -> bytes:
    """
    在同步 FastAPI 接口中调用异步 edge-tts。
    """
    return asyncio.run(call_edge_tts_async(text, voice))


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
        audio_bytes = call_edge_tts(text, request.voice)
        audio_url = save_audio_file(audio_bytes)

        return {
            "success": True,
            "message": "语音生成成功",
            "provider": "edge-tts",
            "audio_url": audio_url
        }

    except Exception as e:
        return {
            "success": False,
            "message": "TTS 语音生成失败",
            "provider": "edge-tts",
            "error": str(e)
        }