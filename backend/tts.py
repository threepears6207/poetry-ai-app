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

    # 兼容原来的 voice 参数
    # 前端原来传 child 也可以继续用
    voice: Optional[str] = "child"

    # 朗读风格，默认古诗朗诵
    style: Optional[str] = "poem"

    # 语速和音调，前端不传时使用古诗朗诵默认值
    rate: Optional[str] = None
    pitch: Optional[str] = None


def normalize_text(text: str) -> str:
    """
    规范化文本，用于生成缓存文件名。
    不直接作为朗读文本，避免把停顿处理清掉。
    """
    value = str(text or "").strip()
    value = re.sub(r"\s+", "", value)
    return value


def map_voice_to_edge_voice(voice: str) -> str:
    """
    将前端传入的 voice 映射为 edge-tts 支持的中文音色。
    """
    voice_map = {
        # 古诗朗诵 / 儿童范读默认使用 Xiaoxiao，声音较柔和
        "poem": "zh-CN-XiaoxiaoNeural",
        "child": "zh-CN-XiaoxiaoNeural",
        "female": "zh-CN-XiaoxiaoNeural",
        "default": "zh-CN-XiaoxiaoNeural",
        "xiaoxiao": "zh-CN-XiaoxiaoNeural",

        # 男声
        "male": "zh-CN-YunxiNeural",
        "yunxi": "zh-CN-YunxiNeural",

        # 其他中文音色
        "xiaoyi": "zh-CN-XiaoyiNeural",
        "yunjian": "zh-CN-YunjianNeural",

        # 兼容前端直接传 edge-tts 音色名的情况
        "zh-CN-XiaoxiaoNeural": "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural": "zh-CN-YunxiNeural",
        "zh-CN-XiaoyiNeural": "zh-CN-XiaoyiNeural",
        "zh-CN-YunjianNeural": "zh-CN-YunjianNeural"
    }

    return voice_map.get(voice or "child", "zh-CN-XiaoxiaoNeural")


def get_poem_rate(rate: Optional[str] = None) -> str:
    """
    古诗朗诵建议语速稍慢。
    edge-tts 支持类似 -10%、-18%、+0% 这种格式。
    """
    return rate or "-18%"


def get_poem_pitch(pitch: Optional[str] = None) -> str:
    """
    音调稍微降低一点，听起来更稳、更像朗诵。
    edge-tts 支持类似 -2Hz、+0Hz、+2Hz 这种格式。
    """
    return pitch or "-2Hz"


def prepare_poem_text(text: str) -> str:
    """
    将古诗文本处理成更适合朗诵的形式。

    处理目标：
    1. 统一标点；
    2. 每句之间增加自然停顿；
    3. 避免整首诗连读太快。
    """
    value = str(text or "").strip()

    if not value:
        return ""

    # 去掉多余空白
    value = re.sub(r"\s+", "", value)

    # 统一英文标点为中文标点
    value = value.replace(",", "，")
    value = value.replace(".", "。")
    value = value.replace("?", "？")
    value = value.replace("!", "！")
    value = value.replace(";", "；")
    value = value.replace(":", "：")

    # 避免重复标点
    value = re.sub(r"。+", "。", value)
    value = re.sub(r"，+", "，", value)
    value = re.sub(r"？+", "？", value)
    value = re.sub(r"！+", "！", value)
    value = re.sub(r"；+", "；", value)

    # 按句末标点切分
    parts = re.split(r"[。！？；]", value)
    parts = [
        part.strip("，。！？； ")
        for part in parts
        if part.strip("，。！？； ")
    ]

    if not parts:
        return value

    # 每句之间加入“。……”形成稍长停顿，更适合古诗范读
    poem_text = "。……".join(parts)

    if not poem_text.endswith("。"):
        poem_text += "。"

    return poem_text


def build_audio_filename(
    text: str,
    voice: str,
    style: str,
    rate: str,
    pitch: str
) -> str:
    """
    根据朗读文本、音色、风格、语速、音调生成固定文件名。

    同样的 text + voice + style + rate + pitch 会得到同一个文件名，
    这样可以复用缓存；不同朗读风格不会误用旧音频。
    """
    normalized_text = normalize_text(text)
    edge_voice = map_voice_to_edge_voice(voice)

    raw = f"{edge_voice}:{style}:{rate}:{pitch}:{normalized_text}"
    file_hash = hashlib.md5(raw.encode("utf-8")).hexdigest()

    return f"tts_{file_hash}.mp3"


