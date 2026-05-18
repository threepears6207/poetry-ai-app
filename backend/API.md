# 诗芽小学堂 API 接口文档

> 文档版本：v1.0  
> 更新时间：2026-05-18  
> 负责人：陈俪姗  
> 后端基础URL：http://localhost:8000（开发环境）

---

## 接口列表

| 接口名称 | 请求方式 | 路径 | 负责人 |
|---------|---------|------|--------|
| 健康检查 | GET | /ping | 陈俪姗 |
| AI诗人对话 | POST | /chat | 陈俪姗 |
| 搜索古诗 | GET | /poems/search | 陈誉文 |
| 古诗详情 | GET | /poems/{id} | 陈誉文 |
| 学习记录 | POST | /record | 陈誉文 |
| 推荐古诗 | GET | /recommend | 陈誉文 |
| AI配图生成 | POST | /generate/image | 陈俪姗 |
| 语音朗读 | POST | /tts | 陈誉文 |
| 拍照识诗 | POST | /ocr | 陈誉文 |

---

## 1. 健康检查

### 基本信息
- 接口路径：GET /ping
- 功能描述：检查后端服务是否正常运行
- 负责人：陈俪姗

### 请求参数
无

### 返回参数

成功返回：
```json
{
  "message": "pong",
  "vivo_app_id": "your_app_id",
  "has_api_key": true
}
```

---

## 2. AI诗人对话

### 基本信息
- 接口路径：POST /chat
- 功能描述：用户向AI诗人提问，AI以古代诗人的语气回答
- 负责人：陈俪姗
- AI能力：蓝心大模型API

### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| message | string | 是 | 用户发送的消息 | "李白你好，能给我讲讲静夜思吗？" |

请求示例：
```json
{
  "message": "李白你好，能给我讲讲静夜思吗？"
}
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "reply": "少年郎，此诗乃吾于长安时所作。那夜月光如霜，洒在床前..."
}
```

失败返回：
```json
{
  "success": false,
  "error": "API调用失败"
}
```

---

## 3. 搜索古诗

### 基本信息
- 接口路径：GET /poems/search
- 功能描述：根据关键词搜索古诗（支持按标题、作者、内容搜索）
- 负责人：陈誉文
- 数据来源：本地数据库（chinese-poetry 数据集）

### 请求参数（Query参数）

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| keyword | string | 是 | 搜索关键词 | "静夜思" 或 "李白" |
| page | int | 否 | 页码，默认1 | 1 |
| page_size | int | 否 | 每页数量，默认10 | 10 |

请求示例：
```
GET /poems/search?keyword=静夜思&page=1&page_size=10
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "total": 1,
  "data": [
    {
      "id": "poem_001",
      "title": "静夜思",
      "author": "李白",
      "dynasty": "唐",
      "content_preview": "床前明月光，疑是地上霜。"
    }
  ]
}
```

失败返回：
```json
{
  "success": false,
  "error": "搜索失败"
}
```

---

## 4. 古诗详情

### 基本信息
- 接口路径：GET /poems/{id}
- 功能描述：根据诗词ID获取完整信息（标题、作者、朝代、诗句内容）
- 负责人：陈誉文
- 数据来源：本地数据库

### 请求参数（路径参数）

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| id | string | 是 | 诗词唯一ID | "poem_001" |

请求示例：
```
GET /poems/poem_001
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "data": {
    "id": "poem_001",
    "title": "静夜思",
    "author": "李白",
    "dynasty": "唐",
    "content": [
      "床前明月光",
      "疑是地上霜",
      "举头望明月",
      "低头思故乡"
    ]
  }
}
```

失败返回：
```json
{
  "success": false,
  "error": "诗词不存在"
}
```

---

## 5. 学习记录

### 基本信息
- 接口路径：POST /record
- 功能描述：记录用户查看过的古诗（用于推荐和学习历史）
- 负责人：陈誉文

### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| poem_id | string | 是 | 诗词ID | "poem_001" |
| user_id | string | 是 | 用户ID | "user_123" |

请求示例：
```json
{
  "poem_id": "poem_001",
  "user_id": "user_123"
}
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "message": "记录成功"
}
```

失败返回：
```json
{
  "success": false,
  "error": "记录失败"
}
```

---

## 6. 推荐古诗

