# 诗芽小学堂 API 接口文档

> 文档版本：v1.2
> 更新时间：2026-05-27
> 负责人：陈俪姗
> 后端基础URL：http://localhost:8000（开发环境）

---

## 接口列表

| 接口名称 | 请求方式 | 路径 | 负责人 | 状态 |
|---------|---------|------|--------|------|
| 健康检查 | GET | /ping | 陈俪姗 | ✅ |
| AI诗人对话 | POST | /chat | 陈俪姗 | ✅ |
| AI配图生成 | POST | /generate/image | 陈俪姗 | ✅ 优化中 |
| 搜索古诗 | GET | /poems/search | 陈誉文 | ✅ |
| 古诗详情 | GET | /poems/{id} | 陈誉文 | ✅ |
| 学习记录 | POST | /record | 陈誉文 | ✅ |
| 学习统计 | GET | /record/summary | 陈誉文 | ✅ |
| 推荐古诗 | GET | /recommend | 陈誉文 | ✅ |
| 拍照识诗 | POST | /ocr | 陈誉文 | ✅ |
| 语音朗读 | POST | /tts | 陈誉文 | 🔧 开发中 |

---

## 1. 健康检查

- 接口路径：GET /ping
- 功能：检查后端服务是否正常运行

返回示例：
```json
{
  "message": "pong",
  "vivo_app_id": "your_app_id",
  "has_api_key": true
}
```

---

## 2. AI诗人对话

- 接口路径：POST /chat
- 功能：用户向AI诗人提问，AI以对应诗人的语气和性格回答
- 模型：Volc-DeepSeek-V3.2
- 负责人：陈俪姗

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| message | string | 是 | 用户发送的消息，第一轮传空字符串或 `__init__` |
| poet_name | string | 是 | 诗人名，如"李白" |
| dynasty | string | 是 | 朝代，如"唐" |
| poem_title | string | 否 | 当前诗题目 |
| poem_content | string | 否 | 当前诗全文（逗号分隔） |
| history | array | 否 | 对话历史，由前端维护并完整传入 |

请求示例：
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

成功返回：
```json
{
  "success": true,
  "reply": "黄鹂就是黄色的小鸟，叫声很好听。"
}
```

失败返回：
```json
{
  "success": false,
  "error": "API调用失败",
  "raw": ""
}
```

**前端注意：**
- `history` 每轮对话后追加，格式为 `[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]`
- 第一轮 `message` 传 `""` 或 `"__init__"`，诗人会主动开口介绍自己
- 内置性格库：李白、杜甫、苏轼、白居易、王维；其他诗人走通用性格

---

## 3. AI配图生成

- 接口路径：POST /generate/image
- 功能：为古诗每句话分别生成一张横版配图，图片之间有连续性
- 模型：Doubao-Seedream-4.5（蓝心图像生成）
- 负责人：陈俪姗

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| poem_id | string | 否 | 诗词ID |
| poem_title | string | 是 | 诗题目 |
| poem_content | array | 是 | 分句数组，直接传 poems.json 的 content 字段 |
| poet_name | string | 是 | 诗人名 |
| dynasty | string | 是 | 朝代 |
| tags | array | 否 | 意象标签，传 poems.json 的 tags 字段 |

请求示例：
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

成功返回：
```json
{
  "success": true,
  "poem_title": "静夜思",
  "has_character": true,
  "character_desc": "男性，身着唐代文人便服，束发，圆润可爱的儿童插画风格面孔",
  "total_lines": 4,
  "frames": [
    {
      "index": 0,
      "line": "床前明月光",
      "scene": "夜晚室内，月光透过窗棂洒在木床前的地板上，光线如银白色薄雾",
      "image_url": "https://...",
      "duration_ms": 3000
    },
    {
      "index": 1,
      "line": "疑是地上霜",
      "scene": "...",
      "image_url": "https://...",
      "duration_ms": 3000
    }
  ],
  "errors": []
}
```

失败返回：
```json
{
  "success": false,
  "error": "poem_content 不能为空"
}
```

