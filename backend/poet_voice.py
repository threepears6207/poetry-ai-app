import hashlib
import os
import re
import threading
from pathlib import Path

from tts import call_edge_tts, map_voice_to_edge_voice
from vivo_tts import VivoTTSError, synthesize_vivo_tts


BASE_DIR = Path(__file__).parent
CHAT_AUDIO_DIR = BASE_DIR / "static" / "audio" / "chat"
CHAT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_cache_lock = threading.Lock()


POET_VOICE_PROFILES = {
    "李白": {"engineid": "tts_humanoid_lam", "vcn": "M24", "speed": 58, "volume": 56,
           "edge_voice": "zh-CN-YunjianNeural", "character": "明亮、俊朗、豪爽"},
    "杜甫": {"engineid": "tts_humanoid_lam", "vcn": "M193", "speed": 42, "volume": 50,
           "edge_voice": "zh-CN-YunxiNeural", "character": "沉稳、温厚、认真"},
    "苏轼": {"engineid": "tts_humanoid_lam", "vcn": "M24", "speed": 52, "volume": 54,
           "edge_voice": "zh-CN-YunjianNeural", "character": "豁达、亲切、带笑意"},
    "白居易": {"engineid": "tts_humanoid_lam", "vcn": "M193", "speed": 48, "volume": 51,
            "edge_voice": "zh-CN-YunxiNeural", "character": "平实、清楚、自然"},
    "王维": {"engineid": "short_audio_synthesis_jovi", "vcn": "yunye", "speed": 42, "volume": 48,
           "edge_voice": "zh-CN-YunxiNeural", "character": "安静、轻柔、舒缓"},
    "孟浩然": {"engineid": "short_audio_synthesis_jovi", "vcn": "yunye", "speed": 46, "volume": 50,
            "edge_voice": "zh-CN-YunxiNeural", "character": "温和、自然、松弛"},
    "骆宾王": {"engineid": "short_audio_synthesis_jovi", "vcn": "xiaoming", "speed": 58, "volume": 55,
            "edge_voice": "zh-CN-YunjianNeural", "character": "活泼、率真、有少年气"},
    "王之涣": {"engineid": "tts_humanoid_lam", "vcn": "M24", "speed": 50, "volume": 57,
            "edge_voice": "zh-CN-YunjianNeural", "character": "开阔、坚定、有力量"},
    "李绅": {"engineid": "tts_humanoid_lam", "vcn": "M193", "speed": 40, "volume": 52,
           "edge_voice": "zh-CN-YunxiNeural", "character": "朴实、诚恳、语重心长"},
}

DEFAULT_VOICE_PROFILE = {
    "engineid": "tts_humanoid_lam", "vcn": "M193", "speed": 48, "volume": 52,
    "edge_voice": "zh-CN-YunxiNeural", "character": "温和、自然",
}


def get_poet_voice_profile(poet_name: str) -> dict:
    profile = POET_VOICE_PROFILES.get(str(poet_name or "").strip(), DEFAULT_VOICE_PROFILE)
    return dict(profile)


def prepare_dialogue_text(text: str) -> str:
    """清理不适合朗读的格式，同时保留标点带来的自然停顿。"""
    value = str(text or "").strip()
    value = re.sub(r"```.*?```", "", value, flags=re.DOTALL)
    value = re.sub(r"[*_#>`~]", "", value)
    value = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", value)
    value = re.sub(r"\s+", "", value)
    value = value.replace(",", "，").replace(".", "。")
    value = value.replace("?", "？").replace("!", "！")
    return value[:200]


def _cache_key(poet_name: str, profile: dict, text: str, provider: str) -> str:
    raw = ":".join([
        "v1", provider, poet_name, profile["engineid"], profile["vcn"],
        str(profile["speed"]), str(profile["volume"]), text,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _audio_url(path: Path) -> str:
    return f"/static/audio/chat/{path.name}"


def _save_if_missing(path: Path, audio_bytes: bytes) -> None:
    with _cache_lock:
        if path.exists() and path.stat().st_size > 0:
            return
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_bytes(audio_bytes)
        os.replace(temp_path, path)


def _synthesize_edge_fallback(poet_name: str, text: str, profile: dict) -> dict:
    cache_key = _cache_key(poet_name, profile, text, "edge-tts")
    file_path = CHAT_AUDIO_DIR / f"poet_{cache_key}.mp3"
    cache_hit = file_path.exists() and file_path.stat().st_size > 0

    if not cache_hit:
        rate_percent = max(-25, min(15, profile["speed"] - 50))
        audio_bytes = call_edge_tts(
            text=text,
            voice=profile["edge_voice"],
            rate=f"{rate_percent:+d}%",
            pitch="+0Hz",
        )
        _save_if_missing(file_path, audio_bytes)

    return {
        "url": _audio_url(file_path), "format": "mp3", "provider": "edge-tts",
        "voice_id": map_voice_to_edge_voice(profile["edge_voice"]), "engineid": "edge-tts",
        "speed": profile["speed"], "volume": profile["volume"],
        "character": profile["character"], "cache_hit": cache_hit, "fallback_used": True,
    }


def synthesize_poet_speech(poet_name: str, text: str, allow_fallback: bool = True) -> dict:
    """按诗人的声音档案生成对话语音，蓝心失败时自动降级到 Edge TTS。"""
    name = str(poet_name or "古代诗人").strip() or "古代诗人"
    speech_text = prepare_dialogue_text(text)
    if not speech_text:
        raise ValueError("诗人回复为空，无法生成语音")

    profile = get_poet_voice_profile(name)
    cache_key = _cache_key(name, profile, speech_text, "vivo")
    file_path = CHAT_AUDIO_DIR / f"poet_{cache_key}.wav"
    cache_hit = file_path.exists() and file_path.stat().st_size > 0

    base_result = {
        "url": _audio_url(file_path), "format": "wav", "provider": "vivo",
        "voice_id": profile["vcn"], "engineid": profile["engineid"],
        "speed": profile["speed"], "volume": profile["volume"],
        "character": profile["character"], "fallback_used": False,
    }
    if cache_hit:
        return {**base_result, "cache_hit": True}

    try:
        wav_bytes = synthesize_vivo_tts(
            text=speech_text, engineid=profile["engineid"], vcn=profile["vcn"],
            speed=profile["speed"], volume=profile["volume"],
        )
        _save_if_missing(file_path, wav_bytes)
        return {**base_result, "cache_hit": False}
    except VivoTTSError as vivo_error:
        if not allow_fallback:
            raise
        fallback = _synthesize_edge_fallback(name, speech_text, profile)
        fallback["fallback_reason"] = str(vivo_error)
        return fallback
