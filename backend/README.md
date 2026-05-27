# Backend - FastAPI 后端

负责人：陈俪姗、陈誉文

---

## 环境要求

- Python 3.10+
- pip
- FastAPI
- Uvicorn
- requests
- python-dotenv

---

## 启动方法

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

如需进行手机真机或局域网联调，建议使用：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问 `http://127.0.0.1:8000/docs` 查看接口文档（Swagger UI）。

---

## 环境变量配置

在 `backend/` 目录下新建 `.env` 文件：

```env
VIVO_APP_KEY=你的蓝心APIKey
VIVO_APP_ID=你的蓝心APPID
```

说明：

- `VIVO_APP_KEY`：用于 AI 诗人对话和 AI 配图接口。
- `VIVO_APP_ID`：当前主要用于 `/ping` 健康检查接口返回环境配置状态。
- 如果未配置 `VIVO_APP_KEY`，基础业务接口仍可运行，但 `/chat`、`/generate/image` 等 AI 能力可能无法正常调用。

---

## 文件说明

| 文件 | 说明 |
|---|---|
| main.py | 主入口，注册所有路由，配置 CORS，提供 `/` 和 `/ping` |
| chat.py | AI 诗人对话接口 `POST /chat` |
| poems.py | 古诗搜索与详情接口，支持关键词、作者、朝代、标签筛选 |
| generate.py | AI 配图接口 `POST /generate/image`，用于按诗句生成连续插画分镜 |
| tts.py | 语音朗读接口 `POST /tts`，当前仍为待实现占位接口 |
| ocr.py | 拍照识诗接口 `POST /ocr`，- 文字匹配演示流程已完成；图片 base64 模式入口已完成；真实第三方 OCR 调用暂未完成。|
| record.py | 学习记录接口，包含记录写入、查询和学习统计 |
| recommend.py | 推荐接口 `GET /recommend`，基于学习记录推荐未学习古诗 |
| test_api.py | 后端接口稳定性测试脚本，用于快速检查主要接口是否可用 |
| test_chat.py | AI 对话接口测试脚本 |
| data/poems.json | 本地古诗数据文件 |
| data/records.json | 本地学习记录数据文件，测试时会变化，提交前需注意不要误提交测试数据 |
| API.md | 完整接口文档（入参/出参格式） |

---

## 当前功能进度概览

根据项目书中"输入—理解—互动—巩固—记录—家长共育"的功能目标，目前后端已完成基础业务闭环，并完成部分 AI 能力接入。

| 项目功能目标 | 当前实现情况 | 对应后端能力 |
|---|---|---|
| 古诗识别与输入 | 部分实现 | 已支持文字模拟 OCR 匹配古诗；真实图片 OCR 尚未接入 |
| 古诗搜索与详情 | 已实现 | 支持搜索、详情查询、作者/朝代/标签筛选 |
| 智能讲解与交互 | 已实现接口逻辑 | 已实现 AI 诗人对话接口，依赖蓝心 API Key |
| 多模态内容生成 | 部分实现 | 已实现 AI 配图接口逻辑，需配置蓝心 API 并继续联调稳定性 |
| 语音朗读 | 未实现 | `/tts` 当前仍返回"接口待实现" |
| 趣味学习与巩固 | 暂未实现独立后端接口 | 前端可先做页面演示，后续可补充闯关、跟读、配对等记录接口 |
| 学习记录与推荐 | 已实现 | 支持记录学习、查询记录、学习统计、推荐未学习古诗 |
| 家长管理与共育 | 部分实现 | 已提供学习统计接口，前端家长端已可接入真实学习数据；时长限制等管理能力仍可扩展 |
| 接口稳定性保障 | 已实现基础脚本 | `test_api.py` 可快速测试主要后端接口 |

---

## 接口状态

| 接口 | 方法 | 说明 | 状态 |
|---|---|---|---|
| `/` | GET | 后端根路径，返回 API 运行状态 | ✅ 已完成 |
| `/ping` | GET | 健康检查，返回 vivo 配置状态 | ✅ 已完成 |
| `/chat` | POST | AI 诗人对话 | ✅ 已完成接口逻辑，需配置 `VIVO_APP_KEY` |
| `/poems/search` | GET | 古诗搜索，支持关键词、作者、朝代、标签、分页 | ✅ 已完成 |
| `/poems/{poem_id}` | GET | 古诗详情 | ✅ 已完成 |
| `/record` | POST | 添加学习记录 | ✅ 已完成 |
| `/record` | GET | 查询用户学习记录 | ✅ 已完成 |
| `/record/summary` | GET | 用户学习统计，供家长端展示 | ✅ 已完成 |
| `/recommend` | GET | 推荐未学习古诗 | ✅ 已完成 |
| `/ocr` | POST | 拍照识诗，当前支持两种模式，根据文字匹配，真实图片ocr预留 | ✅ 演示版已完成，真实图片 OCR 待接入 |
| `/generate/image` | POST | AI 配图生成 | ✅ 已完成（优化中） |
| `/tts` | POST | 语音朗读 | ⏳ 待实现 |

