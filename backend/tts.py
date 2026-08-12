import asyncio
import hashlib
import re
import tempfile
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
    """普通朗读接口参数，保留旧版前端字段。"""

    text: str
    voice: Optional[str] = "child"
    style: Optional[str] = "poem"
    rate: Optional[str] = None
    pitch: Optional[str] = None


VOICE_MAP = {
    "poem": "zh-CN-XiaoxiaoNeural",
    "child": "zh-CN-XiaoxiaoNeural",
    "female": "zh-CN-XiaoxiaoNeural",
    "default": "zh-CN-XiaoxiaoNeural",
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "male": "zh-CN-YunxiNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "zh-CN-XiaoxiaoNeural": "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural": "zh-CN-YunxiNeural",
    "zh-CN-XiaoyiNeural": "zh-CN-XiaoyiNeural",
    "zh-CN-YunjianNeural": "zh-CN-YunjianNeural",
}
POEM_VOICES = {"poem", "child", "female", "xiaoxiao", "default"}
RATE_PATTERN = re.compile(r"^[+-]?\d{1,3}%$")
PITCH_PATTERN = re.compile(r"^[+-]?\d{1,3}Hz$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def map_voice_to_edge_voice(voice: str) -> str:
    return VOICE_MAP.get(voice or "child", VOICE_MAP["child"])


def _validated_option(value: Optional[str], default: str, pattern: re.Pattern) -> str:
    if value is None or not str(value).strip():
        return default
    cleaned = str(value).strip()
    return cleaned if pattern.fullmatch(cleaned) else default


def get_poem_rate(rate: Optional[str] = None) -> str:
    return _validated_option(rate, "-18%", RATE_PATTERN)


def get_poem_pitch(pitch: Optional[str] = None) -> str:
    return _validated_option(pitch, "-2Hz", PITCH_PATTERN)


def prepare_poem_text(text: str) -> str:
    """统一标点，并在诗句之间加入适合儿童跟读的自然停顿。"""
    value = normalize_text(text)
    if not value:
        return ""

    punctuation = str.maketrans({",": "，", ".": "。", "?": "？", "!": "！", ";": "；", ":": "："})
    value = value.translate(punctuation)
    parts = [part.strip("，。！？；： ") for part in re.split(r"[。！？；]", value)]
    parts = [part for part in parts if part]
    if not parts:
        return value
    return "。……".join(parts) + "。"


def build_audio_filename(text: str, voice: str, style: str, rate: str, pitch: str) -> str:
    raw = f"{map_voice_to_edge_voice(voice)}:{style}:{rate}:{pitch}:{normalize_text(text)}"
    return f"tts_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]}.mp3"


def get_audio_url(filename: str) -> str:
    return f"/static/audio/{filename}"


async def call_edge_tts_async(
    text: str,
    voice: str = "child",
    rate: str = "-18%",
    pitch: str = "-2Hz",
) -> bytes:
    communicate = edge_tts.Communicate(
        text=text,
        voice=map_voice_to_edge_voice(voice),
        rate=rate,
        pitch=pitch,
    )
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    audio_bytes = b"".join(chunks)
    if not audio_bytes:
        raise RuntimeError("edge-tts 未返回音频数据")
    return audio_bytes


def call_edge_tts(text: str, voice: str = "child", rate: str = "-18%", pitch: str = "-2Hz") -> bytes:
    return asyncio.run(call_edge_tts_async(text, voice, rate, pitch))


def save_audio_file(audio_bytes: bytes, filename: str) -> str:
    """原子写入缓存，避免并发请求读到不完整的 mp3。"""
    target = AUDIO_DIR / filename
    with tempfile.NamedTemporaryFile(dir=AUDIO_DIR, suffix=".tmp", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(audio_bytes)
    temp_path.replace(target)
    return get_audio_url(filename)


def _failure(message: str, **extra):
    return {
        "success": False,
        "message": message,
        "provider": "edge-tts",
        "cache_hit": False,
        "audio_url": "",
        **extra,
    }


@router.post("/tts")
def generate_tts(request: TTSRequest):
    raw_text = str(request.text or "").strip()
    if not raw_text:
        return _failure("text 不能为空")

    voice = request.voice or "child"
    style = request.style or "poem"
    rate = get_poem_rate(request.rate)
    pitch = get_poem_pitch(request.pitch)
    tts_text = prepare_poem_text(raw_text) if style == "poem" or voice in POEM_VOICES else raw_text
    if not tts_text:
        return _failure("处理后的朗读文本为空")

    filename = build_audio_filename(tts_text, voice, style, rate, pitch)
    file_path = AUDIO_DIR / filename
    audio_url = get_audio_url(filename)
    edge_voice = map_voice_to_edge_voice(voice)
    common = {"voice": edge_voice, "style": style, "rate": rate, "pitch": pitch}

    if file_path.is_file() and file_path.stat().st_size > 0:
        return {
            "success": True,
            "message": "语音已存在，直接复用",
            "provider": "edge-tts",
            "cache_hit": True,
            "audio_url": audio_url,
            **common,
        }

    try:
        audio_bytes = call_edge_tts(tts_text, voice, rate, pitch)
        return {
            "success": True,
            "message": "古诗朗读语音生成成功",
            "provider": "edge-tts",
            "cache_hit": False,
            "audio_url": save_audio_file(audio_bytes, filename),
            **common,
        }
    except Exception as exc:
        return _failure("TTS 语音生成失败", error=str(exc), **common)
