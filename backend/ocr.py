import base64
import os
import re
from difflib import SequenceMatcher
from typing import Optional

import requests
from fastapi import APIRouter
from pydantic import BaseModel

from poems import load_poems

router = APIRouter()

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

    def best_line_similarity(line: str) -> float:
        if not line or not cleaned_input:
            return 0.0
        if len(cleaned_input) <= len(line):
            return SequenceMatcher(None, line, cleaned_input).ratio()
        window_size = len(line)
        return max(
            SequenceMatcher(None, line, cleaned_input[index:index + window_size]).ratio()
            for index in range(len(cleaned_input) - window_size + 1)
        )

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
        score = 0
        exact_line_count = 0
        fuzzy_line_count = 0
        has_strong_evidence = False

        if clean_title and clean_title in cleaned_input:
            score += 12
            has_strong_evidence = True

        if clean_author and clean_author in cleaned_input:
            score += 3

        if clean_dynasty and clean_dynasty in cleaned_input:
            score += 1

        if clean_content and clean_content in cleaned_input:
            score += 30
            has_strong_evidence = True

        for line in content_list:
            clean_line = normalize_text(line)

            if not clean_line:
                continue

            if clean_line in cleaned_input:
                score += 8
                exact_line_count += 1
                has_strong_evidence = True
                continue

            similarity = best_line_similarity(clean_line)
            if similarity >= 0.82:
                score += 5
                fuzzy_line_count += 1

        # 只共享“春、风、月”等零散汉字不能证明图片中是这首诗。
        # 至少需要标题/完整诗句，或两句都与原诗高度相似，才允许返回匹配结果。
        if fuzzy_line_count >= 2:
            has_strong_evidence = True

        if has_strong_evidence and score > best_score:
            best_score = score
            best_match = poem

    return best_match, best_score


def expand_scene_keywords(tags: list[str]) -> list[str]:
    """
    把图像识别标签扩展成适合匹配古诗 tags 的关键词。
    """
    tag_text = "".join(tags)

    # “自然景观、商品、室内”等宽泛的原始识图标签不能直接匹配诗歌，
    # 否则容易落到诗库中靠前的《春晓》。只使用规则映射出的明确关键词。
    keywords = []

    festival_terms = ("灯笼", "春联", "对联", "年货", "红包", "春节", "过年", "新年")
    if any(term in tag_text for term in festival_terms):
        # 明确识别到春节场景时优先匹配节日诗，避免后面的“花/春天”
        # 之类宽泛线索又把结果带回《春晓》。
        return ["节日", "春节", "新年", "春天", "生活"]

    scene_map = {
        "月": ["月亮", "夜晚", "思乡"],
        "夜": ["月亮", "夜晚", "思乡"],
        "天空": ["月亮", "自然"],
        "春景": ["春天", "自然", "鸟", "花"],
        "春天": ["春天", "自然", "鸟", "花"],
        "花": ["春天", "自然"],
        "鸟": ["鸟", "动物", "自然"],
        "鹅": ["鹅", "动物", "水"],
        "鸟类": ["鸟", "动物", "自然"],
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
        if any(key in tag for tag in tags):
            keywords.extend(values)

    return list(dict.fromkeys(keywords))


def infer_scene_tags_from_text(recognized_text: str) -> list[str]:
    """从照片文字中提取不会直接对应诗句、但能说明场景的节日线索。"""
    text = normalize_text(recognized_text)
    strong_terms = ("春节", "新春", "过年", "春联", "年货", "红包", "福字", "恭喜发财")
    if any(term in text for term in strong_terms):
        return ["春节"]

    weak_terms = ("新年", "迎春", "吉祥", "平安", "发财")
    if sum(1 for term in weak_terms if term in text) >= 2:
        return ["春节"]
    return []


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

        theme_tags = poem.get("theme_tags", [])
        title_text = normalize_text(title)
        content_text = normalize_text("".join(content_list))
        tag_text = normalize_text("".join(tags) + "".join(theme_tags))

        score = 0

        for keyword in keywords:
            clean_keyword = normalize_text(keyword)

            if not clean_keyword:
                continue
            if clean_keyword in tag_text or clean_keyword in title_text:
                score += 4
            elif len(clean_keyword) >= 2 and clean_keyword in content_text:
                score += 1

        if score > best_score:
            best_score = score
            best_match = poem

    # 场景识诗至少需要两个有效主题命中；不足时宁可提示未识别。
    if best_score < 8:
        return None, best_score, keywords

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
        "tags": poem.get("tags", []),
        "theme_tags": poem.get("theme_tags", [])
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
            scene_tags = list(dict.fromkeys(
                scene_tags + infer_scene_tags_from_text(recognized_text)
            ))
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
