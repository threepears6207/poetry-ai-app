# 诗芽小学堂后端

后端使用 FastAPI，负责古诗数据、学习记录、巩固计划、个性化推荐、OCR、语音识别、诗人对话、语音合成、AI 配图和视频生成实验。

## 最新进展（2026-08-06）

- 已完成诗库结构化、来源追踪、正文哈希去重、标签规范化和可信内容筛选。
- 已新增图片理解结果候选检索，可综合文字、景物、季节和氛围返回 2—3 首候选诗。
- 已升级推荐排序，综合适龄与内容完整、待温习/薄弱项、近期偏好、难度递进和内容多样性。
- 已完成学习巩固闭环：分镜朗读和诗句连线均完成后，集章墙诗卡由灰色变彩色并增加小红花。
- 已提供当日练习提醒、暂停当日提醒以及家长端学习聚合数据。
- 陈誉文负责范围的专项自动化测试共 27 项，当前全部通过。

## 当前数据状态

- 正式读写已切换到 SQLite，默认文件为 `data/poetry_ai.db`。
- 当前本地 SQLite 古诗库共 218 首；核心库和扩展候选通过 `library_scope`、`verification_status`、`content_complete` 和 `recommend_eligible` 区分。
- 诗歌已补充来源、版本、年龄段、难度、主题标签、知识标签、正文哈希、完整状态和推荐资格等结构化字段。
- 主要数据表：`poems`、`users`、`learning_records`、`consolidations`、`reading_scores`、`daily_reminder_settings`。
- `data/poems.json`、`records.json`、`consolidations.json` 仅作为历史源数据/迁移输入，正式接口不再直接读写它们。
- SQLite 运行库已加入 `.gitignore`，新环境需自行初始化。

## 环境

- Windows
- Python 3.11
- pip
- 可访问 vivo 蓝心开放平台、百度 AI 开放平台和 edge-tts 服务的网络

## 安装

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` 已包含 FastAPI、Uvicorn、edge-tts、websocket-client 和 websockets 等运行依赖。实时语音识别通过 vivo WebSocket 服务完成，不再下载或加载本地 FunASR 模型。

## 环境变量

在 `backend/.env` 中配置：

```env
# vivo 大模型、生图、TTS 和视频生成
VIVO_APP_KEY=你的APIKey
VIVO_APP_ID=你的APPID

# 百度文字 OCR
BAIDU_OCR_API_KEY=你的OCR_API_Key
BAIDU_OCR_SECRET_KEY=你的OCR_Secret_Key

# 百度图像识别，用于风景图匹配古诗
BAIDU_IMAGE_API_KEY=你的图像识别API_Key
BAIDU_IMAGE_SECRET_KEY=你的图像识别Secret_Key

# 可选：改用其他 SQLite 文件
POETRY_DB_PATH=data/poetry_ai.db
```

`VIVO_APP_KEY` 未配置时，古诗查询、学习记录和 SQLite 接口仍可运行，但对话、生图、vivo TTS 和视频能力不可用。

## 初始化数据库

新环境首次运行：

```powershell
cd backend
python scripts/init_database.py
python scripts/import_poems_to_db.py
```

第一条命令根据 `schema.sql` 建表，第二条命令将候选目录导入 SQLite。导入过程会规范化正文和标签、计算正文哈希并根据可信来源与字段完整度设置推荐资格。

如需用候选文件同步更新已存在的诗：

```powershell
python scripts/import_poems_to_db.py --sync-existing
```

历史 JSON 学习记录迁移前可先预检，确认后再写入：

```powershell
python scripts/migrate_json_data_to_db.py
python scripts/migrate_json_data_to_db.py --apply
```

## 启动

```powershell
cd backend
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
uvicorn main:app --reload
```

手机真机联调：

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后：

- 健康检查：`http://127.0.0.1:8000/ping`
- Swagger：`http://127.0.0.1:8000/docs`
- 静态资源：`http://127.0.0.1:8000/static/...`

## 核心业务流程

### 学习记录

`POST /record` 写入一次学习时长，并为该用户/古诗自动创建巩固记录。家长端通过 `GET /record/summary` 获取已学数量、总时长和最近记录。