### 基本信息
- 接口路径：GET /recommend
- 功能描述：推荐用户未看过的古诗
- 负责人：陈誉文

### 请求参数（Query参数）

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| user_id | string | 是 | 用户ID | "user_123" |
| limit | int | 否 | 返回数量，默认5 | 5 |

请求示例：
```
GET /recommend?user_id=user_123&limit=5
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "data": [
    {
      "id": "poem_002",
      "title": "望庐山瀑布",
      "author": "李白",
      "dynasty": "唐",
      "content_preview": "日照香炉生紫烟，遥看瀑布挂前川。"
    }
  ]
}
```

失败返回：
```json
{
  "success": false,
  "error": "推荐失败"
}
```

---

## 7. AI配图生成

### 基本信息
- 接口路径：POST /generate/image
- 功能描述：根据诗句内容生成AI配图
- 负责人：陈俪姗
- AI能力：蓝心图片生成API

### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| poem_id | string | 是 | 诗词ID | "poem_001" |
| content | string | 是 | 诗句内容 | "床前明月光，疑是地上霜" |

请求示例：
```json
{
  "poem_id": "poem_001",
  "content": "床前明月光，疑是地上霜"
}
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "image_url": "https://example.com/images/poem_001.png"
}
```

失败返回：
```json
{
  "success": false,
  "error": "配图生成失败"
}
```

---

## 8. 语音朗读

### 基本信息
- 接口路径：POST /tts
- 功能描述：将诗句内容转换为语音朗读
- 负责人：陈誉文
- AI能力：蓝心音频生成API或第三方TTS服务

### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| text | string | 是 | 要朗读的文本内容 | "床前明月光，疑是地上霜，举头望明月，低头思故乡" |

请求示例：
```json
{
  "text": "床前明月光，疑是地上霜，举头望明月，低头思故乡"
}
```

### 返回参数

成功返回：
```json
{
  "success": true,
  "audio_url": "https://example.com/audio/poem_001.mp3"
}
```

失败返回：
```json
{
  "success": false,
  "error": "语音生成失败"
}
```

---

## 9. 拍照识诗

### 基本信息
- 接口路径：POST /ocr
- 功能描述：识别图片中的古诗文字，并匹配数据库中的古诗
- 负责人：陈誉文
- AI能力：腾讯云OCR或百度OCR API

### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| image | string | 是 | 图片的Base64编码字符串 | "data:image/jpeg;base64,/9j/4AAQ..." |

请求示例：
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."
}
```

### 返回参数

成功返回（识别到匹配的古诗）：
```json
{
  "success": true,
  "recognized_text": "床前明月光疑是地上霜",
  "matched_poem": {
    "id": "poem_001",
    "title": "静夜思",
    "author": "李白",
    "dynasty": "唐",
    "content": [
      "床前明月光",
      "疑是地上霜",
      "举头望明月",
      "低头思故乡"
    ]
  }
}
```

成功返回（识别到文字但未匹配到古诗）：
```json
{
  "success": true,
  "recognized_text": "识别到的文字内容",
  "matched_poem": null,
  "message": "未找到匹配的古诗"
}
```

失败返回：
```json
{
  "success": false,
  "error": "图片识别失败"
}
```

---

## 通用规范

### 1. 响应格式统一
所有接口返回格式保持一致：
```json
{
  "success": true/false,
  "data": {},
  "error": "错误信息（仅失败时）"
}
```

### 2. HTTP状态码
- 200：请求成功
- 400：参数错误
- 500：服务器内部错误

### 3. CORS跨域
后端已配置允许所有来源的跨域请求（开发环境）

### 4. 错误处理
所有接口需要捕获异常并返回友好的错误信息，不要暴露堆栈信息

### 5. 数据来源说明
- 古诗数据：使用GitHub开源的chinese-poetry数据集
- AI对话：蓝心大模型API
- AI配图：蓝心图片生成API
- 语音朗读：蓝心音频生成API或第三方TTS
- OCR识别：蓝心的通用OCR或腾讯云OCR或百度OCR

---

## 版本更新记录

| 版本 | 日期 | 更新内容 | 更新人 |
|------|------|---------|--------|
| v1.0 | 2026-05-18 | 初始版本，定义全部9个接口 | 陈俪姗 |

---

