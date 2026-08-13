<template>
  <view class="page-root final-camera-root">
    <view class="camera-app final-camera-app" :style="appScaleStyle">
      <view v-if="pageState === 'camera'" class="final-mode-page">
        <view class="camera-home-scene" aria-hidden="true">
          <image class="camera-town-bg" src="/static/final-ui/town-bg.png" mode="scaleToFill" />
          <view class="camera-home-brand">
            <image src="/static/final-ui/brand-logo.png" mode="widthFix" />
          </view>
          <view class="camera-home-age">
            <image src="/static/final-ui/age.png" mode="scaleToFill" />
            <text>{{ homeAgeText }}</text>
          </view>
          <view class="camera-home-parent">
            <image src="/static/final-ui/parent.png" mode="scaleToFill" />
            <text>家长端</text>
          </view>
          <view class="camera-home-entry camera-home-camera"><image src="/static/final-ui/town-camera.png" mode="scaleToFill" /></view>
          <view class="camera-home-entry camera-home-today"><image src="/static/final-ui/town-today.png" mode="scaleToFill" /></view>
          <view class="camera-home-entry camera-home-search"><image src="/static/final-ui/town-search.png" mode="scaleToFill" /></view>
          <view class="camera-home-entry camera-home-practice"><image src="/static/final-ui/town-practice.png" mode="scaleToFill" /></view>
          <view class="camera-home-entry camera-home-stamps"><image src="/static/final-ui/town-stamps.png" mode="scaleToFill" /></view>
        </view>
        <view class="camera-popup-mask">
          <view class="camera-choice-popup">
            <image src="/static/final-ui/camera-choice-transparent.png" mode="scaleToFill" />
            <view class="camera-popup-title" @tap.stop="speakText('拍一拍')">拍 一 拍</view>
            <view class="camera-popup-tip">
              <text>拍一拍，找诗意：</text>
              <text>课本诗句和眼前风景都可以拍哦</text>
            </view>
            <button class="popup-close-hotspot" @tap="goBack" aria-label="关闭"></button>
            <button class="popup-action album-hotspot" :disabled="recognizing" @tap="chooseAlbumAndRecognize" aria-label="相册"></button>
            <button class="popup-action camera-hotspot" :disabled="recognizing" @tap="shootAndRecognize" aria-label="拍照"></button>
            <button class="popup-action back-hotspot" @tap="goBack" aria-label="返回"></button>
            <view v-if="recognizing" class="recognizing-tip">正在识别，请稍等……</view>
          </view>
        </view>
      </view>

      <view v-else class="final-result-page">
        <image class="final-page-bg" src="/static/final-ui/camera-result-page.png" mode="scaleToFill" />
        <button class="result-back-hotspot result-back-native" @tap="pageState = 'camera'" aria-label="返回"></button>
        <view class="result-page-title" @tap.stop="speakText('诗芽为你找到了这些古诗')">诗芽为你找到了这些古诗</view>
        <view class="result-subtitle">点击你想学习的诗，打开画卷开始学习吧</view>
        <view class="result-cards">
          <view v-for="(poem, index) in resultCandidates" :key="poem.id" class="result-poem-card" :class="{ best: index === resultCandidates.length - 1 }" @tap="selectResult(poem)">
            <view class="candidate-title" :class="{ 'long-title': isLongPoemTitle(poem.title), 'extra-long-title': isExtraLongPoemTitle(poem.title) }">{{ poem.title }}</view>
            <view class="candidate-author">{{ poem.dynasty }} · {{ poem.author }}</view>
            <view class="candidate-lines">
              <text v-for="line in getCandidateLines(poem)" :key="line">{{ line }}</text>
            </view>
            <view class="candidate-tags">{{ (poem.tags || []).slice(0, 2).join(' · ') }}</view>
            <button class="open-poem-button">打开画卷</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { API } from '@/utils/api.js'
import { speakText } from '@/utils/speech.js'
// #ifdef APP-PLUS
import {
  analyzeImage,
  initializeImageModel,
  openModelStoragePermissionSettings,
  releaseImageModel,
} from '@/uni_modules/shiya-image-analysis'
// #endif

