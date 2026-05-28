import base64
import json
import os
import re
from pathlib import Path
from typing import Optional

import requests
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "poems.json"


class PhotoRequest(BaseModel):
    """
    拍照识诗接口请求体。

    mode:
    - text：前端直接传文字，用于演示和测试
    - image_base64：前端传图片 base64，先 OCR，再图像识别
    """
    image: Optional[str] = ""
    text: Optional[str] = ""
    mode: Optional[str] = "text"


def load_poems():
    """
    读取古诗数据。
    """
    if not DATA_PATH.exists():
        return []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """
    清洗文本，去掉空格和标点，方便匹配。
    """
    if not text:
        return ""

    text = text.strip()
    text = re.sub(r"[\s，。！？；：、“”‘’（）《》〈〉,.!?;:\"'()\[\]{}<>-]", "", text)

    return text


def clean_base64_image(image_base64: str) -> str:
    """
    兼容 data:image/png;base64,xxxx 格式，并校验 base64。
    """
    if not image_base64:
        raise ValueError("image 不能为空")

    image_data = image_base64.strip()

    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    try:
        base64.b64decode(image_data)
    except Exception:
        raise ValueError("image 不是合法的 base64 图片数据")

    return image_data


def get_baidu_access_token(api_key_env: str, secret_key_env: str, service_name: str) -> str:
    """
    根据指定环境变量获取百度 access_token。

    OCR 和图像识别是两个不同应用，所以分别传入不同的 Key。
    """
    api_key = os.getenv(api_key_env)
    secret_key = os.getenv(secret_key_env)

    if not api_key or not secret_key:
        raise RuntimeError(
            f"{service_name} 配置未完成，请配置 {api_key_env} 和 {secret_key_env}"
        )

    token_url = "https://aip.baidubce.com/oauth/2.0/token"

    params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key
    }

    response = requests.get(token_url, params=params, timeout=15)
    response.raise_for_status()

    result = response.json()
    access_token = result.get("access_token")

    if not access_token:
        raise RuntimeError(f"获取 {service_name} access_token 失败：{result}")

    return access_token


def get_baidu_ocr_access_token() -> str:
    """
    获取百度 OCR 应用 access_token。
    """
    return get_baidu_access_token(
        "BAIDU_OCR_API_KEY",
        "BAIDU_OCR_SECRET_KEY",
        "百度 OCR"
    )


def get_baidu_image_access_token() -> str:
    """
    获取百度图像识别应用 access_token。
    """
    return get_baidu_access_token(
        "BAIDU_IMAGE_API_KEY",
        "BAIDU_IMAGE_SECRET_KEY",
        "百度图像识别"
    )


def baidu_ocr_text(image_base64: str) -> str:
    """
    调用百度 OCR 通用文字识别。
    返回识别出的完整文字。
    """
    image_data = clean_base64_image(image_base64)
    access_token = get_baidu_ocr_access_token()

    ocr_url = (
        "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        f"?access_token={access_token}"
    )

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "image": image_data
    }

    response = requests.post(
        ocr_url,
        headers=headers,
        data=data,
        timeout=20
    )
    response.raise_for_status()

    result = response.json()

    if "error_code" in result:
        raise RuntimeError(f"百度 OCR 调用失败：{result}")

    words_result = result.get("words_result", [])

    texts = [
        item.get("words", "")
        for item in words_result
        if item.get("words")
    ]

    return "".join(texts)


def baidu_scene_tags(image_base64: str) -> list[str]:
    """
    调用百度图像识别：通用物体和场景识别。
    返回识别出的标签列表。
    """
    image_data = clean_base64_image(image_base64)
    access_token = get_baidu_image_access_token()

    scene_url = (
        "https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general"
        f"?access_token={access_token}"
    )

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "image": image_data
    }

    response = requests.post(
        scene_url,
        headers=headers,
        data=data,
        timeout=20
    )
    response.raise_for_status()

    result = response.json()

    if "error_code" in result:
        raise RuntimeError(f"百度图像识别调用失败：{result}")

    result_items = result.get("result", [])

    tags = []
    for item in result_items:
        keyword = item.get("keyword")
        root = item.get("root")

        if keyword:
            tags.append(keyword)

        if root:
            tags.append(root)

    return list(dict.fromkeys(tags))


