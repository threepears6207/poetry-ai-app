# 诗芽小学堂

诗芽小学堂是一个面向 3—7 岁儿童的 AI 古诗学习应用，参赛项目为中国高校计算机大赛 AIGC 创新赛。

项目把“找诗—看画学诗—和诗人对话—跟读巩固—个性化推荐”连成一个完整流程，并针对低龄儿童提供语音交互和横屏大字界面。

## 当前已实现

- 150 首儿童古诗库：3—4 岁 50 首，5—7 岁 100 首。
- 古诗搜索、详情、拍照 OCR 识诗和风景匹配。
- AI 连续分镜配图，支持并行生成、逐帧展示和本地缓存。
- 诗人角色对话，根据年龄调整回答方式，并使用不同诗人声音播放回复。
- 单句跟读评分、错句立即重读、整首通过后更新巩固进度。
- 基于年龄、已学记录和跟读强项标签的个性化推荐。
- 学习记录、巩固计划、跟读成绩和家长端统计。
- 基于 vivo 平台的整首诗文生视频实验接口。

## 技术结构

| 部分 | 技术 |
|---|---|
| 前端 | uni-app、Vue 3、HBuilderX，主要运行于 Android 横屏 App |
| 后端 | Python 3.11、FastAPI、Uvicorn |
| 数据 | SQLite，含古诗、用户、学习记录、巩固记录和跟读评分 |
| AI 能力 | vivo 大模型、图像生成、WebSocket TTS、视频生成实验 |
| 语音与识别 | FunASR、edge-tts、百度 OCR、百度图像识别 |

## 目录

```text
poetry-ai-app/
├─ backend/                  FastAPI 后端、SQLite 数据层和 AI 能力
├─ frontend/shiya-app/       uni-app 前端
├─ docs/                     项目资料
└─ README.md                 项目总览
```

## 快速开始

1. 按 [后端说明](backend/README.md) 安装 Python 3.11 依赖、初始化 SQLite 并启动 `8000` 端口。
2. 按 [前端说明](frontend/shiya-app/README.md) 修改 `utils/api.js` 中的后端地址。
3. 在 HBuilderX 中打开 `frontend/shiya-app`，运行 H5 或 Android 真机。

后端启动后可访问：

- `http://127.0.0.1:8000/ping`
- `http://127.0.0.1:8000/docs`

## 当前用户方案

比赛版本暂未开发注册登录，前后端共用 `test_user` 作为测试用户。孩子选择的年龄层会写入用户记录，学习、跟读、巩固和推荐数据均按 `user_id` 隔离。

## 文档

- [前端 README](frontend/shiya-app/README.md)
- [后端 README](backend/README.md)
- [后端 API 补充文档](backend/API.md)
