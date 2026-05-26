import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

DATA_PATH = Path(__file__).parent / "data" / "poems.json"


class PhotoRequest(BaseModel):
    image: str
    mode: str = "text"


def load_poems():
    if not DATA_PATH.exists():
        return []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """
    去掉标点、空格、换行，方便匹配。
    例如：
    床前明月光，疑是地上霜。
    会变成：
    床前明月光疑是地上霜
    """
    remove_chars = [
        "，", "。", "？", "！", ",", ".", "?", "!",
        "、", "；", ";", "：", ":", "\n", "\r", " ",
        "“", "”", "\"", "'", "《", "》"
    ]

    for ch in remove_chars:
        text = text.replace(ch, "")

    return text.strip()


def match_poem_by_text(recognized_text: str):
    poems = load_poems()
    cleaned_input = normalize_text(recognized_text)

    best_match = None
    best_score = 0

    for poem in poems:
        title = poem.get("title", "")
        author = poem.get("author", "")
        dynasty = poem.get("dynasty", "")
        content_list = poem.get("content", [])

        content_text = normalize_text("".join(content_list))

        score = 0

        # 1. 标题命中
        if title and title in cleaned_input:
            score += 10

        # 2. 作者命中
        if author and author in cleaned_input:
            score += 3

        # 3. 完整诗句文本命中
        if content_text and content_text in cleaned_input:
            score += 20

        # 4. 单句命中
        for line in content_list:
            clean_line = normalize_text(line)

            if clean_line and clean_line in cleaned_input:
                score += 5

            # 输入内容是某一句的一部分，例如“床前明月光”
            if cleaned_input and cleaned_input in clean_line:
                score += 4

        # 5. 输入内容是整首诗的一部分
        if cleaned_input and cleaned_input in content_text:
            score += 8

        if score > best_score:
            best_score = score
            best_match = poem

    if best_score <= 0:
        return None

    return best_match
def recognize_text_from_image_base64(image_base64: str) -> str:
    """
    真实 OCR 预留函数。

    当前阶段：
    - 暂时不调用第三方 OCR
    - 只做接口结构预留
    - 后续拿到腾讯云 OCR / 百度 OCR Key 后，在这里实现图片文字识别

    参数：
    - image_base64: 前端上传的图片 base64 字符串

    返回：
    - OCR 识别出的文字
    """
    # TODO: 后续在这里接入真实 OCR API
    return ""

@router.post("/ocr")
def recognize_photo(request: PhotoRequest):
    """
    拍照识诗接口。

    支持两种模式：
    1. mode='text'
       当前演示版，直接把 image 字段当作已识别文本。

    2. mode='image_base64'
       真实图片 OCR 预留模式，后续用于接入腾讯云 OCR / 百度 OCR。
    """

    if request.mode == "text":
        recognized_text = request.image

    elif request.mode == "image_base64":
        recognized_text = recognize_text_from_image_base64(request.image)

        if not recognized_text:
            return {
                "success": False,
                "mode": "image_base64",
                "error": "图片 OCR 功能暂未接入真实服务，请先使用 mode='text' 进行演示测试"
            }

    else:
        return {
            "success": False,
            "mode": request.mode,
            "error": "不支持的识别模式，目前支持 text 和 image_base64"
        }

    matched_poem = match_poem_by_text(recognized_text)

    if not matched_poem:
        return {
            "success": False,
            "mode": request.mode,
            "recognized_text": recognized_text,
            "error": "未匹配到古诗"
        }

    return {
        "success": True,
        "mode": request.mode,
        "recognized_text": recognized_text,
        "matched_poem": matched_poem
    }