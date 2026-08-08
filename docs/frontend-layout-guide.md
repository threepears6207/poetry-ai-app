# 前端布局与坐标调整指南

## 1. 应该修改哪些文件

前端源码在 `frontend/shiya-app`。日常调整只改源码，不要修改 `docs/assets`，后者是 H5 构建产物，下次构建会被覆盖。

| 界面 | 源文件 |
|---|---|
| 首页、小镇入口、每日抽诗弹窗 | `pages/index/index.vue` |
| 拍照/相册识诗、拍摄方式选择、识别结果 | `pages/camera/camera.vue` |
| 古诗学习、分镜画面、播放控制 | `pages/study/study.vue` |
| 诗人对话 | `pages/chat/chat.vue` |
| 搜索与推荐 | `pages/recommend/recommend.vue` |
| 巩固、跟读、连线练习 | `pages/review/review.vue` |
| 集章墙 | `pages/collection/collection.vue` |
| 家长端 | `pages/parent/parent.vue` |
| 页面注册、横屏方向 | `pages.json` |
| 全局满屏、沉浸式横屏 | `App.vue` |
| Android 权限、H5 路由 | `manifest.json` |
| 后端地址与接口调用 | `utils/api.js` |
| 图片素材 | `static/final-ui/` |

每个 `.vue` 文件一般分为三段：

- `<template>`：组件结构，决定谁套在谁里面。
- `<script setup>`：数据、点击事件、缩放计算。
- `<style scoped>`：位置、宽高、字体、层级，绝大多数视觉问题在这里调整。

## 2. 当前项目的坐标系

### 最终版页面：1672 x 770

首页、拍照、对话、推荐、集章墙使用一张固定的 `1672px × 770px` 设计画布。左上角为原点 `(0, 0)`，向右是 X 增大，向下是 Y 增大。

```text
(0,0) --------------------------> X / left
  |
  |       元素左上角 (left, top)
  |       +------------------+
  |       |                  |
  |       +------------------+
  v
Y / top                    (1672,770)
```

页面会计算：

```js
scale = Math.min(windowWidth / 1672, windowHeight / 770)
```

然后对整张画布使用 `transform: scale(...)`。因此 CSS 里仍按设计稿原始坐标填写，不需要手动换算成手机像素。

例如：

```css
.camera-entry {
  position: absolute;
  left: 109px; /* 距设计画布左边 109 */
  top: 149px;  /* 距设计画布上边 149 */
  width: 440px;
  height: 330px;
}
```

元素的右边界是 `left + width`，下边界是 `top + height`。在 `1672 × 770` 画布中必须满足：

```text
left >= 0
top >= 0
left + width <= 1672
top + height <= 770
```

如果用 `right` 或 `bottom`，它们分别表示距父容器右边和下边的距离。`left: 50%` 表示元素左边从父容器中线开始；要真正居中通常还需要 `transform: translateX(-50%)`。

### 旧版主页面：844 x 390

`study.vue`、`review.vue`、`parent.vue` 的主缩放常量是 `844 × 390`。在这些页面调整普通组件时，应按这一套坐标判断，不能直接套用 `1672 × 770`。

`review.vue` 中部分最终版练习区域又单独使用 `1672 × 770`。判断方法是沿模板向外找最近的定位父容器：

- 最近父容器宽高为 `844 × 390`：使用旧版坐标。
- 最近父容器宽高为 `1672 × 770`：使用最终版坐标。
- 父容器没有固定宽高：百分比和绝对定位均相对该父容器实际尺寸。

不要只看元素本身的 `left/top`，绝对定位永远相对于最近一个设置了 `position: relative/absolute/fixed` 的祖先。

## 3. 常见问题怎么改

### 画面不在框内

先检查图片元素和它的父框：

```css
.frame {
  position: relative;
  overflow: hidden;
}

.frame image {
  width: 100%;
  height: 100%;
}
```

- 图片必须是父框的子元素。
- 父框需有明确 `width/height`。
- 需要裁掉框外内容时使用 `overflow: hidden`。
- 不希望变形时，uni-app `<image>` 优先用 `mode="aspectFill"`（填满并裁剪）或 `mode="aspectFit"`（完整显示并留空）。
- `mode="scaleToFill"` 会强行拉伸到框大小，适合本来就按框比例制作的 UI 素材，不适合照片和 AI 配图。

