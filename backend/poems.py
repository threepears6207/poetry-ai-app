from fastapi import APIRouter

router = APIRouter()

# TODO: 陈誉文负责实现
# 数据来源：chinese-poetry 开源数据集（GitHub: chinese-poetry/chinese-poetry）
# 建议把数据集的 JSON 文件读入内存或导入 SQLite 数据库


@router.get("/poems/search")
def search_poems(keyword: str, page: int = 1, page_size: int = 10):
    """
    搜索古诗
    - keyword: 搜索关键词（支持标题、作者、诗句内容）
    - page: 页码，默认1
    - page_size: 每页数量，默认10
    """
    # TODO: 实现搜索逻辑
    return {
        "success": True,
        "total": 0,
        "data": []
    }


@router.get("/poems/{poem_id}")
def get_poem_detail(poem_id: str):
    """
    获取古诗详情
    - poem_id: 诗词唯一ID
    返回：标题、作者、朝代、诗句内容
    """
    # TODO: 实现详情查询逻辑
    return {
        "success": True,
        "data": {
            "id": poem_id,
            "title": "",
            "author": "",
            "dynasty": "",
            "content": []
        }
    }
