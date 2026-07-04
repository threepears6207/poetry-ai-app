import hashlib
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import requests
from fastapi import APIRouter
from pydantic import AliasChoices, BaseModel, Field

from generate import plan_poem_sequence


router = APIRouter()

VIVO_VIDEO_SUBMIT_URL = "https://api-ai.vivo.com.cn/api/v1/submit_task"
VIVO_VIDEO_QUERY_URL = "https://api-ai.vivo.com.cn/api/v1/query_task"
SUPPORTED_MODELS = {
    "Doubao-Seedance-1.0-pro",
    "Doubao-Seedance-2.0",
    "Doubao-Seedance-2.0-fast",
}

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "static" / "videos" / "poems"
CACHE_FILE = BASE_DIR / "static" / "video_tasks_cache.json"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

_cache_lock = threading.Lock()


VIDEO_STYLE = (
    "中国传统儿童绘本动画风格，水彩笔触，色彩柔和温润，"
    "人物造型圆润可爱，线条细腻流畅，背景层次丰富，"
    "整体氛围温暖治愈，具有国风古典美感，适合3至7岁儿童观看"
)

VIDEO_ALLOWED = (
    "允许云、水面、树叶、衣袖、窗帘和月光进行轻柔自然的运动；"
    "允许人物眨眼、呼吸、缓慢抬头、低头、转身或行走；"
    "允许运镜缓慢推进、拉远、平移或自然转场；"
    "所有动作幅度小、节奏舒缓，镜头之间具有明确的叙事承接"
)

VIDEO_FORBIDDEN = (
    "禁止出现任何文字、字幕、诗句、标题、标志、水印和边框；"
    "禁止出现现代建筑、现代服装、现代家具、汽车、电线和电子产品；"
    "禁止新增诗中不存在的主要人物、动物或装饰性物体；"
    "禁止恐怖、阴森、暴力、打斗、追逐、哭喊、夸张表情和危险动作；"
    "禁止人物脸型、年龄、性别、发型和服装颜色在镜头间变化；"
    "禁止多手、多脚、肢体变形、五官漂移、人物凭空出现或消失；"
    "禁止镜头快速闪烁、剧烈抖动、突然变焦、过快剪辑和画面跳变；"
    "禁止室内外元素空间错乱，禁止无关物体闯入画面"
)

FORBIDDEN_SCENE_TERMS = (
    "文字", "字幕", "诗句", "标题", "标志", "水印", "边框",
    "问号", "感叹号", "气泡", "对话框", "泪", "哭",
    "现代建筑", "现代服装", "现代家具", "汽车", "电线", "电子产品",
)


class VideoGenerateRequest(BaseModel):
    poem_id: str = ""
    poem_title: str = Field(
        default="",
        validation_alias=AliasChoices("poem_title", "title"),
    )
    poem_content: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("poem_content", "content"),
    )
    poet_name: str = ""
    dynasty: str = ""
    tags: List[str] = Field(default_factory=list)
    model: str = "Doubao-Seedance-2.0-fast"
    duration: int = 5
    ratio: str = "16:9"
    force_regenerate: bool = False
    dry_run: bool = False


def _now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _cache_key(poem_id: str, poem_title: str) -> str:
    if poem_id.strip():
        value = poem_id.strip()
    else:
        value = hashlib.md5(poem_title.strip().encode("utf-8")).hexdigest()
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value) or "untitled"


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {"poems": {}, "tasks": {}}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            cache = json.load(file)
        cache.setdefault("poems", {})
        cache.setdefault("tasks", {})
        return cache
    except Exception:
        return {"poems": {}, "tasks": {}}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _cache_lock:
        temp_file = CACHE_FILE.with_suffix(".json.tmp")
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(cache, file, ensure_ascii=False, indent=2)
        os.replace(temp_file, CACHE_FILE)


def _request_params() -> dict:
    return {
        "request_id": str(uuid.uuid4()),
        "system_time": int(time.time()),
        "module": "aigc",
    }


def _request_headers() -> dict:
    app_key = os.getenv("VIVO_APP_KEY", "").strip()
    if not app_key:
        raise RuntimeError("缺少 VIVO_APP_KEY，无法调用视频生成接口")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app_key}",
    }


def _validate_request(request: VideoGenerateRequest) -> str:
    if not request.poem_title.strip():
        return "poem_title 不能为空"
    if not request.poem_content:
        return "poem_content 不能为空"
    if request.model not in SUPPORTED_MODELS:
        return f"不支持的视频模型：{request.model}"
    if request.duration not in {5, 10}:
        return "当前实验仅允许 duration=5 或 duration=10"
    if request.ratio not in {"16:9", "9:16", "1:1", "adaptive"}:
        return "ratio 仅支持 16:9、9:16、1:1 或 adaptive"
    return ""


