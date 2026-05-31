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
OCR_PROVIDER=baidu
BAIDU_OCR_API_KEY=你的百度OCR API Key
BAIDU_OCR_SECRET_KEY=你的百度OCR Secret Key
BAIDU_IMAGE_API_KEY=你的百度图像识别 API Key
BAIDU_IMAGE_SECRET_KEY=你的百度图像识别 Secret Key
```

说明：

- `VIVO_APP_KEY`：用于 AI 诗人对话和 AI 配图接口。
- `VIVO_APP_ID`：当前主要用于 `/ping` 健康检查接口返回环境配置状态。
- `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY`：用于有文字图片的 OCR 识别。
- `BAIDU_IMAGE_API_KEY` / `BAIDU_IMAGE_SECRET_KEY`：用于无文字风景图的场景识别。
- 如果未配置 `VIVO_APP_KEY`，基础业务接口仍可运行，但 `/chat`、`/generate/image` 等 AI 能力无法正常调用。

---

## 文件说明

| 文件 | 说明 |
|---|---|
| main.py | 主入口，注册所有路由，配置 CORS，提供 `/` 和 `/ping` |
| chat.py | AI 诗人对话接口 `POST /chat` |
| poems.py | 古诗搜索与详情接口，支持关键词、作者、朝代、标签筛选 |
| generate.py | AI 配图接口 `POST /generate/image`，按诗句生成连续插画分镜，含本地缓存机制 |
| tts.py | 语音朗读接口 `POST /tts`，使用 edge-tts 生成中文朗读音频，返回本地音频 URL |
| ocr.py | 拍照识诗接口 `POST /ocr`，支持文字图片调用百度 OCR 识别、风景图调用百度图像识别匹配古诗 |
| record.py | 学习记录接口，包含记录写入、查询和学习统计 |
| recommend.py | 推荐接口 `GET /recommend`，基于学习记录推荐未学习古诗 |
| test_api.py | 后端接口稳定性测试脚本，用于快速检查主要接口是否可用 |
| test_chat.py | AI 对话接口测试脚本 |
| data/poems.json | 本地古诗数据文件 |
| data/records.json | 本地学习记录数据文件，测试时会变化，提交前注意不要误提交测试数据 |
| static/poem_images_cache.json | AI 配图本地缓存文件，存储已生成过的诗句图片路径，避免重复调用模型 |
| API.md | 完整接口文档（入参/出参格式） |

---

## 当前功能进度概览

| 项目功能目标 | 当前实现情况 | 对应后端能力 |
|---|---|---|
| 古诗识别与输入 | 已实现 | 支持文字图片百度 OCR 识别 + 风景图场景识别匹配古诗 |
| 古诗搜索与详情 | 已实现 | 支持搜索、详情查询、作者/朝代/标签筛选 |
| 智能讲解与交互 | 已实现 | 已实现 AI 诗人对话接口，依赖蓝心 API Key |
| 多模态内容生成 | 已实现 | 已实现 AI 配图接口，含分镜规划和本地缓存，已生成古诗秒回 |
| 语音朗读 | 已实现 | `/tts` 使用 edge-tts 生成中文朗读音频，返回可播放音频 URL |
| 趣味学习与巩固 | 暂未实现独立后端接口 | 前端可先做页面演示，后续可补充闯关、跟读、配对等记录接口 |
| 学习记录与推荐 | 已实现 | 支持记录学习、查询记录、学习统计、推荐未学习古诗 |
| 家长管理与共育 | 部分实现 | 已提供学习统计接口，前端家长端已可接入真实学习数据 |
| 接口稳定性保障 | 已实现基础脚本 | `test_api.py` 可快速测试主要后端接口 |

---

## 接口状态

| 接口 | 方法 | 说明 | 状态 |
|---|---|---|---|
| `/` | GET | 后端根路径，返回 API 运行状态 | ✅ 已完成 |
| `/ping` | GET | 健康检查，返回 vivo 配置状态 | ✅ 已完成 |
| `/chat` | POST | AI 诗人对话 | ✅ 已完成，需配置 `VIVO_APP_KEY` |
| `/poems/search` | GET | 古诗搜索，支持关键词、作者、朝代、标签、分页 | ✅ 已完成 |
| `/poems/{poem_id}` | GET | 古诗详情 | ✅ 已完成 |
| `/record` | POST | 添加学习记录 | ✅ 已完成 |
| `/record` | GET | 查询用户学习记录 | ✅ 已完成 |
| `/record/summary` | GET | 用户学习统计，供家长端展示 | ✅ 已完成 |
| `/recommend` | GET | 推荐未学习古诗 | ✅ 已完成 |
| `/ocr` | POST | 拍照识诗，支持文字图片 OCR 识别和风景图场景识别 | ✅ 已完成 |
| `/generate/image` | POST | AI 配图生成，含本地缓存 | ✅ 已完成 |
| `/tts` | POST | 语音朗读，使用 edge-tts 生成音频 | ✅ 已完成 |

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

支持两种模式：

- **文字图片模式**：调用百度 OCR 识别图片中的诗句文字，再匹配古诗；
- **风景图模式**：调用百度图像识别，识别场景标签后匹配古诗；
- 需配置 `BAIDU_OCR_API_KEY`、`BAIDU_OCR_SECRET_KEY`、`BAIDU_IMAGE_API_KEY`、`BAIDU_IMAGE_SECRET_KEY`。

请求体示例（图片 base64 模式）：

```json
{
  "image_base64": "图片的base64字符串"
}
```

返回示例（文字图片）：

```json
{
  "success": true,
  "mode": "image_base64",
  "recognized_text": "床前明月光疑是地上霜",
  "matched_poem": {
    "id": "poem_002",
    "title": "静夜思",
    "author": "李白",
    "dynasty": "唐",
    "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
    "tags": ["月亮", "思乡", "李白"]
  }
}
```

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

为古诗每句话生成一张横版配图，图片之间保持连续分镜效果。已生成过的古诗自动缓存，下次请求直接返回，不重复调用模型。

**参数说明：**

注意 poems.json 与接口参数的字段名对应关系：

| poems.json 字段 | 接口参数名 |
|---|---|
| `id` | `poem_id` |
| `title` | `poem_title` |
| `content` | `poem_content` |
| `author` | `poet_name` |
| `dynasty` | `dynasty` |
| `tags` | `tags` |

请求体示例：

```json
{
  "poem_id": "poem_002",
  "poem_title": "静夜思",
  "poem_content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
  "poet_name": "李白",
  "dynasty": "唐",
  "tags": ["月亮", "思乡", "李白"]
}
```

**缓存机制：**

- 同一首诗（按 `poem_id` 识别）生成成功后自动写入 `static/poem_images_cache.json`；
- 下次请求同一首诗时直接返回缓存，`from_cache: true`，秒回，不再调用模型；
- 当前已预生成：《静夜思》（poem_002）；
- 如需强制重新生成，请求体加 `"force_regenerate": true`。

**响应结构：**

```json
{
  "success": true,
  "from_cache": true,
  "poem_title": "静夜思",
  "has_character": true,
  "character_desc": "人物形象描述",
  "recurring_elements": "固定建筑元素描述",
  "total_lines": 4,
  "frames": [
    {
      "index": 0,
      "line": "床前明月光",
      "scene": "规划的场景描述",
      "shot_type": "中景",
      "image_url": "/static/images/poems/poem_002/frame_0.jpg",
      "duration_ms": 3000
    }
  ],
  "errors": []
}
```

**前端接入注意事项：**

- `image_url` 为本地静态路径，拼接 `http://127.0.0.1:8000` 前缀即可访问；
- 已缓存的诗秒回；未缓存的诗首次生成约需 1-2 分钟，前端**必须显示 loading 动画**；
- 建议进入详情页时立即发起请求，不要等用户点击；
- 请求超时时间必须设置为 **120 秒以上**；
- `success: false` 时 `frames` 为空数组，页面显示"配图生成中，请稍后重试"，不要白屏。

