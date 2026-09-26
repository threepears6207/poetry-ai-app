import hashlib
import json
import os
import re
import threading
from pathlib import Path

from dashscope_tts import DEFAULT_TTS_MODEL, synthesize_dashscope_tts


BASE_DIR = Path(__file__).parent
CHAT_AUDIO_DIR = BASE_DIR / "static" / "audio" / "chat"
VOICE_PROFILE_PATH = BASE_DIR / "static" / "poet_voice_profiles.json"
CHAT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_cache_lock = threading.RLock()

MALE_CHILD_VOICES = ("Mochi", "Pip")
MALE_YOUNG_VOICES = ("Moon", "Kai")
MALE_MATURE_VOICES = ("Kai", "Neil", "Moon")
MALE_ELDER_VOICES = ("Eldric Sage", "Arthur")
MALE_HEROIC_VOICES = ("Vincent", "Moon")
FEMALE_GENTLE_VOICES = ("Maia", "Seren", "Mia")
FEMALE_LIVELY_VOICES = ("Momo", "Vivian", "Stella")
FEMALE_CHILD_VOICES = ("Bella", "Bunny")

ALLOWED_VOICES = set(
    MALE_CHILD_VOICES
    + MALE_YOUNG_VOICES
    + MALE_MATURE_VOICES
    + MALE_ELDER_VOICES
    + MALE_HEROIC_VOICES
    + FEMALE_GENTLE_VOICES
    + FEMALE_LIVELY_VOICES
    + FEMALE_CHILD_VOICES
)

DEFAULT_VOICE_PROFILE = {
    "dynasty": "",
    "voice": "Kai",
    "instructions": (
        "使用温和自然、适合儿童聆听的成年男性声音，语速适中，吐字清楚，"
        "语气亲切但不过度表演。"
    ),
    "character": "温和、自然、亲切",
    "source": "default",
}


def _load_profiles() -> dict:
    if not VOICE_PROFILE_PATH.is_file():
        return {}
    try:
        data = json.loads(VOICE_PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_profiles(profiles: dict) -> None:
    VOICE_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = VOICE_PROFILE_PATH.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, VOICE_PROFILE_PATH)


def _stable_choice(values: tuple, poet_name: str, dynasty: str) -> str:
    digest = hashlib.sha256(f"{dynasty}:{poet_name}".encode("utf-8")).digest()
    return values[int.from_bytes(digest[:4], "big") % len(values)]


def _contains_any(text: str, keywords: tuple) -> bool:
    return any(keyword in text for keyword in keywords)


def _build_dynamic_profile(poet_name: str, dynasty: str, style: str) -> dict:
    """把未知诗人的既有性格描述归入有限且经过校验的千问音色。"""
    description = str(style or "").strip()
    is_female = _contains_any(description, ("女诗人", "女词人", "女性", "女子", "才女"))
    is_child = _contains_any(
        description,
        ("男童", "女童", "孩童", "孩子气", "童声", "七岁", "少年气", "少女"),
    )
    is_elder = _contains_any(
        description,
        ("老年", "年长", "白发", "苍老", "老爷爷", "晚年", "高龄"),
    )
    is_heroic = _contains_any(
        description,
        ("豪迈", "奔放", "壮阔", "激昂", "有力量", "气势", "开阔", "坚定"),
    )
    is_lively = _contains_any(
        description,
        ("活泼", "俏皮", "风趣", "幽默", "开朗", "率真", "轻快"),
    )
    is_scholarly = _contains_any(
        description,
        ("严谨", "认真", "睿智", "教导", "清楚", "简练", "实在", "学问"),
    )

    if is_female and is_child:
        voices = FEMALE_CHILD_VOICES
        character = "童真、明亮、亲切"
        performance = "使用明亮自然的女童声音，语气充满好奇，节奏轻快但吐字清楚。"
    elif is_female and is_lively:
        voices = FEMALE_LIVELY_VOICES
        character = "开朗、灵动、亲切"
        performance = "使用自然灵动的女性声音，语气开朗带笑，节奏轻快但不要夸张。"
    elif is_female:
        voices = FEMALE_GENTLE_VOICES
        character = "温柔、细腻、含蓄"
        performance = "使用成熟温柔的女性声音，语速舒缓，表达细腻含蓄，停顿自然。"
    elif is_child:
        voices = MALE_CHILD_VOICES
        character = "童真、聪慧、活泼"
        performance = "使用聪明活泼的男童声音，语气自然好奇，节奏轻快但不要尖叫。"
    elif is_elder:
        voices = MALE_ELDER_VOICES
        character = "年长、温厚、沉稳"
        performance = "使用年长温厚的男性声音，语速稍慢，语气慈祥自然，像长辈讲故事。"
    elif is_heroic:
        voices = MALE_HEROIC_VOICES
        character = "豪迈、开阔、坚定"
        performance = "使用开阔有力量的成年男性声音，语气坚定舒展，保持亲切，不要喊叫。"
    elif is_scholarly:
        voices = ("Neil", "Kai")
        character = "睿智、清楚、耐心"
        performance = "使用睿智清楚的成年男性声音，吐字准确，语速适中，像亲切老师耐心解释。"
    elif is_lively:
        voices = MALE_YOUNG_VOICES
        character = "明亮、自然、风趣"
        performance = "使用明亮自然的成年男性声音，语气轻松带笑，节奏活泼但不过度表演。"
    else:
        voices = MALE_MATURE_VOICES
        character = "温和、自然、亲切"
        performance = "使用温和自然的成年男性声音，语速适中，吐字清楚，语气亲切。"

    return {
        "dynasty": str(dynasty or "").strip(),
        "voice": _stable_choice(voices, poet_name, dynasty),
        "instructions": performance + "面对3到7岁小朋友说话，表达要温暖、清楚。",
        "character": character,
        "source": "automatic",
    }