**前端注意：**
- 请求超时时间必须设 **120 秒以上**，4句诗约需 2-4 分钟
- 生成期间显示 loading 状态，提示"正在为这首诗作画..."
- `frames` 按 index 顺序轮播，每张展示 `duration_ms` 毫秒（默认3000）
- 图片尺寸 `2560x1440`，横版 16:9，CSS 设置 `object-fit: cover`
- `errors` 数组记录某句生成失败的情况，不影响其他句子

---

## 4. 搜索古诗

- 接口路径：GET /poems/search
- 负责人：陈誉文

### 请求参数（Query）

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| keyword | string | 否 | 综合搜索（标题、作者、朝代、诗句、标签） |
| author | string | 否 | 作者筛选 |
| dynasty | string | 否 | 朝代筛选 |
| tag | string | 否 | 标签筛选 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认10 |

请求示例：
```
GET /poems/search?keyword=静夜思
GET /poems/search?author=李白&dynasty=唐
```

成功返回：
```json
{
  "success": true,
  "total": 1,
  "page": 1,
  "page_size": 10,
  "data": [
    {
      "id": "poem_002",
      "title": "静夜思",
      "author": "李白",
      "dynasty": "唐",
      "content_preview": "床前明月光，疑是地上霜。",
      "tags": ["月亮", "思乡", "李白"]
    }
  ]
}
```

---

## 5. 古诗详情

- 接口路径：GET /poems/{id}
- 负责人：陈誉文

请求示例：
```
GET /poems/poem_002
```

成功返回：
```json
{
  "success": true,
  "data": {
    "id": "poem_002",
    "title": "静夜思",
    "author": "李白",
    "dynasty": "唐",
    "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
    "translation": "明亮的月光洒在床前...",
    "tags": ["月亮", "思乡", "李白"]
  }
}
```

---

## 6. 学习记录

- 接口路径：POST /record
- 负责人：陈誉文

请求示例：
```json
{
  "poem_id": "poem_002",
  "user_id": "test_user",
  "duration_seconds": 60
}
```

成功返回：
```json
{
  "success": true,
  "message": "记录成功"
}
```

---

## 7. 学习统计

- 接口路径：GET /record/summary
- 功能：统计用户已学古诗数量、学习记录数、累计学习时长等
- 负责人：陈誉文

请求示例：
```
GET /record/summary?user_id=test_user
```

成功返回：
```json
{
  "success": true,
  "data": {
    "poem_count": 3,
    "record_count": 5,
    "total_duration": 180,
    "poems": [],
    "recent_records": []
  }
}
```

---

## 8. 推荐古诗

- 接口路径：GET /recommend
- 功能：推荐用户未看过的古诗
- 负责人：陈誉文

请求示例：
```
GET /recommend?user_id=test_user&limit=5
```

成功返回：
```json
{
  "success": true,
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

## 9. 拍照识诗

- 接口路径：POST /ocr
- 功能：识别图片中的古诗文字并匹配数据库
- 负责人：陈誉文

请求示例：
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "mode": "text"
}
```

成功返回（匹配到）：
```json
{
  "success": true,
  "recognized_text": "床前明月光疑是地上霜",
  "matched_poem": {
    "id": "poem_002",
    "title": "静夜思",
    "author": "李白",
    "dynasty": "唐",
    "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"]
  }
}
```

---

## 10. 语音朗读

- 接口路径：POST /tts
- 功能：将诗句转换为语音
- 负责人：陈誉文
- 状态：🔧 开发中

请求示例：
```json
{
  "text": "床前明月光，疑是地上霜，举头望明月，低头思故乡"
}
```

成功返回：
```json
{
  "success": true,
  "audio_url": "https://..."
}
```

---

## 通用规范

- 所有接口统一返回 `success` 字段标识成功与否
- 失败时返回 `error` 字段说明原因
- HTTP 状态码：200 成功，400 参数错误，500 服务器错误
- 后端已配置 CORS，允许所有来源跨域（开发环境）

---

## 版本更新记录

| 版本 | 日期 | 更新内容 | 更新人 |
|------|------|---------|--------|
| v1.0 | 2026-05-18 | 初始版本，定义全部接口 | 陈俪姗 |
| v1.1 | 2026-05-23 | 更新 /chat 接口参数，新增 history 字段 | 陈俪姗 |
| v1.2 | 2026-05-27 | 更新 /generate/image 为逐句生成，新增 /record/summary | 陈俪姗 |