---

## 主要接口说明

### 1. 健康检查

`GET /ping`

用于检查后端服务和环境变量配置状态。

返回示例：

```json
{
  "message": "pong",
  "vivo_app_id": "your_app_id",
  "has_api_key": true
}
```

---

### 2. 古诗搜索

`GET /poems/search`

支持综合关键词搜索，以及作者、朝代、标签筛选。

请求示例：

```http
GET /poems/search?keyword=春&page=1&page_size=10
GET /poems/search?author=李白
GET /poems/search?dynasty=唐
GET /poems/search?tag=思乡
GET /poems/search?keyword=月&author=李白&dynasty=唐
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | string | 否 | 综合搜索标题、作者、朝代、诗句、标签 |
| author | string | 否 | 作者筛选，例如"李白" |
| dynasty | string | 否 | 朝代筛选，例如"唐" |
| tag | string | 否 | 标签筛选，例如"思乡" |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 10，最大 50 |

返回示例：

```json
{
  "success": true,
  "total": 1,
  "page": 1,
  "page_size": 10,
  "filters": {
    "keyword": "春",
    "author": "",
    "dynasty": "",
    "tag": ""
  },
  "data": [
    {
      "id": "poem_001",
      "title": "春晓",
      "author": "孟浩然",
      "dynasty": "唐",
      "content_preview": "春眠不觉晓，处处闻啼鸟。",
      "tags": ["春天", "自然", "儿童启蒙"]
    }
  ]
}
```

---

### 3. 古诗详情

`GET /poems/{poem_id}`

请求示例：

```http
GET /poems/poem_001
```

返回示例：

```json
{
  "success": true,
  "data": {
    "id": "poem_001",
    "title": "春晓",
    "author": "孟浩然",
    "dynasty": "唐",
    "content": ["春眠不觉晓", "处处闻啼鸟", "夜来风雨声", "花落知多少"],
    "tags": ["春天", "自然", "儿童启蒙"]
  }
}
```

---

### 4. 学习记录

#### 添加学习记录

`POST /record`

请求体示例：

```json
{
  "user_id": "test_user",
  "poem_id": "poem_001",
  "duration_seconds": 30
}
```

返回示例：

```json
{
  "success": true,
  "message": "记录成功"
}
```

#### 查询学习记录

`GET /record?user_id=test_user`

返回示例：

```json
{
  "success": true,
  "total": 1,
  "data": [
    {
      "id": 1,
      "user_id": "test_user",
      "poem_id": "poem_001",
      "duration_seconds": 30,
      "created_at": "2026-05-25 20:30:00"
    }
  ]
}
```

#### 学习统计

`GET /record/summary?user_id=test_user`

用于家长端展示学习情况。

返回示例：

```json
{
  "success": true,
  "user_id": "test_user",
  "learned_count": 2,
  "record_count": 3,
  "total_duration_seconds": 120,
  "learned_poems": [
    {
      "id": "poem_001",
      "title": "春晓",
      "author": "孟浩然",
      "dynasty": "唐",
      "tags": ["春天", "自然", "儿童启蒙"]
    }
  ],
  "recent_records": []
}
```

---

### 5. 推荐古诗

`GET /recommend`

根据用户学习记录，优先推荐用户未学习过的古诗。

请求示例：

```http
GET /recommend?user_id=test_user&limit=5
```

返回示例：

```json
{
  "success": true,
  "user_id": "test_user",
  "total": 5,
  "data": [
    {
      "id": "poem_002",
      "title": "静夜思",
      "author": "李白",
      "dynasty": "唐",
      "content_preview": "床前明月光，疑是地上霜。",
      "tags": ["月亮", "思乡", "儿童启蒙"]
    }
  ]
}
```

---

### 6. 拍照识诗

`POST /ocr`

当前为演示版 OCR：

- 暂不调用真实 OCR 服务；
- 先把 `image` 字段当作"已经识别出的文字"；
- 再用文字匹配 `poems.json` 中的古诗；
- 前端拍照页已可通过测试文字完成"识别文本 → 匹配古诗 → 展示结果 → 跳转详情"的演示闭环。

请求体示例：

```json
{
  "image": "床前明月光疑是地上霜",
  "mode": "text"
}
```

返回示例：

```json
{
  "success": true,
  "mode": "text",
  "recognized_text": "床前明月光疑是地上霜",
  "matched_poem": {
    "id": "poem_002",
    "title": "静夜思",
    "author": "李白",
    "dynasty": "唐",
    "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
    "tags": ["月亮", "思乡", "儿童启蒙"]
  }
}
```

后续计划：接入腾讯云 OCR、百度 OCR 或其他文字识别服务，将真实图片识别结果传入现有匹配逻辑。

---

### 7. AI 对话接口说明

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

- `history` 由前端维护，每轮对话后追加，完整传入；
- 第一轮 `message` 可传空字符串或 `__init__`，诗人会主动开口；
- 目前支持的诗人性格库：李白、杜甫、苏轼、白居易、王维（其他诗人走通用性格）；
- 使用模型：Volc-DeepSeek-V3.2；
- 该接口依赖 `VIVO_APP_KEY`，未配置时会调用失败。

---

### 8. AI 配图接口说明

`POST /generate/image`

用于为古诗每句话生成一张横版配图，并尽量保持连续分镜效果。

请求体示例：

```json
{
  "poem_id": "poem_002",
  "poem_title": "静夜思",
  "poem_content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
  "poet_name": "李白",
  "dynasty": "唐",
  "tags": ["月亮", "思乡"]
}
```

- `poem_content` 直接传 poems.json 里的 `content` 数组；
- `tags` 传 poems.json 里的 `tags` 字段；
- 每句诗生成一张图，4句诗约需 2-4 分钟；
- 图片尺寸 `2560x1440`，横版 16:9；
- 生成流程：整体分镜规划 → 逐句构建 prompt → 逐句调用图像 API。

响应结构：

```json
{
  "success": true,
  "poem_title": "静夜思",
  "has_character": true,
  "character_desc": "人物形象描述",
  "total_lines": 4,
  "frames": [
    {
      "index": 0,
      "line": "床前明月光",
      "scene": "规划的场景描述",
      "image_url": "https://...",
      "duration_ms": 3000
    }
  ],
  "errors": []
}
```

⚠️ **前端注意：请求超时时间必须设 120 秒以上，生成期间显示 loading 状态**

该接口依赖 `VIVO_APP_KEY`，仍需继续进行真实 API 联调和稳定性测试。

---

### 9. 语音朗读接口说明

`POST /tts`

请求体示例：

```json
{
  "text": "床前明月光，疑是地上霜。"
}
```

当前状态：占位接口，返回：

```json
{
  "success": false,
  "error": "接口待实现"
}
```

后续计划：接入文字转语音能力，返回音频 URL 或可播放音频资源。

---

## 数据存储说明

当前后端暂时使用 JSON 文件存储数据：

| 文件 | 说明 |
|---|---|
| `data/poems.json` | 古诗基础数据 |
| `data/records.json` | 用户学习记录 |

注意：

- 当前阶段未接入 MySQL 或 SQLite；
- `records.json` 会在调用 `POST /record` 或运行测试脚本时发生变化；
- 提交代码前应检查 `records.json` 是否只是测试数据变化，避免误提交无关学习记录；
- 后续如需支持多用户、部署和长期数据保存，应升级为数据库存储。

---

## 接口测试脚本

`test_api.py` 用于快速检查后端主要接口是否正常。

使用前先启动后端：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

另开终端运行：

```bash
python test_api.py
```

当前测试覆盖：

- `GET /ping`
- `GET /poems/search`
- `GET /poems/poem_001`
- `GET /recommend`
- `POST /record`
- `GET /record/summary`
- `POST /ocr`

说明：

- 测试脚本主要用于冒烟测试，检查接口是否可访问；
- 脚本会调用 `POST /record`，因此运行后可能修改 `data/records.json`；
- 测试完成后如不需要保留测试记录，应恢复 `records.json`。
- `test_api.py` 已覆盖 `/ocr` 的 `text` 模式和 `image_base64` 占位模式，可用于检查 OCR 接口结构是否正常。

---

## 前端联调说明

### 浏览器本机联调

前端请求地址可使用：

```js
const BASE_URL = 'http://127.0.0.1:8000'
```

### 手机真机联调

如果使用手机或模拟器访问后端，需要将 `BASE_URL` 改为电脑局域网 IP，例如：

```js
const BASE_URL = 'http://192.168.x.x:8000'
```

同时后端启动命令需要使用：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

注意：不要把个人电脑的局域网 IP 提交到 GitHub。

---

## 当前已完成开发记录

- 完成 FastAPI 项目基础结构；
- 完成 CORS 配置，支持前端跨域联调；
- 完成古诗搜索和详情接口；
- 搜索接口已支持 keyword、author、dynasty、tag 和分页；
- 完成学习记录写入和查询接口；
- 完成学习统计接口 `/record/summary`，可供家长端展示；
- 完成推荐接口 `/recommend`，可推荐用户未学习过的古诗；
- 完成演示版 OCR `/ocr`，支持文字匹配古诗；
- 完成 AI 诗人对话接口 `/chat` 的核心逻辑；
- 完成 AI 配图接口 `/generate/image` 的核心逻辑；
- 完成后端接口测试脚本 `test_api.py`。
