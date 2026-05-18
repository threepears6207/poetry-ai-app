from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# TODO: 陈誉文负责实现
#
# 该接口支持两种模式，由前端传入 mode 参数决定：
#
# 模式1：text（拍文字）
#   拍摄书本、墙上写的古诗等
#   流程：图片 → OCR识别文字 → 数据库匹配古诗
#   使用：腾讯云通用OCR 或 百度OCR API
#
# 模式2：scene（拍风景）
#   拍摄湖、山、月亮、雨天等自然环境
#   流程：图片 → AI识图理解场景内容 → 根据意境推荐匹配的古诗
#   使用：蓝心大模型（支持图片输入）或 vivo 通用OCR的图像理解能力
#   提示词参考：
#     "请描述这张图片的场景和意境，然后推荐3首最匹配的古诗，
#      只返回JSON格式：{scene_desc: '...', poems: [{title, author, reason}]}"


class PhotoRequest(BaseModel):
    image: str   # 图片的 Base64 编码字符串
    mode: str    # "text"（拍文字）或 "scene"（拍风景）


@router.post("/ocr")
def recognize_photo(request: PhotoRequest):
    """
    拍照识诗，支持两种模式：
    - mode="text"：拍含有古诗文字的图片，识别文字并匹配数据库中的古诗
    - mode="scene"：拍自然风景，AI理解场景意境后推荐匹配的古诗
    """
    if request.mode == "text":
        # TODO: 调用 OCR API 识别文字，再去数据库匹配古诗
        # 成功返回示例：
        # {
        #   "success": True,
        #   "mode": "text",
        #   "recognized_text": "床前明月光疑是地上霜",
        #   "matched_poem": {
        #     "id": "poem_001",
        #     "title": "静夜思",
        #     "author": "李白",
        #     "dynasty": "唐",
        #     "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"]
        #   }
        # }
        return {"success": False, "mode": "text", "error": "接口待实现"}

    elif request.mode == "scene":
        # TODO: 把图片传给 AI（蓝心大模型或其他支持图片的模型）
        # 让 AI 描述图片场景，并推荐意境匹配的古诗列表
        # 成功返回示例：
        # {
        #   "success": True,
        #   "mode": "scene",
        #   "scene_desc": "图片展示了一轮明月挂在夜空，月光洒在平静的湖面上",
        #   "matched_poems": [
        #     {"id": "poem_001", "title": "静夜思", "author": "李白", "reason": "月夜思乡意境"},
        #     {"id": "poem_002", "title": "春江花月夜", "author": "张若虚", "reason": "月色江景相映"}
        #   ]
        # }
        return {"success": False, "mode": "scene", "error": "接口待实现"}

    else:
        return {"success": False, "error": "mode 参数只能是 'text' 或 'scene'"}