### 单句跟读与巩固

- `POST /asr/score` 只评当前单句，返回 `score`、`stars`、`message`、`passed`。
- `passed=false` 不代表整次巩固失败，前端应立即重读当前句。
- 整首全部通过后，前端调用一次 `POST /consolidation/result`。
- 第 1 次通过：已巩固，1 天后复习；第 2 次：已巩固，3 天后复习；第 3 次及以后：已掌握，7 天后复习。
- 兼容旧前端的 `passed=false`：不增加次数、不改变状态，并允许当天继续尝试。

### 个性化推荐

1. 先筛选年龄匹配、内容完整且允许推荐的古诗。
2. 优先安排待温习、待巩固或薄弱项目。
3. 结合近期喜欢的主题、意象和阅读画像。
4. 按难度递进，并对连续同类内容施加多样性约束。
5. `GET /recommend/today` 返回当前推荐；`exclude_poem_id` 可用于“换一首”。

### 图片候选与诗库解析

- `POST /poems/candidates` 接收结构化图片理解结果，综合 `recognized_text`、`objects`、`season`、`mood` 和 `confidence` 检索诗库。
- 文字场景优先按诗句匹配，风景场景按标签匹配，图文混合场景合并结果后去重排序。
- 低置信度或无可靠结果时返回重新拍摄状态，不强行推荐。
- `POST /poems/resolve` 只解析和返回可信候选；未经核验的未知文本不会直接写入正式诗库。

### 学习巩固、集章墙和提醒

- `POST /consolidation/progress` 分别记录 `reading` 和 `connection` 两类练习进度。
- 两项均完成后，`collection_state` 从 `gray` 变为 `color`，首次解锁增加 `flower_count`。
- `GET /collection/wall` 只返回已学诗，并由服务端给出灰卡、彩卡和小红花状态。
- `GET /reminders/status` 返回当天是否显示练习提醒；`POST /reminders/suppress-today` 仅暂停当天提醒，次日恢复资格。
- `GET /parent/overview` 聚合今日学习、待温习数量、练习完成情况和近期学习记录。

### 诗人对话与语音

- `/chat` 使用年龄分层提示词和诗人性格设定生成回复。
- 回复会清理思考标签、括号动作描写等不适合直接呈现给儿童的内容。
- 新前端使用 `include_audio=false` 先获取文字，再调用 `/chat/voice-preview` 生成语音，降低回答等待感。
- vivo WebSocket TTS 失败时使用 edge-tts 降级；语音失败不影响文字回复。

### AI 配图

- `POST /generate/image` 是兼容旧前端的同步接口。
- 正式前端使用 `POST /generate/image/start` 开启任务，再通过 `GET /generate/image/status/{task_id}` 获取进度和已完成分镜。
- 图片保持原有高质量 prompt，最多 4 帧并行调用，单帧完成后可立即返回。
- 成功结果保存到 `static/images/poems/{poem_id}/` 和 `static/poem_images_cache.json`。

### 视频生成实验

`POST /generate/video` 提交整首诗的文生视频任务，`GET /generate/video/{task_id}` 查询进度并在成功后下载 MP4。

调试 prompt 时应使用 `dry_run=true`，此时只返回分镜和 prompt，不提交真实生成任务，不消耗视频额度。该功能目前为独立实验，前端正式学习流程仍使用图片分镜。

