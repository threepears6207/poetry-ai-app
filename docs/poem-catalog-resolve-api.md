# 诗库核验与复用接口

`POST /poems/resolve` 接收端侧识别结果和云端已经核验、补全的诗词候选。诗库服务依次执行：

1. 规范化正文并计算 SHA-256 内容哈希。
2. 优先按正文哈希复用已有诗；其次按标题、作者、正文复用。
3. 同标题、作者但正文冲突时拒绝自动覆盖。
4. `/poems/resolve` 只接收云端已经核验、补全的候选；调用方不再传 `verification_status` 和 `source_name`。后端校验正文与元数据后，在库内固定记录核验状态和来源。
5. 新增诗统一从 `poem_301` 起按当前最大编号递增，不再生成 `ext_xxx`，也不再区分 extension 库。
6. 无论复用还是新入库，都通过统一的 `poems[]` 返回正式 `poem_id`。

## 请求示例

```json
{
  "recognized_text": "床前明月光，疑是地上霜",
  "auto_insert": true,
  "candidates": [
    {
      "title": "静夜思",
      "author": "李白",
      "dynasty": "唐",
      "content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
      "age_level": "age_3_4",
      "age_range": "3-4岁",
      "difficulty": 1,
      "tags": ["月亮", "思乡"],
      "theme_tags": ["夜晚", "思乡"],
      "knowledge_tags": ["画面理解"],
      "source_url": "https://example.org/poem/jing-ye-si",
      "source_version": "2026-08-06"
    }
  ]
}
```

## 成功响应要点

```json
{
  "success": true,
  "poems": [
    {
      "poem_id": "poem_002",
      "title": "静夜思",
      "author": "李白",
      "resolution": "reused",
      "match_type": "content_hash"
    }
  ],
  "rejected": []
}
```

`resolution` 为 `reused` 或 `inserted`。例如当前最大正式编号为 `poem_300` 时，下一首核验通过的新诗返回 `poem_301`。`rejected` 仅用于后端联调和日志；儿童端只消费 `poems[]`。

`source_name` 和 `verification_status` 仍保留为数据库内部审计字段：新增诗分别写入 `cloud_verified_poem` 和 `verified`，但不再出现在 resolve 请求或响应中。
