<template>
  <view class="page-root">
    <view class="camera-app">
      <view v-if="pageState === 'camera'" class="camera-page">
        <view class="camera-header">
          <view class="camera-back" @tap.stop="goBack">‹</view>

          <view class="camera-title-pill">
            <view class="camera-logo">🌱</view>
            <text>拍照识别</text>
          </view>

          <view class="camera-tip">诗芽可以识别古诗，也能为风景匹配古诗哦！</view>
        </view>

        <view class="camera-shell">
          <view class="camera-card">
            <view class="camera-fallback">
              <view>
                点击“拍摄”会调起手机系统相机<br />
                点击“相册”可以选择已有图片
              </view>
            </view>

            <view class="corner c1"></view>
            <view class="corner c2"></view>
            <view class="corner c3"></view>
            <view class="corner c4"></view>

            <view class="scan-line"></view>
            <view class="camera-guide-text">请把诗句或风景放进取景框</view>
          </view>
        </view>

        <view class="mode-panel">
          <view class="mode-switch">
            <button
              class="mode-option"
              :class="{ active: mode === 'poem' }"
              @tap="mode = 'poem'"
            >
              古诗
            </button>

            <button
              class="mode-option"
              :class="{ active: mode === 'landscape' }"
              @tap="mode = 'landscape'"
            >
              风景
            </button>
          </view>
        </view>

        <view class="right-actions">
          <button class="side-btn" @tap="goBack">
            <text class="side-icon">🏠</text>
            <text>返回</text>
          </button>

          <button class="shoot-btn" :disabled="recognizing" @tap="shootAndRecognize">
            <text class="shoot-icon">📷</text>
            <text>拍摄</text>
          </button>

          <button class="side-btn" :disabled="recognizing" @tap="chooseAlbumAndRecognize">
            <text class="side-icon">🖼️</text>
            <text>相册</text>
          </button>
        </view>
      </view>

      <view v-if="pageState === 'result'" class="camera-page result-page">
        <view class="camera-header">
          <view class="camera-back" @tap.stop="pageState = 'camera'">‹</view>

          <view class="camera-title-pill">
            <view class="camera-logo">🌱</view>
            <text>识别结果</text>
          </view>
        </view>

        <view class="result-card">
          <view class="poem-zone">
            <view class="poem-result">
              <view class="result-title">{{ matchedPoem.title }}</view>
              <view class="author">{{ matchedPoem.dynasty }} · {{ matchedPoem.author }}</view>
              <view class="poem-lines">
                <text
                  v-for="line in matchedPoem.content"
                  :key="line"
                >
                  {{ line }}
                </text>
              </view>
            </view>

            <view class="tag-panel">
              <view
                v-for="tag in displayTags"
                :key="tag"
                class="tag"
              >
                {{ tag }}
              </view>
            </view>
          </view>

          <view class="result-meta">
            <view class="mascot">👧</view>
          </view>

          <view class="speech-area">
            <view class="speech-card">
              诗芽为你找到了最合适的古诗，要不要进入学习？<br />
              进入后可以看诗意画面，还能和诗人聊聊这首诗。
            </view>

            <view class="inline-actions">
              <button class="choice secondary" @tap="pageState = 'camera'">再拍一首</button>
              <button class="choice primary" @tap="goStudy">进入学习 ▶</button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { API, getLocalPoemById } from '@/utils/api.js'

const pageState = ref('camera')
const mode = ref('poem')
const recognizing = ref(false)

const matchedPoem = ref(getLocalPoemById('poem_001'))
const sceneTags = ref([])
const matchType = ref('text')

const displayTags = computed(() => {
  if (sceneTags.value.length > 0) {
    return sceneTags.value.slice(0, 3).map((tag) => `✨ ${tag}`)
  }

  if (matchType.value === 'scene') {
    return ['🌿 风景', '📷 图片', '✨ 匹配']
  }

  return ['🌸 古诗', '📷 图片', '✨ 识别']
})

const goBack = () => {
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []

  if (pages.length > 1) {
    uni.navigateBack({
      delta: 1,
      fail: () => {
        uni.reLaunch({
          url: '/pages/index/index'
        })
      }
    })
    return
  }

  uni.reLaunch({
    url: '/pages/index/index',
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.replace('#/pages/index/index')
      }
    }
  })
}