## 接口总览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务状态 |
| GET | `/ping` | 健康检查和 vivo 配置状态 |
| GET | `/poems/search` | 标题、作者、朝代、诗句、标签搜索与分页 |
| GET | `/poems/{poem_id}` | 古诗详情 |
| POST | `/poems/candidates` | 根据文字、景物、季节和氛围返回候选诗卡 |
| POST | `/poems/resolve` | 解析可信候选诗，不自动写入未知内容 |
| POST | `/record` | 写入学习记录并建立巩固记录 |
| GET | `/record` | 用户学习记录 |
| GET | `/record/summary` | 家长端学习统计 |
| POST | `/profile/reading-score` | 保存整首跟读平均分 |
| GET | `/profile/{user_id}` | 用户标签分数和强项标签 |
| GET | `/recommend` | 年龄 + 未学 + 强项标签推荐 |
| GET | `/recommend/today` | 今天学什么及换一首推荐 |
| POST | `/consolidation/progress` | 写入朗读或连线的分阶段进度 |
| GET | `/collection/wall` | 已学诗集章墙状态 |
| GET | `/consolidation/list` | 巩固列表和统计 |
| GET | `/consolidation/status/{poem_id}` | 单首巩固状态 |
| POST | `/consolidation/result` | 整首通过后更新复习计划 |
| GET | `/reminders/status` | 当日练习提醒状态 |
| POST | `/reminders/suppress-today` | 今天先不提醒 |
| GET | `/parent/overview` | 家长端学习聚合数据 |
| POST | `/ocr` | 文字 OCR 识诗或风景匹配 |
| POST | `/asr` | 语音转文字 |
| POST | `/asr/score` | 当前单句跟读评分 |
| POST | `/tts` | 古诗范读 MP3 |
| POST | `/chat` | AI 诗人对话 |
| POST | `/chat/voice-preview` | 按诗人声音生成语音 |
| GET | `/chat/voice-profile/{poet_name}` | 查询诗人声音档案 |
| POST | `/generate/image` | 兼容用同步配图 |
| POST | `/generate/image/start` | 开启渐进式配图 |
| GET | `/generate/image/status/{task_id}` | 配图任务进度 |
| POST | `/generate/poet_avatar` | 诗人形象生成 |
| POST | `/generate/video` | 提交视频生成实验任务 |
| GET | `/generate/video/{task_id}` | 查询视频任务 |

具体入参和实时返回结构以 Swagger `/docs` 为准。

## 主要文件

| 文件/目录 | 说明 |
|---|---|
| `main.py` | FastAPI 入口、CORS、静态目录和路由注册 |
| `database.py` / `schema.sql` | SQLite 连接、WAL 配置和表结构 |
| `poems.py` | 古诗搜索与详情 |
| `poem_catalog.py` | 可信候选解析、规范化与去重 |
| `candidate_search.py` | 图片理解结果的文字/风景候选检索 |
| `tag_rules.py` | 主题和知识标签规范化规则 |
| `record.py` | 学习记录与家长统计 |
| `consolidation.py` | 分阶段练习、集章状态和 1/3/7 天复习节奏 |
| `learning_dashboard.py` | 当日提醒与家长端聚合数据 |
| `recommend.py` | 适龄、巩固优先、偏好、难度和多样性推荐 |
| `ocr.py` | 百度 OCR、图像识别和 SQLite 古诗匹配 |
| `asr.py` | vivo 实时语音识别、流式 WebSocket 转发和单句评分 |
| `chat.py` / `poet_voice.py` / `vivo_tts.py` | 诗人对话、声音档案、vivo TTS 和降级 |
| `generate.py` | 分镜规划、并行生图、渐进任务和图片缓存 |
| `video_generate.py` | 整首古诗文生视频实验 |
| `data_sources/` | 150 首古诗源数据、译文和标签质检报告 |
| `scripts/` | 建库、导入、迁移、元数据生成与审核脚本 |
| `static/` | 已生成的诗歌图片、诗人头像、音频和缓存 |
| `test_result/` | 后端测试脚本；运行结果文本已忽略 |

## 测试

陈誉文负责范围的专项测试：

```powershell
cd backend
$env:PYTHONPATH=(Get-Location).Path
python -m pytest tests -q
```

当前基线结果：`27 passed`。

先启动后端，再在另一个终端运行：

```powershell
cd backend
python test_result/test_api.py
python test_result/test_chat.py
python test_result/test_generate.py
```

`test_api.py` 会调用部分写入接口，测试后的记录会保存在本地 SQLite 中。

## Git 与运行文件

以下内容不应提交：

- `.env`
- `venv/`、`poetai/`
- `data/*.db`、`*.db-wal`、`*.db-shm`
- `static/audio/chat/`和运行时生成的 `tts_*.mp3`
- `static/videos/`和 `static/video_tasks_cache.json`
- `server*.log`
- `test_result/test_result*txt`

已确认需要共享的正式图片和对应缓存 JSON 可正常提交。