const DESIGN_WIDTH = 1672
const DESIGN_HEIGHT = 770
const appScale = ref(1)
const homeAgeText = ref('4 岁')

const appScaleStyle = computed(() => `transform: scale(${appScale.value});`)
const isLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 4
const isExtraLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 6

const updateAppScale = () => {
  try {
    const systemInfo = uni.getSystemInfoSync()
    const width = Number(systemInfo.windowWidth || systemInfo.screenWidth || DESIGN_WIDTH)
    const height = Number(systemInfo.windowHeight || systemInfo.screenHeight || DESIGN_HEIGHT)
    const nextScale = Math.min(width / DESIGN_WIDTH, height / DESIGN_HEIGHT)

    appScale.value = nextScale > 0 ? Number(nextScale.toFixed(4)) : 1
  } catch (err) {
    appScale.value = 1
  }
}

const handleAppResize = () => {
  updateAppScale()
}

onMounted(() => {
  updateAppScale()
  homeAgeText.value = uni.getStorageSync('shiYaChildAgeText') || '4 岁'

  if (typeof uni.onWindowResize === 'function') {
    uni.onWindowResize(handleAppResize)
  }
})

onUnmounted(() => {
  if (typeof uni.offWindowResize === 'function') {
    uni.offWindowResize(handleAppResize)
  }

  // #ifdef APP-PLUS
  releaseImageModel()
  // #endif
})

const DEFAULT_COMPETITION_MODEL_PATH = '/sdcard/1225/1.7.0.4_1225_mtk9500'
const pageState = ref('camera')
const mode = ref('poem')
const recognizing = ref(false)

const matchedPoem = ref(null)
const sceneTags = ref([])
const matchType = ref('text')
const modelReady = ref(false)
let modelInitializing = null

const displayTags = computed(() => {
  const poemTags = Array.isArray(matchedPoem.value?.tags) ? matchedPoem.value.tags : []
  return poemTags.slice(0, 3).map((tag) => `✨ ${tag}`)
})

const resultCandidates = ref([])

const getCandidateLines = (poem = {}) => {
  const content = Array.isArray(poem.content)
    ? poem.content
    : String(poem.content || '').split(/[，。\n]/).filter(Boolean)
  return content.slice(0, 4)
}

const normalizePoem = (poem = {}) => ({
  ...poem,
  id: poem.id || poem.poem_id || '',
  content: Array.isArray(poem.content)
    ? poem.content
    : String(poem.content || '').split(/[，。\n]/).filter(Boolean),
  tags: Array.isArray(poem.tags) ? poem.tags : [],
})

const loadPoemDetail = async (poem) => {
  const normalized = normalizePoem(poem)
  if (!normalized.id || normalized.content.length) return normalized

  try {
    const detail = await API.getPoemDetail(normalized.id)
    if (detail?.success && detail?.data) {
      return normalizePoem({ ...normalized, ...detail.data })
    }
  } catch (err) {
    console.log('候选古诗详情加载失败：', err)
  }

  return normalized
}

const selectResult = async (poem) => {
  if (!poem?.id) return
  matchedPoem.value = await loadPoemDetail(poem)
  goStudy()
}
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



const isBlobLike = (value) => {
  return typeof Blob !== 'undefined' && value instanceof Blob
}

const stripImageBase64Prefix = (value = '') => {
  return String(value || '').replace(/^data:image\/\w+;base64,/, '')
}

const readBlobAsBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    if (typeof FileReader === 'undefined') {
      reject(new Error('当前平台不支持 FileReader 读取图片'))
      return
    }

    const reader = new FileReader()

    reader.onload = () => {
      const result = reader.result || ''
      const base64 = stripImageBase64Prefix(result)

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

const readFileByPlusIo = (filePath) => {
  return new Promise((resolve, reject) => {
    if (typeof plus === 'undefined' || !plus.io) {
      reject(new Error('plus.io 不可用'))
      return
    }

    plus.io.resolveLocalFileSystemURL(
      filePath,
      (entry) => {
        entry.file(
          (file) => {
            const reader = new plus.io.FileReader()

            reader.onloadend = (event) => {
              const result = event?.target?.result || ''
              const base64 = stripImageBase64Prefix(result)

              if (!base64) {
                reject(new Error('plus.io 图片 base64 转换失败'))
                return
              }

              resolve(base64)
            }

            reader.onerror = reject
            reader.readAsDataURL(file)
          },
          reject
        )
      },
      reject
    )
  })
}

const readFileByUniFs = (filePath) => {
  return new Promise((resolve, reject) => {
    if (typeof uni.getFileSystemManager !== 'function') {
      reject(new Error('uni.getFileSystemManager 不可用'))
      return
    }

    const fs = uni.getFileSystemManager()

    fs.readFile({
      filePath,
      encoding: 'base64',
      success: (res) => {
        const base64 = stripImageBase64Prefix(res.data)

        if (!base64) {
          reject(new Error('图片 base64 为空'))
          return
        }

        resolve(base64)
      },
      fail: reject
    })
  })
}

const readFileByH5Fetch = (filePath) => {
  return new Promise((resolve, reject) => {
    if (typeof fetch !== 'function' || typeof FileReader === 'undefined') {
      reject(new Error('H5 图片读取能力不可用'))
      return
    }

    fetch(filePath)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`图片读取失败：${res.status}`)
        }

        return res.blob()
      })
      .then((blob) => readBlobAsBase64(blob))
      .then(resolve)
      .catch(reject)
  })
}

const normalizeLocalFilePath = (filePath) => {
  const path = String(filePath || '')

  // App 真机常见路径是 file:///storage/...，plus.io 可以直接读。
  // 部分 uni 文件系统读取不接受 file://，失败后会自动降级到 plus.io。
  return path
}

const pathToBase64 = async (filePath) => {
  if (!filePath) {
    throw new Error('没有获取到图片路径')
  }

  const path = normalizeLocalFilePath(filePath)

  if (path.startsWith('data:image')) {
    return stripImageBase64Prefix(path)
  }

  const errors = []

  try {
    return await readFileByUniFs(path)
  } catch (err) {
    errors.push(`uniFs: ${err?.errMsg || err?.message || err}`)
    console.log('getFileSystemManager 读取失败，尝试 plus.io：', err)
  }

  try {
    return await readFileByPlusIo(path)
  } catch (err) {
    errors.push(`plusIo: ${err?.message || err}`)
    console.log('plus.io 读取失败，尝试 H5 fetch：', err)
  }

  try {
    return await readFileByH5Fetch(path)
  } catch (err) {
    errors.push(`h5Fetch: ${err?.message || err}`)
    console.log('H5 fetch 读取失败：', err)
  }

  throw new Error(`当前平台暂不支持读取图片：${errors.join('；')}`)
}

