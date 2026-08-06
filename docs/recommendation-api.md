# 个性化推荐接口

## 今天学什么

`GET /recommend/today?user_id=child_001&age_level=age_3_4`

返回一首当前推荐，同时保留统一的 `poems[]`：

```json
{
  "success": true,
  "poem": {"poem_id": "poem_001", "title": "春晓"},
  "poems": [{"poem_id": "poem_001", "title": "春晓"}],
  "user_id": "child_001",
  "age_level": "age_3_4"
}
```

“换一首”时传当前诗 ID：

`GET /recommend/today?user_id=child_001&exclude_poem_id=poem_001`

## 推荐列表

`GET /recommend?user_id=child_001&limit=5`

排序依次考虑：

1. 年龄匹配和内容可推荐资格。
2. 到期温习或低于 75 分的薄弱诗。
3. 最近学习中反复出现的意象偏好。
4. 相对当前能力的小步难度递进。
5. 对刚学过的同主题和同作者进行降权。

列表接口同时返回 `poems`、`data` 和 `recommendations`，三者内容相同；`data`、`recommendations` 用于兼容原前端。传 `debug=true` 可查看 `score_components`。
