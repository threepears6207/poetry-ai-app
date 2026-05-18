from fastapi import APIRouter
from pydantic import BaseModel
import os

router = APIRouter()

# TODO: 陈俪姗负责实现
# AI能力：蓝心图片生成 API
# 参考 vivo 开放平台文档：https://api-ai.vivo.com.cn


class GenerateImageRequest(BaseModel):
    poem_id: str
    content: str  # 诗句内容，作为图片生成的提示词


@router.post("/generate/image")
def generate_image(request: GenerateImageRequest):
    """
    根据诗句内容生成 AI 配图
    - poem_id: 诗词ID
    - content: 诗句内容（作为图片生成的提示词）
    """
    # TODO: 调用蓝心图片生成 API
    return {
        "success": False,
        "error": "接口待实现"
    }
