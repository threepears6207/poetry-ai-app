from fastapi import APIRouter

router = APIRouter()

# TODO: 陈誉文负责实现
# 逻辑：查出该用户已看过的诗，从数据集中随机推荐未看过的


@router.get("/recommend")
def recommend_poems(user_id: str, limit: int = 5):
    """
    推荐用户未看过的古诗
    - user_id: 用户ID
    - limit: 返回数量，默认5
    """
    # TODO: 实现推荐逻辑
    return {
        "success": True,
        "data": []
    }