const fileToBase64 = async (chooseRes) => {
  console.log('图片选择/拍摄完整结果：', chooseRes)

  const tempFile = chooseRes.tempFiles && chooseRes.tempFiles[0]
  const tempPath = chooseRes.tempImagePath || (chooseRes.tempFilePaths && chooseRes.tempFilePaths[0])

  // H5 可能返回 File/Blob；App 端没有 Blob，所以必须先判断 typeof Blob。
  if (isBlobLike(tempFile)) {
    return await readBlobAsBase64(tempFile)
  }

  if (tempFile && isBlobLike(tempFile.file)) {
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

const handleOcrResult = async (res) => {
  console.log('识诗结果：', res)

  if (!res || !res.success) {
    sceneTags.value = res?.scene_tags || []
    matchType.value = res?.match_type || 'text'

    toast(res?.message || res?.error || '未识别到相关古诗')
    return
  }

  const firstCandidate = Array.isArray(res.candidates) ? res.candidates[0] : null
  let poem = res.data?.matched_poem || res.data || res.matched_poem || firstCandidate

  const candidateId = poem?.id || poem?.poem_id
  if (candidateId && (!Array.isArray(poem?.content) || !poem.content.length)) {
    try {
      const detail = await API.getPoemDetail(candidateId)
      if (detail?.success && detail?.data) poem = detail.data
    } catch (err) {
      console.log('候选诗详情加载失败：', err)
    }
  }

  if (!poem || !(poem.id || poem.poem_id)) {
    toast('识别成功但没有匹配到古诗')
    return
  }

  matchedPoem.value = {
    ...poem,
    id: poem.id || poem.poem_id,
    content: Array.isArray(poem.content)
      ? poem.content
      : String(poem.content || '').split(/[，,。\n]/).filter(Boolean)
  }

  const rawCandidates = Array.isArray(res.candidates) ? res.candidates : []
  const loadedCandidates = await Promise.all(
    rawCandidates
      .filter(candidate => candidate?.id || candidate?.poem_id)
      .slice(0, 3)
      .map(loadPoemDetail)
  )
  const otherCandidates = loadedCandidates.filter(
    candidate => String(candidate.id) !== String(matchedPoem.value.id)
  )
  resultCandidates.value = [...otherCandidates.slice(0, 2), matchedPoem.value]

  sceneTags.value = res.scene_tags || poem.tags || []
  matchType.value = res.match_type || res.mode || 'text'
  pageState.value = 'result'

  toast(`识别到《${matchedPoem.value.title}》`)
}

const recognizeByBase64 = async (imageBase64) => {
  const res = await API.recognizePoemImage(imageBase64)
  await handleOcrResult(res)
}

const ensureImageModelReady = () => {
  if (modelReady.value) return Promise.resolve(true)
  if (modelInitializing) return modelInitializing

  modelInitializing = new Promise((resolve) => {
    initializeImageModel(DEFAULT_COMPETITION_MODEL_PATH, (result) => {
      modelInitializing = null
      modelReady.value = result.state === 'ready'

      if (result.state === 'permission_required') {
        openModelStoragePermissionSettings()
        toast('请授权模型文件访问后再试')
      } else if (!modelReady.value) {
        toast(result.message || '端侧模型初始化失败')
      }

      resolve(modelReady.value)
    })
  })

  return modelInitializing
}

const analyzeLocalImage = (imagePath) => {
  return new Promise((resolve) => {
    analyzeImage(imagePath, (result) => resolve(result))
  })
}

const getNativeImagePath = (chooseResult = {}) => {
  const tempFile = chooseResult.tempFiles?.[0]
  const imagePath = tempFile?.path || chooseResult.tempFilePaths?.[0] || chooseResult.tempImagePath || ''
  if (!imagePath) return ''

  if (typeof plus !== 'undefined' && plus.io && typeof plus.io.convertLocalFileSystemURL === 'function') {
    const nativePath = plus.io.convertLocalFileSystemURL(imagePath)
    if (nativePath) return nativePath
  }

  return imagePath
}

const handleCandidateResult = async (res) => {
  if (!res?.success || !Array.isArray(res.poems) || !res.poems.length) {
    toast(res?.status === 'retake' ? '这张照片不够清楚，请再拍一次' : (res?.error || '暂未找到合适的古诗'))
    return
  }

  const loadedCandidates = await Promise.all(res.poems.slice(0, 3).map(loadPoemDetail))
  matchedPoem.value = loadedCandidates[0] || null
  resultCandidates.value = matchedPoem.value
    ? [...loadedCandidates.slice(1), matchedPoem.value]
    : loadedCandidates
  pageState.value = 'result'
}

const recognizeByLocalImage = async (imagePath) => {
  const ready = await ensureImageModelReady()
  if (!ready) return

  const terminalResult = await analyzeLocalImage(imagePath)
  if (terminalResult?.state !== 'success' || !terminalResult.analysis) {
    toast(terminalResult?.message || '端侧图片识别失败，请再拍一次')
    return
  }

  const candidates = await API.findPoemCandidates(terminalResult.analysis)
  await handleCandidateResult(candidates)
}

const recognizeSelectedImage = async (chooseResult) => {
  // #ifdef APP-PLUS
  const imagePath = getNativeImagePath(chooseResult)
  if (!imagePath) throw new Error('没有获取到图片路径')
  await recognizeByLocalImage(imagePath)
  // #endif

  // #ifndef APP-PLUS
  const imageBase64 = await fileToBase64(chooseResult)
  await recognizeByBase64(imageBase64)
  // #endif
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

  speakText('拍照')

  recognizing.value = true

  try {
    const photoRes = await chooseCameraBySystem()

    uni.showLoading({
      title: '识别中...'
    })

    await recognizeSelectedImage(photoRes)
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

  speakText('相册')

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

    await recognizeSelectedImage(chooseRes)
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
  font-family: "ShiyaZhenKai", "STKaiti", "KaiTi", "PingFang SC", serif;
  font-synthesis: none;
  color: #5b508d;
}
.camera-app {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: none;
  max-height: none;
  transform-origin: center center;
  will-change: transform;
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
  animation: scan-7b8d50ad 2.2s infinite ease-in-out;
}
@keyframes scan-7b8d50ad {
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
  -webkit-writing-mode: vertical-rl;
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
.camera-page {
  position: absolute;
  inset: 0;
  /* 原来 padding:7px 16px 14px; */
  padding: 2px 16px 14px; /* 顶部padding大幅减小，整个识别卡片向上靠紧标题 */
  display: grid;
  grid-template-columns: minmax(0, 1fr) 48px 92px;
  grid-template-rows: 58px minmax(0, 1fr);
  gap: 8px 12px;
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
  /* 原 padding:16px 20px; */
  padding: 8px 20px 16px; /* 顶部内边距缩小，内部全部元素上移 */
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
  display: block;
  color: #4e4775;
  overflow: hidden;
}
.poem-result-inner {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.poem-result.long-poem .poem-result-inner {
  justify-content: flex-start;
}
.poem-result.long-poem .result-title {
  font-size: 18px;
  letter-spacing: 3px;
}
.poem-result.long-poem .author {
  margin: 2px 0 4px;
  font-size: 12px;
}
.poem-result.long-poem .poem-lines {
  font-size: 14px;
  line-height: 1.42;
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
  top: 40px;
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
  font-size: 15px;
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

/* 最终版插画界面：业务逻辑仍沿用原 OCR 与相册/相机实现。 */
.final-camera-root {
  font-family: "ShiyaZhenKai", "STKaiti", "KaiTi", "PingFang SC", serif;
  font-synthesis: none;
}
.final-camera-app {
  position: relative;
  width: 1672px;
  height: 770px;
  max-width: none;
  max-height: none;
  flex: 0 0 auto;
  transform-origin: center;
  overflow: hidden;
  background: transparent;
}
.final-mode-page,
.final-result-page {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.final-mode-page { isolation: isolate; }
.camera-home-scene { position: absolute; inset: 0; width: 100%; height: 100%; overflow: hidden; pointer-events: none; -webkit-filter: blur(7px); filter: blur(7px); transform: scale(1.018); transform-origin: center; }
.camera-town-bg { position: absolute; inset: 0; width: 100%; height: 100%; }
.camera-home-brand { position: absolute; left: 18px; top: 0; width: 400px; height: 180px; z-index: 20; filter: drop-shadow(0 6px 5px rgba(84, 54, 24, .2)); }
.camera-home-brand image { width: 100%; }
.camera-home-age,
.camera-home-parent { position: absolute; top: 24px; height: 72px; z-index: 40; display: flex; align-items: center; justify-content: center; color: #744318; font-family: "PingFang SC", sans-serif; font-size: 34px; font-weight: 900; }
.camera-home-age { right: 216px; width: 178px; padding-right: 20px; }
.camera-home-parent { right: 30px; width: 168px; }
.camera-home-age image,
.camera-home-parent image { position: absolute; inset: 0; width: 100%; height: 100%; z-index: -1; }
.camera-home-entry { position: absolute; z-index: 5; }
.camera-home-entry image { position: absolute; max-width: none; max-height: none; }
.camera-home-camera { left: 109px; top: 149px; width: 440px; height: 330px; }
.camera-home-camera image { left: 0; top: 0; width: 440px; height: 330px; }
.camera-home-today { left: 606px; top: 83px; width: 447px; height: 463px; z-index: 9; }
.camera-home-today image { left: -232px; top: -22px; width: 900px; height: 500px; }
.camera-home-search { left: 105px; top: 395px; width: 521px; height: 294px; }
.camera-home-search image { left: 0; top: 0; width: 521px; height: 294px; }
.camera-home-practice { left: 1149px; top: 188px; width: 335px; height: 270px; }
.camera-home-practice image { left: 0; top: 0; width: 335px; height: 270px; }
.camera-home-stamps { left: 1120px; top: 412px; width: 450px; height: 250px; }
.camera-home-stamps image { left: 0; top: 0; width: 450px; height: 250px; }
.final-page-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.camera-popup-mask {
  position: absolute;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(55, 46, 30, .34);
  -webkit-backdrop-filter: none;
          backdrop-filter: none;
}
.camera-choice-popup {
  position: relative;
  z-index: 1001;
  width: 790px;
  height: 584px;
}
.camera-choice-popup > image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.camera-popup-title {
  position: absolute;
  left: 230px;
  top: 33px;
  width: 330px;
  height: 83px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #704117;
  font-size: 34px;
  font-weight: 900;
  letter-spacing: 5px;
}
.camera-popup-tip {
  position: absolute;
  left: 95px;
  top: 208px;
  width: 600px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  color: #79502a;
  font-size: 22px;
  font-weight: 900;
  letter-spacing: 3px;
}
.popup-close-hotspot,
.popup-action {
  position: absolute;
  padding: 0;
  border: 0;
  background: transparent;
  outline: none;
  box-shadow: none;
  -webkit-tap-highlight-color: transparent;
}
.popup-close-hotspot::after,
.popup-action::after,
.popup-close-hotspot:focus,
.popup-close-hotspot:active,
.popup-action:focus,
.popup-action:active,
.popup-action[disabled] {
  border: 0;
  outline: none;
  box-shadow: none;
  background: transparent;
}
.popup-close-hotspot { right: 82px; top: 63px; width: 58px; height: 60px; border-radius: 50%;
}
.popup-action { top: 424px; height: 97px;
}
.album-hotspot { left: 76px; width: 203px;
}
.camera-hotspot { left: 293px; width: 207px;
}
.back-hotspot { left: 508px; width: 202px;
}
.recognizing-tip { position: absolute; left: 230px; bottom: 200px; width: 330px; text-align: center; color: #7a4c22; font-size: 18px; font-weight: 900;
}
.final-back-hotspot {
  position: absolute;
  left: 24px;
  top: 30px;
  width: 130px;
  height: 105px;
  padding: 0;
  border: 0;
  background: transparent;
  z-index: 5;
}
.final-page-title {
  position: absolute;
  left: 505px;
  top: 60px;
  width: 665px;
  text-align: center;
  color: #704117;
  font-size: 48px;
  font-weight: 900;
  letter-spacing: 16px;
}
.mode-card {
  position: absolute;
  top: 180px;
  width: 510px;
  height: 548px;
  border-radius: 58px;
  border: 6px solid transparent;
  transition: transform .16s, box-shadow .16s;
  color: #704117;
}
.mode-card.poem-mode { left: 279px;
}
.mode-card.landscape-mode { left: 850px;
}
.mode-card.selected {
  border-color: rgba(213, 142, 54, .7);
  box-shadow: 0 0 0 10px rgba(255, 232, 166, .55), 0 14px 28px rgba(81, 52, 20, .18);
  transform: translateY(-8px);
}
.mode-title { position: absolute; left: 45px; right: 45px; bottom: 51px; text-align: center; font-size: 35px; font-weight: 900; letter-spacing: 8px;
}
.mode-sub { position: absolute; left: 0; right: 0; bottom: 7px; text-align: center; font-size: 20px; font-weight: 800; color: #9a6b3d;
}
.selected-mark { position: absolute; right: 18px; top: 18px; width: 55px; height: 55px; border-radius: 50%; background: #c98231; color: white; display: flex; align-items: center; justify-content: center; font: 900 34px/1 sans-serif;
}
.capture-actions { position: absolute; left: 475px; bottom: 18px; width: 720px; display: flex; gap: 26px;
}
.final-action { flex: 1; height: 72px; border: 4px solid #9c6429; border-radius: 20px; color: #623816; font-size: 26px; font-weight: 900;
}
.final-action.primary { background: #e4a64d; box-shadow: inset 0 3px rgba(255,255,255,.45);
}
.final-action.secondary { background: #fae4ba; box-shadow: inset 0 3px rgba(255,255,255,.55);
}
.capture-tip { position: absolute; left: 558px; bottom: 96px; width: 555px; text-align: center; color: #815a35; font-size: 20px; font-weight: 800;
}
.result-back-hotspot { position: absolute; left: 226px; top: 72px;
}
.result-back-native { z-index: 70; width: 142px; height: 112px; padding: 0; border: 0; background: transparent; }
.art-back { z-index: 70; width: 120px; height: 120px; padding: 0; border: 0; background: transparent; }
.art-back image { width: 100%; height: 100%; }
.result-page-title { position: absolute; left: 525px; top: 68px; width: 625px; text-align: center; color: #744319; font-size: 35px; font-weight: 900; letter-spacing: 3px;
}
.result-subtitle { position: absolute; left: 515px; top: 163px; width: 645px; text-align: center; color: #9a714b; font-size: 22px; font-weight: 800;
}
.result-cards { position: absolute; left: 264px; top: 230px; width: 1142px; height: 470px; display: flex; gap: 34px;
}
.result-poem-card { position: relative; flex: 1; padding: 8px 28px 18px; display: flex; flex-direction: column; align-items: center; color: #704117;
}
.result-poem-card.best { transform: none;
}
.result-poem-card:first-child { transform: translateX(10px); }
.result-poem-card:last-child { transform: translateX(-10px); }
.candidate-title { width: 100%; height: 68px; display: flex; align-items: center; justify-content: center; font-size: 38px; font-weight: 900; letter-spacing: 7px;
}
.candidate-title.long-title { font-size: 31px; letter-spacing: 2px; }
.candidate-title.extra-long-title { font-size: 27px; letter-spacing: 0; }
.candidate-author { width: 190px; height: 48px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #8a5b2f; font-weight: 800;
}
.candidate-lines { margin-top: 22px; display: flex; flex-direction: column; align-items: center; gap: 9px; font-size: 24px; font-weight: 800; transform: translateY(-18px);
}
.candidate-tags { margin-top: auto; margin-bottom: 58px; font-size: 18px; color: #956a40; font-weight: 800;
}
.open-poem-button { position: absolute; left: 50px; right: 50px; bottom: -10px; width: auto; height: 54px; padding: 0 0 10px; display: flex; align-items: center; justify-content: center; border: 3px solid #9b642d; border-radius: 15px; background: rgba(255, 239, 197, .58); box-shadow: inset 0 2px rgba(255,255,255,.5); color: #68401d; font-size: 23px; font-weight: 900;
}


/* 手机横屏可读性 */
.camera-popup-title { font-size: 46px; }
.camera-popup-tip { font-size: 38px; }
.recognizing-tip { font-size: 27px; }
.result-page-title { font-size: 44px; }
.result-subtitle { font-size: 32px; }
.candidate-title { font-size: 46px; }
.candidate-title.long-title { font-size: 36px; letter-spacing: 1px; }
.candidate-title.extra-long-title { font-size: 30px; letter-spacing: 0; }
.candidate-author { font-size: 30px; }
.candidate-lines { font-size: 34px; }
.candidate-tags { font-size: 27px; }
.open-poem-button { font-size: 32px; }
</style>
