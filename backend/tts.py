import asyncio
import hashlib
import re
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


def normalize_text(text: str) -> str:
    """
    规范化文本，避免同一首诗因为空格、换行不同而重复生成多个音频。
    """
    value = str(text or "").strip()
    value = re.sub(r"\s+", "", value)
    return value


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
        "yunjian": "zh-CN-YunjianNeural",

        # 兼容前端直接传 edge-tts 音色名的情况
        "zh-CN-XiaoxiaoNeural": "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural": "zh-CN-YunxiNeural",
        "zh-CN-XiaoyiNeural": "zh-CN-XiaoyiNeural",
        "zh-CN-YunjianNeural": "zh-CN-YunjianNeural"
    }

    return voice_map.get(voice or "default", "zh-CN-XiaoxiaoNeural")


def build_audio_filename(text: str, voice: str) -> str:
    """
    根据朗读文本和音色生成固定文件名。

    同样的 text + voice 会得到同一个文件名，
    这样就可以判断是否已经生成过。
    """
    normalized_text = normalize_text(text)
    edge_voice = map_voice_to_edge_voice(voice)

    raw = f"{edge_voice}:{normalized_text}"
    file_hash = hashlib.md5(raw.encode("utf-8")).hexdigest()

    return f"tts_{file_hash}.mp3"


def get_audio_url(filename: str) -> str:
    """
    返回前端可访问的音频相对路径。
    """
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


def save_audio_file(audio_bytes: bytes, filename: str) -> str:
    """
    保存 mp3 音频文件，并返回前端可访问的相对路径。
    """
    file_path = AUDIO_DIR / filename

    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    return get_audio_url(filename)


@router.post("/tts")
def generate_tts(request: TTSRequest):
    """
    文字转语音接口。

    请求示例：
    {
      "text": "床前明月光，疑是地上霜。",
      "voice": "child"
    }

    缓存逻辑：
    1. 同样的 text + voice 会生成同一个 mp3 文件名；
    2. 如果文件已经存在，直接返回已有 audio_url；
    3. 如果文件不存在，才调用 edge-tts 生成新音频。
    """
    text = normalize_text(request.text)
    voice = request.voice or "child"

    if not text:
        return {
            "success": False,
            "message": "text 不能为空",
            "provider": "edge-tts",
            "cache_hit": False,
            "audio_url": ""
        }

    filename = build_audio_filename(text, voice)
    file_path = AUDIO_DIR / filename
    audio_url = get_audio_url(filename)
    edge_voice = map_voice_to_edge_voice(voice)

    # 如果同样文本和同样音色已经生成过，直接复用
    if file_path.exists() and file_path.stat().st_size > 0:
        return {
            "success": True,
            "message": "语音已存在，直接复用",
            "provider": "edge-tts",
            "cache_hit": True,
            "voice": edge_voice,
            "audio_url": audio_url
        }

    try:
        audio_bytes = call_edge_tts(text, voice)
        audio_url = save_audio_file(audio_bytes, filename)

        return {
            "success": True,
            "message": "语音生成成功",
            "provider": "edge-tts",
            "cache_hit": False,
            "voice": edge_voice,
            "audio_url": audio_url
        }

    except Exception as e:
        return {
            "success": False,
            "message": "TTS 语音生成失败",
            "provider": "edge-tts",
            "cache_hit": False,
            "voice": edge_voice,
            "error": str(e),
            "audio_url": ""
        }