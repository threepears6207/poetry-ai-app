from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# TODO: 陈誉文负责实现
# 建议用一个简单的 JSON 文件或 SQLite 数据库记录用户看过的诗


class RecordRequest(BaseModel):
    poem_id: str
    user_id: str


@router.post("/record")
def add_record(request: RecordRequest):
    """
    记录用户查看过的古诗
    - poem_id: 诗词ID
    - user_id: 用户ID
    """
    # TODO: 实现记录存储逻辑
    return {"success": True, "message": "记录成功"}
