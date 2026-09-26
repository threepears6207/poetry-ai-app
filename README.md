# 诗芽小学堂

诗芽小学堂是一个面向 3—7 岁儿童的 AI 古诗学习应用。

项目把“找诗—看画学诗—和诗人对话—跟读巩固—个性化推荐”连成一个完整流程，并针对低龄儿童提供语音交互和横屏大字界面。

## 当前已实现

- SQLite 结构化儿童古诗库，支持年龄、难度、主题、知识标签和学习状态管理。
- 古诗搜索、详情、千问视觉拍照识诗和风景匹配。
- DeepSeek 规划整首诗的连续分镜，火山方舟 Seedream 4.5 并行生成逐句配图并写入正式缓存。
- DeepSeek 诗人角色对话，根据年龄调整回答方式；千问3-TTS为已出现诗人保留固定声音，并为新诗人自动分配和持久化声音档案。
- 百炼 Fun-ASR Realtime 支持实时语音识别和单句跟读评分，普通古诗范读使用独立语音流程。
- 单句跟读评分、错句立即重读、整首通过后更新巩固进度。
- 基于年龄、已学记录和跟读强项标签的个性化推荐。
- 学习记录、巩固计划、跟读成绩和家长端统计。
- DeepSeek 规划整首诗视频，百炼 Wan3 生成正式视频；前端默认只播放已有缓存，未命中时继续使用逐句配图，不自动提交付费任务。

## 技术结构

| 部分 | 技术 |
|---|---|
| 前端 | uni-app、Vue 3、HBuilderX，主要运行于 Android 横屏 App |
| 后端 | Python 3.11、FastAPI、Uvicorn |
| 数据 | SQLite，含古诗、用户、学习记录、巩固记录和跟读评分 |
| 对话与规划 | DeepSeek `deepseek-flash` |
| 图片理解 | 阿里云百炼 `qwen3-vl-plus` |
| 图片生成 | 火山方舟 `Doubao-Seedream-4.5` |
| 视频生成 | 阿里云百炼 `wan3.0-video-prime` |
| 语音与识别 | 百炼 Fun-ASR Realtime、千问3-TTS、edge-tts |

## 目录

```text
poetry-ai-app/
├─ backend/                  FastAPI 后端、SQLite 数据层和 AI 能力
├─ frontend/shiya-app/       uni-app 前端
├─ docs/                     项目资料
└─ README.md                 项目总览
```

## 快速开始

1. 按 [后端说明](backend/README.md) 安装 Python 3.11 依赖并初始化 SQLite。
2. 在本机 `backend/.env` 中配置 DeepSeek、火山方舟和阿里云百炼密钥；该文件不会提交到 Git。
3. 从 `backend` 目录启动 `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`。
4. 按 [前端说明](frontend/shiya-app/README.md) 将 `utils/api.js` 的 `BASE_URL` 改为当前开发机地址。
5. 在 HBuilderX 中打开 `frontend/shiya-app`，运行 H5 或 Android 真机。

后端启动后可访问：

- `http://127.0.0.1:8000/ping`
- `http://127.0.0.1:8000/docs`

## 当前用户方案

当前演示版本暂未开发注册登录，前后端共用 `test_user` 作为测试用户。孩子选择的年龄层会写入用户记录，学习、跟读、巩固和推荐数据均按 `user_id` 隔离。

视频自动生成默认关闭，日常开发和答辩准备只读取已经验收的正式视频缓存，避免误提交付费任务；需要演示生成能力时再显式打开前端开关。

## 文档

- [前端 README](frontend/shiya-app/README.md)
- [后端 README](backend/README.md)
- [后端 API 补充文档](backend/API.md)