const toast = (title) => {
  uni.showToast({
    title,
    icon: 'none'
  })
}



const readBlobAsBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      const result = reader.result || ''
      const base64 = String(result).split(',')[1] || ''

      if (!base64) {
        reject(new Error('图片 base64 转换失败'))
        return
      }

      resolve(base64)
    }

    reader.onerror = () => {
      reject(new Error('图片读取失败'))
    }

    reader.readAsDataURL(blob)
  })
}

const pathToBase64 = (filePath) => {
  return new Promise((resolve, reject) => {
    if (!filePath) {
      reject(new Error('没有获取到图片路径'))
      return
    }

    const path = String(filePath)

    if (path.startsWith('data:image')) {
      resolve(path.split(',')[1] || '')
      return
    }

    // 小程序 / 部分 App 环境
    if (typeof uni.getFileSystemManager === 'function') {
      try {
        const fs = uni.getFileSystemManager()

        fs.readFile({
          filePath: path,
          encoding: 'base64',
          success: (res) => resolve(res.data),
          fail: (err) => {
            console.log('getFileSystemManager 读取失败，尝试 H5 fetch：', err)

            if (typeof fetch === 'function' && typeof FileReader !== 'undefined') {
              fetch(path)
                .then((res) => res.blob())
                .then((blob) => readBlobAsBase64(blob))
                .then(resolve)
                .catch(reject)
            } else {
              reject(err)
            }
          }
        })
        return
      } catch (err) {
        console.log('getFileSystemManager 不可用：', err)
      }
    }

    // H5 环境
    if (typeof fetch === 'function' && typeof FileReader !== 'undefined') {
      fetch(path)
        .then((res) => res.blob())
        .then((blob) => readBlobAsBase64(blob))
        .then(resolve)
        .catch(reject)
      return
    }

    reject(new Error('当前平台暂不支持读取图片，请尝试相册上传或真机运行'))
  })
}

const fileToBase64 = async (chooseRes) => {
  console.log('图片选择/拍摄完整结果：', chooseRes)

  const tempFile = chooseRes.tempFiles && chooseRes.tempFiles[0]
  const tempPath = chooseRes.tempImagePath || (chooseRes.tempFilePaths && chooseRes.tempFilePaths[0])

  if (tempFile instanceof Blob) {
    return await readBlobAsBase64(tempFile)
  }

  if (tempFile && tempFile.file instanceof Blob) {
    return await readBlobAsBase64(tempFile.file)
  }

  if (tempFile && tempFile.path) {
    return await pathToBase64(tempFile.path)
  }

  if (tempPath) {
    return await pathToBase64(tempPath)
  }

  throw new Error('没有获取到可读取的图片文件')
}

const handleOcrResult = (res) => {
  console.log('识诗结果：', res)

  if (!res || !res.success) {
    sceneTags.value = res?.scene_tags || []
    matchType.value = res?.match_type || 'text'

    toast(res?.message || res?.error || '未识别到相关古诗')
    return
  }

  const poem = res.data?.matched_poem || res.data || res.matched_poem

  if (!poem || !poem.id) {
    toast('识别成功但没有匹配到古诗')
    return
  }

  matchedPoem.value = {
    ...poem,
    content: Array.isArray(poem.content)
      ? poem.content
      : String(poem.content || '').split(/[，,。\n]/).filter(Boolean)
  }

  sceneTags.value = res.scene_tags || poem.tags || []
  matchType.value = res.match_type || res.mode || 'text'
  pageState.value = 'result'

  toast(`识别到《${matchedPoem.value.title}》`)
}

const recognizeByBase64 = async (imageBase64) => {
  const res = await API.recognizePoemImage(imageBase64)
  handleOcrResult(res)
}

const chooseCameraBySystem = () => {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['camera'],
      success: resolve,
      fail: reject
    })
  })
}


