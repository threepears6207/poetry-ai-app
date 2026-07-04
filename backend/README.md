# 诗芽小学堂后端

后端使用 FastAPI，负责古诗数据、学习记录、巩固计划、个性化推荐、OCR、语音识别、诗人对话、语音合成、AI 配图和视频生成实验。

## 当前数据状态

- 正式读写已切换到 SQLite，默认文件为 `data/poetry_ai.db`。
- 古诗库共 150 首：`age_3_4` 50 首，`age_5_7` 100 首。
- 数据表：`poems`、`users`、`learning_records`、`consolidations`、`reading_scores`。
- `data/poems.json`、`records.json`、`consolidations.json` 仅作为历史源数据/迁移输入，正式接口不再直接读写它们。
- SQLite 运行库已加入 `.gitignore`，新环境需自行初始化。

## 环境

- Windows
- Python 3.11（FunASR 及其依赖不建议使用 3.12/3.13）
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

`requirements.txt` 已包含 FastAPI、Uvicorn、FunASR、PyTorch、edge-tts、websocket-client 等项目依赖。首次安装和首次语音识别会比较慢。

FunASR 默认会将模型缓存到用户目录。如需改位置，在启动前设置：

```powershell
$env:MODELSCOPE_CACHE="D:\modelscope_cache"
```

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

第一条命令根据 `schema.sql` 建表，第二条命令将 `data_sources/generated/children_poems_candidates.json` 中的 150 首古诗导入 SQLite。

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

1. 根据 `age_3_4` / `age_5_7` 筛选年龄匹配的古诗。
2. 排除该用户已学过的诗。
3. 根据 `reading_scores` 计算标签平均分和 `strong_tags`。
4. 优先返回与强项标签重合的古诗，再参考难度排序。

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
| POST | `/record` | 写入学习记录并建立巩固记录 |
| GET | `/record` | 用户学习记录 |
| GET | `/record/summary` | 家长端学习统计 |
| POST | `/profile/reading-score` | 保存整首跟读平均分 |
| GET | `/profile/{user_id}` | 用户标签分数和强项标签 |
| GET | `/recommend` | 年龄 + 未学 + 强项标签推荐 |
| GET | `/consolidation/list` | 巩固列表和统计 |
| GET | `/consolidation/status/{poem_id}` | 单首巩固状态 |
| POST | `/consolidation/result` | 整首通过后更新复习计划 |
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
| `record.py` | 学习记录与家长统计 |
| `consolidation.py` | 巩固记录和 1/3/7 天复习节奏 |
| `recommend.py` | 跟读画像与个性化推荐 |
| `ocr.py` | 百度 OCR、图像识别和 SQLite 古诗匹配 |
| `asr.py` | FunASR 语音识别和单句评分 |
| `chat.py` / `poet_voice.py` / `vivo_tts.py` | 诗人对话、声音档案、vivo TTS 和降级 |
| `generate.py` | 分镜规划、并行生图、渐进任务和图片缓存 |
| `video_generate.py` | 整首古诗文生视频实验 |
| `data_sources/` | 150 首古诗源数据、译文和标签质检报告 |
| `scripts/` | 建库、导入、迁移、元数据生成与审核脚本 |
| `static/` | 已生成的诗歌图片、诗人头像、音频和缓存 |
| `test_result/` | 后端测试脚本；运行结果文本已忽略 |

## 测试

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
