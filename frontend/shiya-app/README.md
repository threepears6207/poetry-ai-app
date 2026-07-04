# 诗芽小学堂前端

前端使用 uni-app + Vue 3 开发，主要面向 Android 横屏真机，同时支持 H5 联调。当前项目为 HBuilderX 工程，没有 `package.json`，不需要在本目录执行 `npm install`。

## 页面

| 路径 | 功能 |
|---|---|
| `pages/index/index` | 首页、年龄选择、搜索、当日推荐、巩固入口 |
| `pages/camera/camera` | 拍照 OCR 识诗、风景图匹配古诗 |
| `pages/study/study` | 诗文学习、语音范读、AI 分镜配图、学习记录 |
| `pages/chat/chat` | 诗人文字/语音对话、诗人回复语音播放 |
| `pages/recommend/recommend` | 按年龄、类别和强项标签推荐未学古诗 |
| `pages/review/review` | 巩固列表、单句跟读评分、复习进度 |
| `pages/parent/parent` | 学习数量、时长和最近记录 |

App 启动时会锁定横屏并尝试进入 Android 沉浸式全屏。

## 联调前配置

打开 `utils/api.js`，修改文件顶部的 `BASE_URL`。

```js
// 电脑本机 H5
const BASE_URL = 'http://127.0.0.1:8000'

// 手机与电脑连同一 Wi-Fi/热点时，改为电脑局域网 IP
const BASE_URL = 'http://192.168.x.x:8000'
```

当前代码中的地址是开发机的热点地址，换网络后需要重新修改。真机不能使用 `127.0.0.1`，因为它指向手机自身。

后端要以局域网模式启动：

```powershell
cd backend
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 运行

### H5

1. 用 HBuilderX 打开 `frontend/shiya-app`。
2. 选择“运行—运行到浏览器”。
3. 先访问后端 `/ping`，确认接口可达。

H5 的相机、麦克风和音频自动播放受浏览器限制，真机效果以 Android App 为准。

### Android 真机

1. 手机与电脑使用同一局域网。
2. 在 HBuilderX 选择“运行—运行到手机或模拟器—Android App 基座”。
3. 允许相机和麦克风权限。
4. 用手机浏览器访问 `http://电脑IP:8000/ping`，确认网络畅通。

## 主要数据流程

### 学习与配图

1. 搜索、OCR 或推荐页选中古诗。
2. 进入学习页后请求诗文详情，并预热 AI 配图。
3. 前端调用 `POST /generate/image/start`，再轮询 `GET /generate/image/status/{task_id}`。
4. 已生成的分镜会立即展示，后续分镜生成完成后继续播放。
5. 学习结束时调用 `POST /record`，后端同时建立该诗的巩固记录。

### 诗人对话

- `POST /chat` 先获取文字回复。
- 文字显示后调用 `POST /chat/voice-preview` 生成对应诗人语音。
- 新语音播放前会停止上一段，离开页面时释放音频资源。
- 语音生成失败不影响文字回复。

### 跟读巩固

1. 每句录音后调用 `POST /asr/score`。
2. `passed=false` 只重读当前句，不结束整次巩固。
3. 整首全部通过后，写入整首平均分 `POST /profile/reading-score`。
4. 最后只调用一次 `POST /consolidation/result`，并传 `passed=true`。

### 推荐

- 前端传递年龄层：`age_3_4` 或 `age_5_7`。
- 后端先排除已学古诗，再按跟读强项标签和难度排序。
- 首页和推荐页共用“日期 + 年龄层”缓存，同一天显示同一首每日推荐。

## 用户与本地兜底

- 当前统一使用 `test_user`，定义在 `utils/api.js` 的 `DEFAULT_USER_ID`。
- 年龄选择保存在本地存储，推荐接口会同步后端用户年龄层。
- `utils/api.js` 内保留 5 首 `LOCAL_POEMS`，后端暂时不可用时用于页面兜底，正常数据仍以后端 SQLite 为准。

## 关键文件

| 文件 | 说明 |
|---|---|
| `utils/api.js` | 后端地址、统一请求、接口封装、每日推荐和生图 Promise 缓存 |
| `pages.json` | 页面路由和全局横屏样式 |
| `manifest.json` | Android 横屏、权限和 H5 路由配置 |
| `App.vue` | 沉浸式横屏和全局页面背景 |

## 常见问题

- **手机接口超时**：检查 `BASE_URL`、电脑防火墙、后端是否使用 `0.0.0.0` 启动。
- **诗人回复有文字无声音**：查看 `/chat/voice-preview` 请求和后端 vivo TTS 配置。
- **录音按钮无效**：检查 Android 麦克风权限；H5 需浏览器允许录音。
- **拍照识别失败**：确认图片已转为 base64，并查看后端百度 OCR/图像识别配置。
- **配图首次较慢**：等待逐帧返回；同一首诗后续会复用后端缓存。
