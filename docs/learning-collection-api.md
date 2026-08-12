# 学习、巩固与集章墙状态接口

对应优化文档“第五部分：陈誉文开发主线”第 4 项“巩固、集章墙与家长端”中的学习状态闭环。

## 状态规则

1. `POST /record` 记录学习后，创建待巩固记录，诗卡为 `gray`。
2. 分镜朗读完成后提交 `reading`。
3. 诗句连线完成后提交 `connection`。
4. 两项都完成时，服务端将 `collection_state` 改为 `color`，并把 `flower_count` 增加 1。
5. 重复提交同一结果不会重复增加小红花。
6. 首次解锁后按 1/3/7 天复习节奏推进；到达 `next_review_date` 后自动开启新一轮 `reading + connection`。
7. 每轮两项都完成才增加 `practice_count`，第 3 轮完成后状态改为 `已掌握`。
8. 后续复习不会重复增加小红花，彩卡不会退回灰色；未到复习日期的重复提交不会推进轮次。

## 提交分项进度

`POST /consolidation/progress`

```json
{
  "user_id": "child_001",
  "poem_id": "poem_001",
  "activity": "reading",
  "completed": true
}
```

`activity` 为 `reading` 或 `connection`。

```json
{
  "success": true,
  "just_unlocked": false,
  "data": {
    "poem_id": "poem_001",
    "reading_completed": true,
    "connection_completed": false,
    "collection_state": "gray",
    "flower_count": 0
  }
}
```

旧接口 `POST /consolidation/result` 继续可用；`passed=true` 会按“朗读和连线均完成”处理。

复习轮次开始后，响应中的 `reading_completed` 和 `connection_completed` 会按本轮进度重新计算，`collection_state` 始终保持 `color`。

## 集章墙

`GET /collection/wall?user_id=child_001`

接口只返回存在学习记录的诗，不返回未学诗：

```json
{
  "success": true,
  "total": 1,
  "color_count": 1,
  "flower_count": 1,
  "poems": [
    {
      "poem_id": "poem_001",
      "title": "春晓",
      "collection_state": "color",
      "flower_count": 1
    }
  ]
}
```
