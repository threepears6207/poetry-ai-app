from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# TODO: 陈誉文负责实现
# AI能力：蓝心音频生成 API（文字转语音）


class TTSRequest(BaseModel):
    text: str  # 要朗读的诗句内容


@router.post("/tts")
def text_to_speech(request: TTSRequest):
    """
    将诗句内容转换为语音朗读
    - text: 要朗读的文本内容
    返回音频文件 URL
    """
    # TODO: 调用蓝心音频生成 API
    return {
        "success": False,
        "error": "接口待实现"
    }