const shootAndRecognize = async () => {
  if (recognizing.value) return

  recognizing.value = true

  try {
    const photoRes = await chooseCameraBySystem()

    uni.showLoading({
      title: '识别中...'
    })

    const imageBase64 = await fileToBase64(photoRes)
    await recognizeByBase64(imageBase64)
  } catch (err) {
    console.log('拍照识诗失败：', err)

    const msg = err?.errMsg || err?.message || ''
    if (msg.includes('cancel')) {
      return
    }

    toast('拍照识别失败，请检查相机权限')
  } finally {
    uni.hideLoading()
    recognizing.value = false
  }
}

const chooseAlbumAndRecognize = async () => {
  if (recognizing.value) return

  recognizing.value = true

  try {
    const chooseRes = await uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album']
    })

    uni.showLoading({
      title: '识别中...'
    })

    const imageBase64 = await fileToBase64(chooseRes)
    await recognizeByBase64(imageBase64)
  } catch (err) {
    console.log('相册识诗失败：', err)

    toast(err?.message || '图片识别失败')
  } finally {
    uni.hideLoading()
    recognizing.value = false
  }
}

const goStudy = () => {
  if (matchedPoem.value?.id) {
    API.preloadGenerateImage(matchedPoem.value)
  }

  uni.navigateTo({
    url: `/pages/study/study?poem_id=${matchedPoem.value.id}`,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = `#/pages/study/study?poem_id=${matchedPoem.value.id}`
      }
    }
  })
}
</script>

<style scoped>
* {
  box-sizing: border-box;
}

button::after {
  border: none;
}

.page-root {
  width: 100vw;
  height: 100vh;
  background: #1a1a1a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  font-family: "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  color: #5b508d;
}

.camera-app {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: 100vw;
  max-height: 100vh;
  overflow: hidden;
  border-radius: 0;
  background:
    radial-gradient(circle at 6% 4%, rgba(255, 225, 105, 0.28), transparent 25%),
    radial-gradient(circle at 92% 16%, rgba(255, 210, 145, 0.14), transparent 25%),
    linear-gradient(180deg, #fffaf2 0%, #fff2e9 52%, #ffe9df 100%);
}

.camera-page {
  position: absolute;
  inset: 0;
  padding: 7px 16px 14px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 48px 92px;
  grid-template-rows: 58px minmax(0, 1fr);
  gap: 8px 12px;
}

.camera-header {
  grid-column: 1 / 4;
  position: relative;
  height: 44px;
  z-index: 20;
}

.camera-back {
  position: absolute;
  left: 0;
  top: 4px;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.86);
  color: #5b508d;
  font-size: 26px;
  line-height: 1;
  box-shadow: 0 7px 16px rgba(112, 79, 54, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  z-index: 9999;
  pointer-events: auto;
}

.camera-title-pill {
  position: absolute;
  left: 50%;
  top: 0;
  transform: translateX(-50%);
  height: 42px;
  min-width: 188px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 6px 18px 6px 11px;
  border-radius: 999px;
  border: 4px solid #ffe057;
  background: rgba(255, 255, 255, 0.9);
  color: #5b508d;
  font-weight: 950;
  font-size: 17px;
  letter-spacing: 1px;
  box-shadow: 0 7px 16px rgba(111, 84, 55, 0.09);
}

.camera-logo {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #ff964b;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}

.camera-tip {
  position: absolute;
  left: 50%;
  top: 44px;
  transform: translateX(-50%);
  color: #7a6ea1;
  font-size: 12px;
  font-weight: 850;
  white-space: nowrap;
}

.camera-shell {
  grid-column: 1;
  grid-row: 2;
  display: grid;
  place-items: center;
  min-width: 0;
  min-height: 0;
  padding: 2px 0 4px;
  transform: translateX(10px);
}

.camera-card {
  position: relative;
  width: 90%;
  aspect-ratio: 16 / 9;
  max-height: 285px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(64, 67, 76, 0.92), rgba(27, 31, 39, 0.96));
  overflow: hidden;
  box-shadow: 0 14px 24px rgba(74, 55, 42, 0.18);
  border: 4px solid rgba(255, 255, 255, 0.78);
}

.camera-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 44%, rgba(255, 255, 255, 0.16), transparent 31%),
    linear-gradient(90deg, transparent 0 32%, rgba(255, 255, 255, 0.075) 32% 33%, transparent 33% 66%, rgba(255, 255, 255, 0.075) 66% 67%, transparent 67%),
    linear-gradient(0deg, transparent 0 32%, rgba(255, 255, 255, 0.075) 32% 33%, transparent 33% 66%, rgba(255, 255, 255, 0.075) 66% 67%, transparent 67%);
  opacity: 0.84;
}