def get_audio_url(filename: str) -> str:
    """
    返回前端可访问的音频相对路径。
    """
    return f"/static/audio/{filename}"


async def call_edge_tts_async(
    text: str,
    voice: str = "child",
    rate: str = "-18%",
    pitch: str = "-2Hz"
) -> bytes:
    """
    调用 edge-tts 生成语音，返回 mp3 音频 bytes。
    """
    edge_voice = map_voice_to_edge_voice(voice)

    communicate = edge_tts.Communicate(
        text=text,
        voice=edge_voice,
        rate=rate,
        pitch=pitch
    )

    audio_bytes = b""

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]

    if not audio_bytes:
        raise RuntimeError("edge-tts 未返回音频数据")

    return audio_bytes


def call_edge_tts(
    text: str,
    voice: str = "child",
    rate: str = "-18%",
    pitch: str = "-2Hz"
) -> bytes:
    """
    在同步 FastAPI 接口中调用异步 edge-tts。
    """
    return asyncio.run(call_edge_tts_async(text, voice, rate, pitch))


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
      "text": "床前明月光。疑是地上霜。举头望明月。低头思故乡。",
      "voice": "child"
    }

    古诗朗诵优化：
    1. 默认使用 Xiaoxiao 中文音色；
    2. 默认语速 -18%，比普通朗读更慢；
    3. 默认音调 -2Hz，更稳一点；
    4. 每句之间加入停顿；
    5. 保留缓存功能，同样文本、音色、语速、音调会复用 mp3。
    """
    raw_text = str(request.text or "").strip()

    if not raw_text:
        return {
            "success": False,
            "message": "text 不能为空",
            "provider": "edge-tts",
            "cache_hit": False,
            "audio_url": ""
        }

    voice = request.voice or "child"
    style = request.style or "poem"

    rate = get_poem_rate(request.rate)
    pitch = get_poem_pitch(request.pitch)

    # 默认走古诗朗诵模式
    # 兼容前端原来传 child 的情况，不需要前端改代码
    if style == "poem" or voice in ["poem", "child", "female", "xiaoxiao", "default"]:
        tts_text = prepare_poem_text(raw_text)
    else:
        tts_text = raw_text

    if not tts_text:
        return {
            "success": False,
            "message": "处理后的朗读文本为空",
            "provider": "edge-tts",
            "cache_hit": False,
            "audio_url": ""
        }

    filename = build_audio_filename(
        text=tts_text,
        voice=voice,
        style=style,
        rate=rate,
        pitch=pitch
    )

    file_path = AUDIO_DIR / filename
    audio_url = get_audio_url(filename)
    edge_voice = map_voice_to_edge_voice(voice)

    # 如果同样文本、音色、语速、音调已经生成过，直接复用
    if file_path.exists() and file_path.stat().st_size > 0:
        return {
            "success": True,
            "message": "语音已存在，直接复用",
            "provider": "edge-tts",
            "cache_hit": True,
            "voice": edge_voice,
            "style": style,
            "rate": rate,
            "pitch": pitch,
            "audio_url": audio_url
        }

    try:
        audio_bytes = call_edge_tts(
            text=tts_text,
            voice=voice,
            rate=rate,
            pitch=pitch
        )

        audio_url = save_audio_file(audio_bytes, filename)

        return {
            "success": True,
            "message": "古诗朗诵语音生成成功",
            "provider": "edge-tts",
            "cache_hit": False,
            "voice": edge_voice,
            "style": style,
            "rate": rate,
            "pitch": pitch,
            "audio_url": audio_url
        }

    except Exception as e:
        return {
            "success": False,
            "message": "TTS 语音生成失败",
            "provider": "edge-tts",
            "cache_hit": False,
            "voice": edge_voice,
            "style": style,
            "rate": rate,
            "pitch": pitch,
            "error": str(e),
            "audio_url": ""
        }