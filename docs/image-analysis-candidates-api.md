# 端侧图片理解候选诗接口

`POST /poems/candidates` 接收 vivo 端侧模型审核通过后的结构化结果。后端负责查库、文字与场景召回、合并去重和排序；端侧模型不直接决定最终诗目。

## 请求

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

`content_type` 支持：

- `text_poem`：课本印刷古诗。
- `handwritten`：手写古诗或诗句。
- `scene`：自然风景。
- `mixed`：同时包含文字和风景。

## 成功响应

```json
{
  "success": true,
  "status": "ok",
  "error_code": null,
  "poems": [
    {
      "poem_id": "poem_001",
      "title": "春晓",
      "author": "孟浩然",
      "dynasty": "唐",
      "cover_url": "/static/images/poems/poem_001/frame_0.jpg",
      "age_level": "age_3_4",
      "difficulty": 1
    }
  ]
}
```

儿童端只消费 `poems[]`。联调时可传 `debug=true`，诗卡会临时附带 `match_score`、`text_score`、`scene_score` 和 `match_sources`。

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
