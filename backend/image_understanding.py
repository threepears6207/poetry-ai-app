import base64
import binascii
import json
import os
import re
from typing import Any

import requests
from fastapi import APIRouter
from pydantic import BaseModel

from candidate_search import ImageAnalysisInput


router = APIRouter()

DEFAULT_VISION_MODEL = "qwen3-vl-plus-2025-12-19"
DEFAULT_VISION_API_URL = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
)
DEFAULT_MAX_PIXELS = 2_359_296
MAX_IMAGE_BYTES = 10 * 1024 * 1024

IMAGE_ANALYSIS_PROMPT = """只输出一个 JSON 对象，不要输出解释、Markdown、第二个 JSON 或其他文字。

先判断图片中是否有清晰完整的古诗文字。只要能看出古诗题目、作者或朝代，以及两句及以上诗文，就必须按 poem_text 输出；即使汉字上方带拼音、图片有插画背景、下方有“译文”区域或诗句分行排版，也不能输出 scene。

古诗必须输出以下 JSON 结构：
{"content_type":"poem_text","poem":{"title":"诗名","author":"作者","dynasty":"唐","content":["原诗第一句","原诗第二句"],"translation":"按原诗顺序完整解释全诗含义的一段儿童白话译文"},"confidence":0.9}

title、author、content 必须来自图片中的古诗；忽略拼音、题注、编号、脚注和“译文”区域。图片未写 dynasty 但能依据诗名和作者确认时，自行补全标准朝代。dynasty 只能写“唐、宋、元、明、清”等，不要写“唐朝、清朝”。content 必须是数组，每项只放原诗的一句；按原诗的逗号、句号、问号、感叹号或分号分句，不带句末标点，不得混入译文、白话说明、题目、作者、朝代或拼音。translation 必须是字符串，按原诗句子顺序，用一段儿童能懂的白话完整解释全诗含义，不得照抄原文或添加解释前缀。

只有图片中没有古诗题目、作者或至少两句古诗正文时，才按 scene 输出：
{"content_type":"scene","objects":["山峰","海面"],"scene_tags":["山水","自然"],"season":"夏天","mood":"宁静","confidence":0.9}

objects 最多六项，每项必须是两个字及以上的具体可见事物；scene_tags 最多六项，概括可用于匹配古诗的场景主题。无法判断 season 或 mood 时填写空字符串。confidence 必须是 0 到 1 的数字。

不要输出 recognized_text、poem_draft、tags、theme_tags、knowledge_tags、age_level、age_range、difficulty 或 recommend_reason。所有 JSON 括号和引号必须闭合。"""


class ImageUnderstandingRequest(BaseModel):
    image_base64: str


class ImageUnderstandingError(RuntimeError):
    pass


def _vision_model() -> str:
    return os.getenv("QWEN_VISION_MODEL", DEFAULT_VISION_MODEL).strip() or DEFAULT_VISION_MODEL


def _vision_api_url() -> str:
    return (
        os.getenv("DASHSCOPE_VISION_API_URL", DEFAULT_VISION_API_URL).strip()
        or DEFAULT_VISION_API_URL
    )


def _vision_max_pixels() -> int:
    raw_value = os.getenv("QWEN_VISION_MAX_PIXELS", str(DEFAULT_MAX_PIXELS)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_MAX_PIXELS
    return min(max(value, 262_144), 8_388_608)


def _prepare_image_data_url(value: str) -> str:
    image_value = str(value or "").strip()
    if not image_value:
        raise ImageUnderstandingError("图片内容为空")

    prefix_match = re.match(r"^data:(image/[a-zA-Z0-9.+-]+);base64,", image_value)
    declared_mime = prefix_match.group(1).lower() if prefix_match else ""
    encoded = image_value.split(",", 1)[1] if prefix_match else image_value
    encoded = re.sub(r"\s+", "", encoded)

    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ImageUnderstandingError("图片 Base64 格式无效") from error

    if not image_bytes:
        raise ImageUnderstandingError("图片内容为空")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageUnderstandingError("图片超过 10MB，请压缩后重试")

    detected_mime = ""
    if image_bytes.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
    elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif image_bytes.startswith((b"GIF87a", b"GIF89a")):
        detected_mime = "image/gif"
    elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        detected_mime = "image/webp"

    mime_type = detected_mime or declared_mime
    if mime_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        raise ImageUnderstandingError("仅支持 JPEG、PNG、GIF 或 WEBP 图片")

    return f"data:{mime_type};base64,{encoded}"


def _extract_message_text(result: dict[str, Any]) -> str:
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise ImageUnderstandingError("千问视觉模型未返回分析结果") from error

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts = [
            str(item.get("text", "")).strip()
            for item in content
            if isinstance(item, dict) and item.get("text")
        ]
        if texts:
            return "\n".join(texts)
    raise ImageUnderstandingError("千问视觉模型返回内容格式异常")


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ImageUnderstandingError("千问视觉模型未返回合法 JSON") from error
    if not isinstance(parsed, dict):
        raise ImageUnderstandingError("千问视觉模型返回的不是 JSON 对象")
    return parsed


def validate_analysis_payload(payload: dict[str, Any]) -> None:
    """Validate Qwen's contract without rewriting its JSON structure."""
    try:
        analysis = ImageAnalysisInput.model_validate(payload)
    except ValueError as error:
        raise ImageUnderstandingError("千问返回的 JSON 不符合约定格式") from error

    if analysis.content_type == "poem_text":
        poem = analysis.poem
        if not poem or len(poem.content) < 2 or not (
            poem.title or poem.author or poem.dynasty
        ):
            raise ImageUnderstandingError("图片中未识别到完整古诗")
        return

    if not analysis.objects and not analysis.scene_tags:
        raise ImageUnderstandingError("图片中未识别到清晰场景")


def analyze_image_with_qwen(
    image_base64: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise ImageUnderstandingError("后端缺少 DASHSCOPE_API_KEY")

    image_data_url = _prepare_image_data_url(image_base64)
    payload = {
        "model": _vision_model(),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                        "max_pixels": _vision_max_pixels(),
                    },
                    {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                ],
            }
        ],
        "response_format": {"type": "json_object"},
        "enable_thinking": False,
        "temperature": 0.1,
        "max_tokens": 1000,
    }
    try:
        response = requests.post(
            _vision_api_url(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
    except requests.RequestException as error:
        raise ImageUnderstandingError(f"千问视觉接口连接失败：{error}") from error

    if response.status_code != 200:
        try:
            error_payload = response.json()
            message = (
                error_payload.get("error", {}).get("message")
                or error_payload.get("message")
                or response.text
            )
        except ValueError:
            message = response.text
        raise ImageUnderstandingError(
            f"千问视觉接口返回 HTTP {response.status_code}：{str(message)[:300]}"
        )

    try:
        result = response.json()
    except ValueError as error:
        raise ImageUnderstandingError("千问视觉接口返回内容不是 JSON") from error

    analysis = _parse_json_object(_extract_message_text(result))
    validate_analysis_payload(analysis)
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    return analysis, usage


@router.post("/image/analyze")
def analyze_poem_image(request: ImageUnderstandingRequest):
    try:
        analysis, usage = analyze_image_with_qwen(request.image_base64)
        return {
            "success": True,
            "provider": "dashscope",
            "model": _vision_model(),
            "analysis": analysis,
            "usage": usage,
        }
    except ImageUnderstandingError as error:
        return {
            "success": False,
            "provider": "dashscope",
            "model": _vision_model(),
            "error_code": "image_analysis_failed",
            "message": str(error),
        }
