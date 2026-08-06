# 提醒与家长端接口

对应优化文档“第五部分：陈誉文开发主线”第 4 项“巩固、集章墙与家长端”中的提醒状态与家长端聚合。

## 提醒状态

`GET /reminders/status?user_id=child_001`

```json
{
  "show_practice_prompt": true,
  "practice_prompt_suppressed": false,
  "practice_entry_badge": true,
  "practice_entry_badge_count": 2,
  "pending_review_count": 2
}
```

## 今天先不提醒

`POST /reminders/suppress-today`

```json
{"user_id": "child_001"}
```

只抑制当天弹窗；待温习状态和入口红点不清除，第二天自动恢复提示资格。

## 家长端聚合

`GET /parent/overview?user_id=child_001`

返回：

- `today_learning`：今日诗词、学习次数和时长。
- `pending_review_count`：待温习数量。
- `reading_completion`：朗读完成数量、总数和比例。
- `recent_records`：最近 10 条学习记录。
- `reinforced_poem_count`：已完成规定巩固的诗词数。