def _sanitize_scene_text(scene: str, fallback: str) -> str:
    """移除规划模型偶尔加入的文字符号、哭泣或装饰气泡等冲突描述。"""
    pieces = re.split(r"(?<=[。！？；])", str(scene).strip())
    safe_pieces = [
        piece.strip()
        for piece in pieces
        if piece.strip() and not any(term in piece for term in FORBIDDEN_SCENE_TERMS)
    ]
    safe_scene = "".join(safe_pieces).strip().rstrip("。")
    return safe_scene or f"围绕“{fallback}”的古典诗意场景，人物动作自然克制"


def build_poem_video_prompt(request: VideoGenerateRequest) -> tuple[str, dict]:
    """把整首诗规划为一个独立的多镜头文生视频 Prompt，不生成图片。"""
    plan = plan_poem_sequence(
        poem_title=request.poem_title,
        poem_content=request.poem_content,
        poet_name=request.poet_name,
        dynasty=request.dynasty,
        tags=request.tags,
    )

    character_desc = plan.get("character_desc", "")
    recurring_elements = plan.get("recurring_elements", "")
    outdoor_elements = plan.get("outdoor_elements", "")
    frames = plan.get("frames", [])

    shot_lines = []
    for index, poem_line in enumerate(request.poem_content):
        frame = frames[index] if index < len(frames) else {}
        scene = _sanitize_scene_text(frame.get("scene", poem_line), poem_line)
        shot_type = frame.get("shot_type", "中景")
        shot_lines.append(
            f"镜头{index + 1}（对应诗句“{poem_line}”）：采用{shot_type}，{scene}。"
        )

    identity_rule = ""
    if character_desc:
        identity_rule = (
            f"全片主角形象固定为：{character_desc}。"
            "发型、年龄、性别、脸型、服装样式和颜色从头到尾完全一致。"
        )

    space_rule = ""
    if recurring_elements:
        space_rule += f"室内固定元素必须保持一致：{recurring_elements}。"
    if outdoor_elements:
        space_rule += f"户外固定自然元素必须保持一致：{outdoor_elements}。"

    lines_text = "\n".join(shot_lines)
    prompt = (
        f"为{request.dynasty}代{request.poet_name}的古诗《{request.poem_title}》"
        f"制作一段完整、连续的儿童诗意动画。\n"
        f"画面风格：{VIDEO_STYLE}。\n"
        f"一致性要求：{identity_rule}{space_rule}同一地点、人物和主要物体在相邻镜头中自然延续。\n"
        f"多镜头叙事顺序：\n{lines_text}\n"
        f"允许内容：{VIDEO_ALLOWED}。\n"
        f"严格禁止：{VIDEO_FORBIDDEN}。\n"
        "整段视频必须完整表达全诗意境，镜头按诗句顺序出现，转场自然，"
        "不得打乱诗句顺序，不在画面中显示诗句。"
        f" --ratio {request.ratio} --dur {request.duration}"
    )
    return prompt, plan


def _public_result(record: dict, from_cache: bool = False) -> dict:
    return {
        "success": record.get("status") not in {"failed", "download_failed"},
        "from_cache": from_cache,
        "task_id": record.get("task_id", ""),
        "poem_id": record.get("poem_id", ""),
        "poem_title": record.get("poem_title", ""),
        "model": record.get("model", ""),
        "duration": record.get("duration", 0),
        "ratio": record.get("ratio", ""),
        "status": record.get("status", ""),
        "video_url": record.get("video_url", ""),
        "error": record.get("error", ""),
        "created_at": record.get("created_at", ""),
        "updated_at": record.get("updated_at", ""),
    }


def _download_video(source_url: str, cache_key: str, task_id: str) -> str:
    poem_dir = VIDEO_DIR / cache_key
    poem_dir.mkdir(parents=True, exist_ok=True)
    file_path = poem_dir / f"{task_id}.mp4"
    temp_path = file_path.with_suffix(".mp4.tmp")

    with requests.get(source_url, stream=True, timeout=(15, 180)) as response:
        response.raise_for_status()
        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
    os.replace(temp_path, file_path)
    return f"/static/videos/poems/{cache_key}/{file_path.name}"