### 字不在框内

优先让框负责排版，不要靠很多 `top` 微调文字：

```css
.title-box {
  box-sizing: border-box;
  width: 300px;
  height: 72px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 1.2;
  overflow: hidden;
}
```

检查顺序：`width/height`、`padding`、`font-size`、`line-height`、`letter-spacing`。本项目不少标题设置了较大的 `letter-spacing`，长标题最容易因此越界。

单行按钮文字可用 `white-space: nowrap`；内容长度不固定时不要强制单行，应允许换行，并用 `word-break: break-word`。如果文字被图片遮住，检查 `z-index`，同时确保该元素已设置非 `static` 的 `position`。

### 组件整体位置不对

- 左右移动：改 `left`；数值增大向右，减小向左。
- 上下移动：改 `top`；数值增大向下，减小向上。
- 使用 `right/bottom` 的组件应改对应属性，不要同时再加 `left/top`。
- 多个项目等距排列优先改父容器的 `display: flex`、`gap`、`justify-content`。
- 图片可见区域与点击区域不一致时，同时检查外层 `.entry/.button` 和内部 `image` 的坐标。
- 弹窗或遮罩应相对整张画布使用 `position: absolute; inset: 0`。

### 看起来缩放或留黑边不对

当前策略是完整显示整张设计画布，所以屏幕比例不是 `1672:770` 时会自然留边。不要通过放大 `scale` 消除黑边，否则会裁掉内容。若产品要求铺满屏幕，需要统一决定使用“完整显示”还是“铺满裁剪”，再改所有页面的缩放策略，不能只改某一个组件。

## 4. 如何实际查看坐标

推荐用 HBuilderX 运行到浏览器，再按 `F12` 打开开发者工具：

1. 点击左上角的元素选择器，再点击画面中的组件。
2. 在 `Elements` 的 `Styles` 中找到对应类名和 `.vue` 源文件。
3. 在 `Computed` 查看最终生效的 `left/top/width/height/padding/font-size/line-height`。
4. 在浏览器控制台选中元素后执行 `$0.getBoundingClientRect()`，查看它在当前屏幕上的实际位置。
5. 临时勾选/修改 CSS 数值，确认效果后再写回 `.vue` 文件。

由于页面整体经过缩放，`getBoundingClientRect()` 返回的是屏幕实际像素。换回设计稿坐标可用：

```text
设计坐标 = 屏幕内相对画布的坐标 / scale
```

更简单的做法是直接在开发者工具里改源码 CSS 的 `left/top`，因为源码数值本来就是设计坐标。

调试边界时可临时加入，完成后删除：

```css
/* 临时调试 */
.要检查的类名 { outline: 2px solid red !important; }
.它的父容器 { outline: 2px solid blue !important; }
```

红框是组件自身盒子，蓝框是它的定位参照。图片明明在框里但视觉内容偏移时，通常是 PNG 素材本身带透明留白，可在图片查看器中检查素材边界。

## 5. 推荐调整流程

1. 先确认页面与对应 `.vue` 文件。
2. 在 `<template>` 中找到组件类名。
3. 沿父级确认它使用 `1672 × 770`、`844 × 390`，还是自适应容器。
4. 用红蓝 `outline` 看真实盒子，不要只凭肉眼看图片内容。
5. 一次只改一类问题：先父框，再图片，再文字。
6. 在 H5 横屏检查后，再到 Android 真机检查沉浸式全屏、状态栏、字体和权限相关组件。
7. 至少测试两种横屏比例，以及最长标题/作者/诗句等极端内容。

## 6. 后端与联调地址

H5 在本机运行时，`utils/api.js` 的 `BASE_URL` 可设为 `http://127.0.0.1:8000`。Android 真机不能使用该地址，因为真机的 `127.0.0.1` 指向手机自身；应改为电脑在同一 Wi-Fi/热点下的 IPv4 地址，例如 `http://192.168.3.18:8000`。

后端启动成功后检查：

- `http://127.0.0.1:8000/ping`
- `http://127.0.0.1:8000/docs`

