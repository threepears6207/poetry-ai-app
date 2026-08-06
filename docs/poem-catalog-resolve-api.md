# 诗库核验与复用接口

`POST /poems/resolve` 接收端侧识别结果和云端已经核验、补全的诗词候选。诗库服务依次执行：

1. 规范化正文并计算 SHA-256 内容哈希。
2. 优先按正文哈希复用已有诗；其次按标题、作者、正文复用。
3. 同标题、作者但正文冲突时拒绝自动覆盖。
4. 仅当 `verification_status=verified`、正文完整且提供 `source_name` 时，自动写入扩展库。
5. 无论复用还是新入库，都通过统一的 `poems[]` 返回正式 `poem_id`。

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
      "source_name": "云端核验使用的可信诗词资料库",
      "source_url": "https://example.org/poem/jing-ye-si",
      "source_version": "2026-08-06",
      "verification_status": "verified"
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

`resolution` 为 `reused` 或 `inserted_extension`。`rejected` 仅用于后端联调和日志；儿童端只消费 `poems[]`。