@router.post("/generate/video")
def submit_poem_video(request: VideoGenerateRequest):
    """提交整首诗的文生视频任务；dry_run=true 时只返回 Prompt。"""
    validation_error = _validate_request(request)
    if validation_error:
        return {"success": False, "error": validation_error}

    cache_key = _cache_key(request.poem_id, request.poem_title)
    cache = _load_cache()
    cached_task_id = cache["poems"].get(cache_key, "")
    cached_record = cache["tasks"].get(cached_task_id)
    reusable_statuses = {"submitted", "queued", "running", "processing", "succeeded"}
    if (
        cached_record
        and cached_record.get("status") in reusable_statuses
        and not request.force_regenerate
        and not request.dry_run
    ):
        return _public_result(cached_record, from_cache=True)

    try:
        prompt, plan = build_poem_video_prompt(request)
    except Exception as error:
        return {"success": False, "error": f"视频分镜规划失败：{error}"}

    if request.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "poem_id": request.poem_id,
            "poem_title": request.poem_title,
            "model": request.model,
            "duration": request.duration,
            "ratio": request.ratio,
            "prompt": prompt,
            "plan": plan,
        }

    try:
        response = requests.post(
            VIVO_VIDEO_SUBMIT_URL,
            params=_request_params(),
            headers=_request_headers(),
            json={
                "model": request.model,
                "content": [{"type": "text", "text": prompt}],
            },
            timeout=60,
        )
        result = response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "error": "视频任务提交超时，请稍后重试"}
    except Exception as error:
        return {"success": False, "error": f"视频任务提交异常：{error}"}

    if result.get("code") != 0:
        return {
            "success": False,
            "error": result.get("message", "视频任务提交失败"),
            "code": result.get("code"),
            "trace_id": result.get("trace_id", ""),
            "data": result.get("data"),
        }

    task_id = result.get("data", {}).get("id", "")
    if not task_id:
        return {"success": False, "error": "视频接口未返回 task_id", "raw": result}

    record = {
        "task_id": task_id,
        "cache_key": cache_key,
        "poem_id": request.poem_id,
        "poem_title": request.poem_title,
        "model": request.model,
        "duration": request.duration,
        "ratio": request.ratio,
        "status": "submitted",
        "video_url": "",
        "error": "",
        "prompt": prompt,
        "created_at": _now_text(),
        "updated_at": _now_text(),
    }
    cache["tasks"][task_id] = record
    cache["poems"][cache_key] = task_id
    _save_cache(cache)
    return _public_result(record)


@router.get("/generate/video/{task_id}")
def query_poem_video(task_id: str):
    """查询 vivo 视频任务；成功后立即下载 MP4 到本地静态目录。"""
    cache = _load_cache()
    record = cache["tasks"].get(task_id)
    if record and record.get("status") == "succeeded" and record.get("video_url"):
        return _public_result(record, from_cache=True)

    try:
        response = requests.get(
            VIVO_VIDEO_QUERY_URL,
            params={"task_id": task_id, **_request_params()},
            headers=_request_headers(),
            timeout=60,
        )
        result = response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "task_id": task_id, "error": "视频任务查询超时"}
    except Exception as error:
        return {"success": False, "task_id": task_id, "error": f"视频任务查询异常：{error}"}

    if result.get("code") != 0:
        return {
            "success": False,
            "task_id": task_id,
            "error": result.get("message", "视频任务查询失败"),
            "code": result.get("code"),
            "trace_id": result.get("trace_id", ""),
        }

    data = result.get("data", {})
    status = data.get("status", "unknown")
    if record is None:
        record = {
            "task_id": task_id,
            "cache_key": f"task_{task_id}",
            "poem_id": "",
            "poem_title": "",
            "model": data.get("model", ""),
            "duration": data.get("duration", 0),
            "ratio": data.get("ratio", ""),
            "created_at": _now_text(),
            "video_url": "",
            "error": "",
        }

    record["status"] = status
    record["updated_at"] = _now_text()
    record["error"] = data.get("error") or ""
    record["resolution"] = data.get("resolution", "")

    if status == "succeeded":
        source_url = data.get("content", {}).get("video_url", "")
        if not source_url:
            record["status"] = "download_failed"
            record["error"] = "视频任务成功，但结果中没有 video_url"
        else:
            try:
                record["video_url"] = _download_video(
                    source_url=source_url,
                    cache_key=record["cache_key"],
                    task_id=task_id,
                )
            except Exception as error:
                record["status"] = "download_failed"
                record["error"] = f"视频生成成功，但下载到本地失败：{error}"

    cache["tasks"][task_id] = record
    if record.get("cache_key"):
        cache["poems"][record["cache_key"]] = task_id
    _save_cache(cache)
    return _public_result(record)
