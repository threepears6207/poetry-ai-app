# 端侧图片理解候选诗接口

`POST /poems/candidates` 接收 vivo 端侧模型审核通过后的结构化结果。后端负责查库、文字与场景召回、合并去重和排序；端侧模型不直接决定最终诗目。

## 请求

```json
{
  "content_type": "poem_text",
  "poem": {
    "title": "春晓",
    "author": "孟浩然",
    "dynasty": "唐",
    "content": ["春眠不觉晓", "处处闻啼鸟"],
    "translation": "……"
  },
  "confidence": 0.9,
  "objects": []
}
```

`content_type` 只支持：

- `poem_text`：读取嵌套的 `poem.title`、`poem.author`、`poem.content`；明确且唯一命中时可以只返回 1 首。
- `scene`：读取外层 `objects`，例如 `{"content_type":"scene","poem":null,"objects":["山峰","湖面"],"confidence":0.9}`；返回 2—3 首可靠候选。

后端暂时兼容旧字段 `type`、`poem_text`、`recognized_text`、`recognized_title`、`recognized_author`、`scene`、`scene_tags`、`season`、`mood`，但新端侧不再发送 `mixed`。

## 成功响应

```json
{
  "success": true,
  "status": "ok",
  "error_code": null,
  "poems": [
    {
      "poem_id": "poem_001",
      "id": "poem_001",
      "title": "春晓",
      "author": "孟浩然",
      "dynasty": "唐",
      "cover_url": "/static/images/poems/poem_001/frame_0.jpg",
      "age_level": "age_3_4",
      "difficulty": 1,
      "learned_state": null
    }
  ]
}
```

候选、搜索和推荐接口共享同一组 `PoemCard` 核心字段。`id` 仅用于兼容旧前端，
新接入统一以 `poem_id` 作为详情和学习页跳转主键。

儿童端只消费 `poems[]`。联调时可传 `debug=true`，诗卡会临时附带 `match_score`、`text_score`、`scene_score` 和 `match_sources`。

## 云端补全衔接

`poem_text` 会先检索现有诗库：

1. 本地明确命中时直接返回 1 首，不调用云端。
2. 本地无可靠命中时，候选接口调用 `complete_poem_from_terminal_analysis` 补齐诗歌资料。
3. 补全结果继续经过 `/poems/resolve` 相同的字段校验、正文去重和正式入库逻辑；已有诗复用原 ID，新诗使用 `poem_301+`。
4. 成功响应仍只返回统一 `PoemCard`，并附带 `completion_source="cloud"` 供联调判断。
5. 云端失败返回 `status="retake"` 与 `error_code="cloud_completion_failed"`；补全结果未通过诗库质量门禁时返回 `cloud_completion_rejected`。

`scene` 只做现有诗库的风景候选检索，不会调用云端古诗补全。

## 重拍响应

```json
{
  "success": false,
  "status": "retake",
  "error_code": "low_confidence",
  "poems": []
}
```

重拍原因包括：`insufficient_input`、`low_confidence`、`no_reliable_match`。后端不会在缺少可靠证据时强行推荐。
