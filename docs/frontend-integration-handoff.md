# 诗芽小学堂前端接口交接单（陈誉文模块）

交接对象：吴美昕（前端）  
后端模块负责人：陈誉文  
接口基地址：由联调环境提供，例如 `http://<host>:8000`

## 1. 前端统一诗卡字段

所有新版列表与候选接口优先读取 `poems[]`。诗卡至少使用：

```ts
interface PoemCard {
  poem_id: string
  title: string
  author: string
  dynasty?: string
  cover_url?: string | null
  age_level?: 'age_3_4' | 'age_5_7'
  difficulty?: number
  collection_state?: 'gray' | 'color'
  flower_count?: number
}
```

`match_score`、`score_components`、`source`、`verification_status` 等是联调字段，不在儿童页面展示。

## 2. 页面与接口对应关系

| 前端页面/动作 | 接口 | 方法 | 主要返回 |
|---|---|---|---|
| 今天学什么 | `/recommend/today` | GET | `poem`、`poems[]` |
| 换一首 | `/recommend/today?exclude_poem_id=<当前ID>` | GET | 下一首 `poem` |
| 找古诗推荐列表 | `/recommend?limit=10` | GET | `poems[]` |
| 搜索古诗 | `/poems/search` | GET | `data[]` |
| 古诗详情 | `/poems/{poem_id}` | GET | `data` |
| 拍课本/手写/风景/图文混合 | `/poems/candidates` | POST | `status`、`poems[]` |
| 打开画卷并完成一次学习 | `/record` | POST | 学习记录、初始巩固状态 |
| 练一练列表 | `/consolidation/list` | GET | `data[]` |
| 提交分镜朗读完成 | `/consolidation/progress` | POST | 最新状态 |
| 提交诗句连线完成 | `/consolidation/progress` | POST | 最新状态 |
| 集章墙 | `/collection/wall` | GET | 只含已学诗的 `poems[]` |
| 练习弹窗与入口红点 | `/reminders/status` | GET | `show_practice_prompt`、`practice_entry_badge` |
| 今天先不提醒 | `/reminders/suppress-today` | POST | 当天提醒状态 |
| 家长端总览 | `/parent/overview` | GET | 今日学习、待温习、朗读完成度、近期记录 |
| 学习概览 | `/record/summary` | GET | 已学诗、时长、近期记录 |

所有用户相关请求都传同一个稳定的 `user_id`，不要在不同页面使用不同临时 ID。

## 3. 今天学什么与换一首

```http
GET /recommend/today?user_id=child_001&age_level=age_3_4
```

```json
{
  "success": true,
  "poem": {
    "poem_id": "poem_001",
    "title": "春晓",
    "author": "孟浩然",
    "difficulty": 1
  },
  "poems": [{"poem_id": "poem_001", "title": "春晓"}]
}
```

换一首：

```http
GET /recommend/today?user_id=child_001&age_level=age_3_4&exclude_poem_id=poem_001
```

## 4. 找古诗

推荐列表：

```http
GET /recommend?user_id=child_001&age_level=age_3_4&limit=10
```

搜索：

```http
GET /poems/search?keyword=月亮&page=1&page_size=10
```

详情：

```http
GET /poems/poem_002
```

详情接口兼容去重前的旧 ID；例如请求重复 ID 时，`data.poem_id` 返回规范 ID，`data.requested_poem_id` 保留原请求 ID。

## 5. 拍照识诗候选

```http
POST /poems/candidates
Content-Type: application/json
```

```json
{
  "content_type": "mixed",
  "recognized_text": "处处闻啼鸟",
  "recognized_title": "",
  "recognized_author": "",
  "objects": ["花", "鸟"],
  "scene_tags": ["春景"],
  "season": "spring",
  "mood": "happy",
  "confidence": 0.9,
  "age_level": "age_3_4",
  "limit": 3
}
```

成功时：`status="ok"`，渲染 `poems[]` 的 2-3 张候选卡。不要展示推荐理由。

失败时：

```json
{
  "success": false,
  "status": "retake",
  "error_code": "low_confidence",
  "poems": []
}
```

`insufficient_input`、`low_confidence`、`no_reliable_match` 都进入“请重新拍摄”页面。

## 6. 学习、练一练和集章墙

完成一次学习：

```http
POST /record
```

```json
{
  "user_id": "child_001",
  "poem_id": "poem_001",
  "duration_seconds": 120
}
```

提交分镜朗读：

```json
{
  "user_id": "child_001",
  "poem_id": "poem_001",
  "activity": "reading",
  "completed": true
}
```

提交诗句连线使用相同接口，把 `activity` 改为 `connection`。

只有两项均完成时，后端返回：

```json
{
  "just_unlocked": true,
  "data": {
    "reading_completed": true,
    "connection_completed": true,
    "collection_state": "color",
    "flower_count": 1
  }
}
```

集章墙：

```http
GET /collection/wall?user_id=child_001
```

只展示返回的 `poems[]`；不要在前端自行把未学诗加入集章墙，也不要自行计算灰卡、彩卡或小红花。

## 7. 提醒、入口红点与家长端

查询提醒：

```http
GET /reminders/status?user_id=child_001
```

- `show_practice_prompt=true`：弹出“练一练”提示。
- `practice_entry_badge=true`：练一练入口显示红点。
- 用户关闭当天弹窗后，红点仍按该字段展示，不能跟随弹窗一起清除。

今天先不提醒：

```http
POST /reminders/suppress-today
Content-Type: application/json

{"user_id": "child_001"}
```

家长端：

```http
GET /parent/overview?user_id=child_001
```

使用 `today_learning`、`pending_review_count`、`reading_completion` 和 `recent_records` 四个区块渲染。朗读数据名称统一展示为“朗读完成度”，不要写成专业发音评分。

## 8. 后端内部接口

`POST /poems/resolve` 用于端侧/云端补全结果进入诗库后的核验、复用和扩展库入库，通常由后端适配层调用，儿童前端不直接调用。

## 9. 联调检查清单

- `user_id` 在所有页面保持一致。
- 所有跳转使用 `poem_id`，不要用标题作为主键。
- 拍照失败根据 `status/error_code` 进入重拍，不使用空候选强行跳学习页。
- “换一首”必须传当前 `poem_id`。
- 练一练只使用后端列表。
- 集章墙只展示 `/collection/wall` 返回的已学诗。
- 儿童页面不显示内部评分、匹配来源或长篇推荐理由。