.poem-paper {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 196px;
  height: 158px;
  border-radius: 16px;
  background: #fffdf5;
  transform: translate(-50%, -50%) rotate(-2deg);
  padding: 12px 18px;
  color: #63598f;
  text-align: center;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.17);
}

.poem-paper-title {
  margin: 0 0 5px;
  font-size: 20px;
  color: #5b508d;
  font-weight: 950;
}

.poem-paper-line {
  display: block;
  margin: 3px 0;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 2px;
}

.scan-line {
  position: absolute;
  z-index: 3;
  left: 42px;
  right: 42px;
  top: 46%;
  height: 3px;
  border-radius: 9px;
  background: linear-gradient(90deg, transparent, #55e4cf, transparent);
  box-shadow: 0 0 16px #55e4cf;
  animation: scan 2.2s infinite ease-in-out;
}

@keyframes scan {
  50% {
    transform: translateY(38px);
  }
}

.corner {
  position: absolute;
  width: 38px;
  height: 38px;
  border-color: #ffe66b;
  border-style: solid;
  z-index: 3;
}

.c1 {
  left: 20px;
  top: 20px;
  border-width: 4px 0 0 4px;
  border-radius: 14px 0 0 0;
}

.c2 {
  right: 20px;
  top: 20px;
  border-width: 4px 4px 0 0;
  border-radius: 0 14px 0 0;
}

.c3 {
  left: 20px;
  bottom: 20px;
  border-width: 0 0 4px 4px;
  border-radius: 0 0 0 14px;
}

.c4 {
  right: 20px;
  bottom: 20px;
  border-width: 0 4px 4px 0;
  border-radius: 0 0 14px 0;
}

.mode-panel {
  grid-column: 2;
  grid-row: 2;
  align-self: center;
  width: 42px;
  height: 154px;
  z-index: 2;
}

.mode-switch {
  height: 100%;
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 4px;
  padding: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 2px solid rgba(255, 224, 87, 0.72);
  box-shadow: 0 8px 16px rgba(111, 84, 55, 0.1);
  overflow: hidden;
}

.mode-option {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #7a6ea1;
  font-size: 14px;
  font-weight: 950;
  line-height: 1;
  letter-spacing: 2px;
  writing-mode: vertical-rl;
  text-orientation: upright;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mode-option.active {
  color: #ffffff;
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  box-shadow: 0 3px 0 #f16012;
}

.right-actions {
  grid-column: 3;
  grid-row: 2;
  align-self: center;
  height: 268px;
  display: grid;
  grid-template-rows: 62px 78px 62px;
  gap: 25px;
  z-index: 1;
}

.side-btn {
  margin: 0;
  padding: 0;
  background: rgba(255, 255, 255, 0.86);
  color: #5b508d;
  font-size: 13px;
  border: 0;
  border-radius: 22px;
  font-weight: 950;
  box-shadow: 0 8px 18px rgba(111, 84, 55, 0.13);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  line-height: 1.2;
}

.side-icon {
  font-size: 22px;
  line-height: 1;
}

.shoot-btn {
  margin: 0;
  padding: 0;
  background: linear-gradient(180deg, #ffab68 0%, #ff7d32 100%);
  color: #ffffff;
  font-size: 16px;
  letter-spacing: 1px;
  border: 0;
  border-radius: 22px;
  font-weight: 950;
  box-shadow: 0 5px 0 #f16012, 0 10px 17px rgba(236, 98, 34, 0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  line-height: 1.2;
}

.shoot-icon {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.22);
  font-size: 22px;
  line-height: 1;
}

.result-page {
  grid-template-columns: 1fr;
  grid-template-rows: 58px minmax(0, 1fr);
}

.result-card {
  grid-column: 1 / 4;
  grid-row: 2;
  position: relative;
  border-radius: 24px;
  background:
    radial-gradient(circle at 8% 82%, rgba(139, 216, 157, 0.3), transparent 17%),
    radial-gradient(circle at 98% 88%, rgba(217, 160, 222, 0.28), transparent 18%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 246, 248, 0.92));
  box-shadow: 0 12px 22px rgba(74, 55, 42, 0.13);
  padding: 16px 20px;
  display: grid;
  grid-template-columns: minmax(370px, 46%) minmax(0, 1fr);
  gap: 18px;
  align-items: center;
  overflow: hidden;
}

.poem-zone {
  display: grid;
  gap: 9px;
  align-self: stretch;
  align-content: center;
  width: 100%;
}

.poem-result {
  width: 100%;
  height: 206px;
  border-radius: 12px;
  background: rgba(255, 253, 245, 0.94);
  box-shadow: 0 9px 20px rgba(70, 45, 20, 0.12);
  padding: 14px 24px 14px 18px;
  text-align: center;
  display: grid;
  align-content: center;
  color: #4e4775;
}

.result-title {
  color: #4e4775;
  font-size: 21px;
  letter-spacing: 5px;
  font-weight: 950;
}

.author {
  color: #7a6ea1;
  font-size: 14px;
  font-weight: 850;
  margin: 4px 0 7px;
  letter-spacing: 2px;
}

.poem-lines {
  color: #5d5485;
  font-size: 17px;
  font-weight: 900;
  line-height: 1.58;
  letter-spacing: 2px;
  display: flex;
  flex-direction: column;
}

.tag-panel {
  width: 100%;
  border-radius: 18px;
  background: rgba(255, 248, 232, 0.88);
  border: 2px dashed #ffcf69;
  padding: 8px 10px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
}

.tag {
  padding: 7px 10px;
  border-radius: 999px;
  background: #ecfbff;
  color: #42a8c7;
  font-size: 13px;
  font-weight: 950;
  text-align: center;
}

.result-meta {
  position: absolute;
  left: 465px;
  top: 96px;
  z-index: 2;
}

.mascot {
  width: 66px;
  height: 66px;
  border-radius: 50%;
  background: linear-gradient(180deg, #ffecc4, #ffbd7a);
  display: grid;
  place-items: center;
  font-size: 33px;
  box-shadow: 0 9px 18px rgba(112, 79, 54, 0.13);
  position: relative;
}

.mascot::before {
  content: "🌱";
  position: absolute;
  top: -23px;
  font-size: 28px;
}

.speech-area {
  grid-column: 2;
  display: grid;
  grid-template-columns: 82px 1fr;
  gap: 18px 16px;
  align-self: stretch;
  align-content: start;
  padding-top: 24px;
  width: 85%;
  margin-left: auto;
  margin-right: 18px;
}

.speech-card {
  grid-column: 2;
  position: relative;
  min-height: 112px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 9px 20px rgba(112, 79, 54, 0.12);
  padding: 16px 18px;
  color: #6a5f97;
  font-size: 16px;
  font-weight: 950;
  line-height: 1.58;
}

.inline-actions {
  grid-column: 1 / 3;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  padding-top: 14px;
  transform: translateY(7px);
}

.choice {
  height: 46px;
  border: 0;
  border-radius: 999px;
  font-weight: 950;
  font-size: 16px;
}

.primary {
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: white;
  box-shadow: 0 5px 0 #f16012;
}

.secondary {
  background: #fff;
  color: #6a5f97;
  box-shadow: 0 5px 0 rgba(220, 211, 236, 0.9);
}


.live-camera {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.camera-fallback {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
  padding: 20px;
  text-align: center;
  background:
    radial-gradient(circle at 50% 44%, rgba(255, 255, 255, 0.16), transparent 31%),
    linear-gradient(180deg, rgba(64, 67, 76, 0.92), rgba(27, 31, 39, 0.96));
  color: #fffdf5;
  font-size: 16px;
  font-weight: 950;
  line-height: 1.6;
}

.camera-guide-text {
  position: absolute;
  left: 50%;
  bottom: 16px;
  z-index: 4;
  transform: translateX(-50%);
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.42);
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

button[disabled] {
  opacity: 0.6;
}

</style>
