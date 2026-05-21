# Backend - FastAPI 后端

负责人：陈俪姗、陈誉文

---

## 环境要求

- Python 3.10+
- pip

---

## 启动方法

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

启动后访问 `http://127.0.0.1:8000/docs` 查看接口文档（Swagger UI）。

---

## 环境变量配置

在 `backend/` 目录下新建 `.env` 文件：

```
VIVO_APP_KEY=你的蓝心APIKey
```

---

## 文件说明

| 文件 | 说明 |
|---|---|
| main.py | 主入口，注册所有路由 |
| chat.py | AI 诗人对话接口 POST /chat |
| poems.py | 古诗搜索与详情接口 |
| generate.py | AI 配图接口 POST /generate/image |
| tts.py | 语音朗读接口 POST /tts |
| ocr.py | 拍照识诗接口 POST /ocr |
| record.py | 学习记录接口 POST /record |
| recommend.py | 推荐接口 GET /recommend |
| data/ | 古诗数据库文件 |
| API.md | 完整接口文档（入参/出参格式） |

---

## 接口状态

| 接口 | 方法 | 说明 | 状态 |
|---|---|---|---|
| /chat | POST | AI 诗人对话 | ✅ 已完成 |
| /poems/search | GET | 古诗搜索 | ✅ 已完成 |
| /poems/{id} | GET | 古诗详情 | ✅ 已完成 |
| /record | POST | 学习记录 | ✅ 已完成 |
| /generate/image | POST | AI 配图生成 | 🔧 开发中 |
| /tts | POST | 语音朗读 | 🔧 开发中 |
| /ocr | POST | 拍照识诗 | 🔧 开发中 |
| /recommend | GET | 古诗推荐 | 🔧 开发中 |

---

## AI 对话接口说明

`POST /chat` 请求体：

```json
{
  "message": "黄鹂是什么",
  "poet_name": "杜甫",
  "dynasty": "唐",
  "poem_title": "绝句",
  "poem_content": "两个黄鹂鸣翠柳，一行白鹭上青天。窗含西岭千秋雪，门泊东吴万里船。",
  "history": [
    {"role": "user", "content": "杜甫爷爷你好"},
    {"role": "assistant", "content": "小朋友你好，我是唐代诗人杜甫..."}
  ]
}
```

- `history` 由前端维护，每轮对话后追加，完整传入
- 第一轮 `message` 传空字符串或 `__init__`，诗人会主动开口
- 目前支持的诗人性格库：李白、杜甫、苏轼、白居易、王维