def match_poem_by_text(recognized_text: str):
    """
    根据 OCR 文字匹配古诗。
    """
    poems = load_poems()
    cleaned_input = normalize_text(recognized_text)

    if not cleaned_input:
        return None, 0

    best_match = None
    best_score = 0

    for poem in poems:
        title = poem.get("title", "")
        author = poem.get("author", "")
        dynasty = poem.get("dynasty", "")
        content_list = poem.get("content", [])
        tags = poem.get("tags", [])

        clean_title = normalize_text(title)
        clean_author = normalize_text(author)
        clean_dynasty = normalize_text(dynasty)
        clean_content = normalize_text("".join(content_list))
        clean_tags = normalize_text("".join(tags))

        score = 0

        if clean_title and clean_title in cleaned_input:
            score += 10

        if clean_author and clean_author in cleaned_input:
            score += 3

        if clean_dynasty and clean_dynasty in cleaned_input:
            score += 1

        if clean_content and clean_content in cleaned_input:
            score += 20

        if clean_tags and clean_tags in cleaned_input:
            score += 3

        for line in content_list:
            clean_line = normalize_text(line)

            if not clean_line:
                continue

            if clean_line in cleaned_input:
                score += 6

            if cleaned_input in clean_line:
                score += 4

            common_count = 0
            for char in cleaned_input:
                if char in clean_line:
                    common_count += 1

            if len(clean_line) > 0 and common_count >= max(2, len(clean_line) // 2):
                score += 2

        if score > best_score:
            best_score = score
            best_match = poem

    return best_match, best_score


def expand_scene_keywords(tags: list[str]) -> list[str]:
    """
    把图像识别标签扩展成适合匹配古诗 tags 的关键词。
    """
    tag_text = "".join(tags)

    keywords = list(tags)

    scene_map = {
        "月": ["月亮", "夜晚", "思乡"],
        "夜": ["月亮", "夜晚", "思乡"],
        "天空": ["月亮", "自然"],
        "春": ["春天", "自然", "鸟", "花"],
        "花": ["春天", "自然"],
        "鸟": ["春天", "自然"],
        "鹅": ["鹅", "动物", "水"],
        "鸟类": ["鹅", "动物"],
        "水": ["水", "自然", "鹅"],
        "河": ["水", "自然"],
        "湖": ["水", "自然"],
        "田": ["农田", "劳动"],
        "稻": ["农田", "劳动"],
        "米": ["农田", "劳动"],
        "农": ["农田", "劳动"],
        "山": ["山水", "自然", "登高"],
        "楼": ["登高", "山水"],
        "树": ["自然", "春天"],
        "草": ["自然", "春天"],
        "太阳": ["自然", "春天"],
        "云": ["自然", "山水"],
        "雪": ["冬天", "自然"],
        "雨": ["自然", "春天"]
    }

    for key, values in scene_map.items():
        if key in tag_text:
            keywords.extend(values)

    return list(dict.fromkeys(keywords))


def match_poem_by_scene_tags(scene_tags: list[str]):
    """
    根据图像识别出的风景/物体标签匹配古诗。
    """
    poems = load_poems()

    if not scene_tags:
        return None, 0, []

    keywords = expand_scene_keywords(scene_tags)

    best_match = None
    best_score = 0

    for poem in poems:
        title = poem.get("title", "")
        content_list = poem.get("content", [])
        tags = poem.get("tags", [])

        poem_text = normalize_text(
            title + "".join(content_list) + "".join(tags)
        )

        score = 0

        for keyword in keywords:
            clean_keyword = normalize_text(keyword)

            if clean_keyword and clean_keyword in poem_text:
                score += 3

        if score > best_score:
            best_score = score
            best_match = poem

    return best_match, best_score, keywords


def build_poem_response(poem):
    """
    统一返回古诗数据结构。

    为兼容前端，既返回 data，也返回 matched_poem。
    """
    poem_data = {
        "id": poem.get("id"),
        "title": poem.get("title"),
        "author": poem.get("author"),
        "dynasty": poem.get("dynasty"),
        "content": poem.get("content", []),
        "tags": poem.get("tags", [])
    }

    return poem_data


@router.post("/ocr")
def recognize_photo(request: PhotoRequest):
    """
    拍照识诗接口。

    1. text 模式：
       直接根据文字匹配古诗。

    2. image_base64 模式：
       先 OCR 识别图片文字；
       如果文字匹配失败，再识别图片场景标签；
       根据风景/物体标签匹配古诗。
    """

    mode = request.mode or "text"

    try:
        if mode == "text":
            recognized_text = request.text or request.image or ""

            poem, score = match_poem_by_text(recognized_text)

            if not poem:
                return {
                    "success": False,
                    "mode": mode,
                    "match_type": "text",
                    "recognized_text": recognized_text,
                    "message": "未匹配到对应古诗"
                }

            poem_data = build_poem_response(poem)

            return {
                "success": True,
                "mode": mode,
                "match_type": "text",
                "recognized_text": recognized_text,
                "score": score,
                "data": poem_data,
                "matched_poem": poem_data
            }

        if mode == "image_base64":
            if not request.image:
                return {
                    "success": False,
                    "mode": mode,
                    "message": "image 不能为空，请传入 base64 图片数据"
                }

            recognized_text = baidu_ocr_text(request.image)
            poem, text_score = match_poem_by_text(recognized_text)

            if poem:
                poem_data = build_poem_response(poem)

                return {
                    "success": True,
                    "mode": mode,
                    "match_type": "text",
                    "recognized_text": recognized_text,
                    "scene_tags": [],
                    "expanded_keywords": [],
                    "score": text_score,
                    "data": poem_data,
                    "matched_poem": poem_data
                }

            scene_tags = baidu_scene_tags(request.image)
            scene_poem, scene_score, expanded_keywords = match_poem_by_scene_tags(scene_tags)

            if not scene_poem:
                return {
                    "success": False,
                    "mode": mode,
                    "match_type": "scene",
                    "recognized_text": recognized_text,
                    "scene_tags": scene_tags,
                    "expanded_keywords": expanded_keywords,
                    "message": "未根据图片文字或风景识别到对应古诗"
                }

            poem_data = build_poem_response(scene_poem)

            return {
                "success": True,
                "mode": mode,
                "match_type": "scene",
                "recognized_text": recognized_text,
                "scene_tags": scene_tags,
                "expanded_keywords": expanded_keywords,
                "score": scene_score,
                "data": poem_data,
                "matched_poem": poem_data
            }

        return {
            "success": False,
            "mode": mode,
            "message": "mode 参数不支持，请使用 text 或 image_base64"
        }

    except Exception as e:
        return {
            "success": False,
            "mode": mode,
            "message": "拍照识诗识别失败",
            "error": str(e)
        }