---

### 9. 语音朗读接口说明

`POST /tts`

使用 edge-tts 生成中文朗读音频，返回本地可访问的 mp3 音频 URL。

请求体示例：

```json
{
  "text": "床前明月光，疑是地上霜。",
  "voice": "child"
}
```

支持的 voice 参数：

| voice 值 | 对应音色 |
|---|---|
| child / female / default | 晓晓（女声，适合儿童） |
| male | 云希（男声） |
| xiaoyi | 晓伊 |
| yunjian | 云健 |

返回示例：

```json
{
  "success": true,
  "message": "语音生成成功",
  "provider": "edge-tts",
  "audio_url": "/static/audio/tts_1234567890.mp3"
}
```

- `audio_url` 为本地静态路径，拼接 `http://127.0.0.1:8000` 前缀即可播放；
- edge-tts 需要访问微软服务器，网络异常时可能失败；
- 失败时返回 `"success": false` 和错误信息。

---

## 数据存储说明

当前后端暂时使用 JSON 文件存储数据：

| 文件 | 说明 |
|---|---|
| `data/poems.json` | 古诗基础数据 |
| `data/records.json` | 用户学习记录 |
| `static/poem_images_cache.json` | AI 配图缓存，存储已生成图片的本地路径 |
| `static/images/poems/{poem_id}/` | 各首古诗的生成图片，按 poem_id 分文件夹存放 |
| `static/audio/` | TTS 生成的音频文件 |

注意：

- 当前阶段未接入 MySQL 或 SQLite；
- `records.json` 会在调用 `POST /record` 或运行测试脚本时发生变化，提交前注意检查；
- `static/audio/` 下的音频文件为运行时生成，无需提交到 GitHub；
- `static/images/` 和 `static/poem_images_cache.json` 建议提交，前端联调时可直接使用已缓存的图片。

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
- 完成 OCR 接口 `/ocr`，支持文字图片百度 OCR 识别和风景图场景识别；
- 完成 AI 诗人对话接口 `/chat` 的核心逻辑；
- 完成 AI 配图接口 `/generate/image`，含两阶段分镜规划和本地缓存机制；
- 完成语音朗读接口 `/tts`，使用 edge-tts 生成中文朗读音频；
- 完成后端接口测试脚本 `test_api.py`；
- 预生成《静夜思》配图并写入缓存，前端可直接使用。