def get_poet_voice_profile(poet_name: str, dynasty: str = "", style: str = "") -> dict:
    """读取固定档案；未知诗人首次自动归类后持久化，之后始终复用。"""
    name = str(poet_name or "古代诗人").strip() or "古代诗人"
    clean_dynasty = str(dynasty or "").strip()
    with _cache_lock:
        profiles = _load_profiles()
        existing = profiles.get(name)
        if isinstance(existing, dict) and existing.get("voice") in ALLOWED_VOICES:
            return dict(existing)

        if name == "古代诗人" and not style:
            return dict(DEFAULT_VOICE_PROFILE)

        profile = _build_dynamic_profile(name, clean_dynasty, style)
        profiles[name] = profile
        _save_profiles(profiles)
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


def _cache_key(poet_name: str, profile: dict, text: str) -> str:
    raw = ":".join(
        [
            "qwen3-v1",
            DEFAULT_TTS_MODEL,
            poet_name,
            profile["voice"],
            profile["instructions"],
            text,
        ]
    )
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


def synthesize_poet_speech(
    poet_name: str,
    text: str,
    dynasty: str = "",
    style: str = "",
) -> dict:
    """使用千问3-TTS按持久化诗人声音档案生成对话语音。"""
    name = str(poet_name or "古代诗人").strip() or "古代诗人"
    speech_text = prepare_dialogue_text(text)
    if not speech_text:
        raise ValueError("诗人回复为空，无法生成语音")

    profile = get_poet_voice_profile(name, dynasty=dynasty, style=style)
    cache_key = _cache_key(name, profile, speech_text)
    file_path = CHAT_AUDIO_DIR / f"poet_{cache_key}.wav"
    cache_hit = file_path.exists() and file_path.stat().st_size > 0

    model = os.getenv("DASHSCOPE_TTS_MODEL", DEFAULT_TTS_MODEL).strip() or DEFAULT_TTS_MODEL
    result = {
        "url": _audio_url(file_path),
        "format": "wav",
        "provider": "dashscope-qwen3-tts",
        "model": model,
        "voice_id": profile["voice"],
        "engineid": "qwen3-tts-instruct-flash",
        "character": profile["character"],
        "profile_source": profile["source"],
        "fallback_used": False,
    }
    if cache_hit:
        return {**result, "cache_hit": True}

    audio_bytes = synthesize_dashscope_tts(
        text=speech_text,
        voice=profile["voice"],
        instructions=profile["instructions"],
    )
    _save_if_missing(file_path, audio_bytes)
    return {**result, "cache_hit": False}
