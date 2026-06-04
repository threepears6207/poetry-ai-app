<template>
  <view class="page-root">
    <view class="video-app">
      <view v-if="isImageLoading" class="loading-screen">
        <view class="loading-cloud loading-cloud-one">☁️</view>
        <view class="loading-cloud loading-cloud-two">☁️</view>
        <view class="loading-moon">月</view>
        <view class="loading-bamboo loading-bamboo-left">🎋</view>
        <view class="loading-bamboo loading-bamboo-right">🎋</view>

        <view class="loading-card">
          <view class="loading-icon-wrap">
            <view class="loading-scroll">📜</view>
            <view class="loading-brush">🖌️</view>
          </view>

          <view class="loading-title">正在为《{{ poemData.title }}》作画</view>
          <view class="loading-desc">{{ loadingMessage }}</view>
          <view class="loading-line">{{ loadingPoemLine }}</view>

          <view class="loading-progress-track">
            <view class="loading-progress-bar" :style="{ width: loadingPercent + '%' }"></view>
          </view>

          <view class="loading-foot">
            <text>诗芽小学堂</text>
            <text>{{ loadingPercent }}%</text>
          </view>
        </view>
      </view>

      <view class="topbar">
        <button class="back-btn" @tap="goBack">‹</button>

        <view class="title-pill">
          正在播放：{{ poemData.title }}
        </view>

        <button
          class="done-btn"
          :class="{ disabled: !canFinishStudy }"
          :disabled="!canFinishStudy"
          @tap="finishStudy"
        >
          {{ canFinishStudy ? '看完了 ✓' : '播放中…' }}
        </button>
      </view>

      <view class="video-stage">
        <image
          v-for="(frame, index) in aiFrames"
          :key="frame.frame_key || `${index}-${frame.image_url}`"
          class="ai-frame-image"
          :class="{ active: currentFrameIndex === index }"
          :src="frame.image_url"
          mode="aspectFill"
          @error="handleFrameImageError(index, $event)"
        ></image>

        <template v-if="!hasFrameImages">
          <view class="sun"></view>
          <view class="cloud cloud-one">☁️</view>
          <view class="cloud cloud-two">☁️</view>
          <view class="mountain mountain-one"></view>
          <view class="mountain mountain-two"></view>
          <view class="willow">🌿</view>
          <view class="bird bird-one">🐦</view>
          <view class="bird bird-two">🐦</view>

          <view class="scene-card">
            <view class="scene-child">👧</view>
            <view class="scene-bed">🛏️</view>
            <view class="scene-text">{{ sceneText }}</view>
          </view>
        </template>
      </view>

      <view class="subtitle-box">
        <button
          class="voice-btn"
          :class="{ playing: isPlayingAudio }"
          :disabled="ttsLoading"
          @tap.stop="toggleReadPoem"
        >
          {{ ttsLoading ? '…' : isPlayingAudio ? '🔊' : '🔈' }}
        </button>

        <view class="subtitle-text">
          <text class="active-text">{{ subtitleFirst }}</text>
          <text v-if="subtitleSecond">，{{ subtitleSecond }}。</text>
        </view>

        <view class="progress-track">
          <view class="progress-bar" :style="{ width: progressPercent + '%' }"></view>
        </view>
      </view>

      <view v-if="showGuide" class="guide-mask">
        <view class="guide-card">
          <view class="guide-avatar-wrap">
            <image class="guide-avatar" :src="poetAvatarImage" mode="aspectFill" @error="handlePoetAvatarError"></image>
          </view>

          <view class="guide-content">
            <view class="guide-title">太棒了！我们一起看完了</view>

            <view class="guide-text">
              我是作者<text class="orange-text">{{ poemData.author }}</text>，想知道我写这首诗的时候在想什么吗？快来聊聊吧！
            </view>

            <view class="guide-buttons">
              <button class="guide-btn white-btn" @tap="replayStudy">再看一遍</button>
              <button class="guide-btn orange-btn" @tap="goChat">和诗人聊聊天 💬</button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onUnload, onHide } from '@dcloudio/uni-app'
import { API, getLocalPoemById, normalizeAssetUrl, getPoetAvatarStaticUrl } from '@/utils/api.js'

const showGuide = ref(false)
const poemId = ref('poem_001')
const poemData = ref(getLocalPoemById('poem_001'))
const ttsLoading = ref(false)
const isPlayingAudio = ref(false)
const aiFrames = ref([])
const currentFrameIndex = ref(0)
const progressPercent = ref(0)
const playbackCompleted = ref(false)
const isImageLoading = ref(true)
const loadingPercent = ref(6)
const loadingMessage = ref('正在铺开画卷，请稍等一下')
const poetAvatarUrl = ref('')

let audioContext = null
let studyStartTime = Date.now()
let studyRecorded = false
let frameTimer = null
let progressTimer = null
let loadingTimer = null
let audioRequestToken = 0
let pageAlive = true

// 分镜播放稍微加速一点：后端 3000ms 一张，前端按 75% 播放。
const FRAME_PLAYBACK_SPEED = 0.75

const sceneText = computed(() => {
  if (poemData.value.title === '春晓') return '春天的早晨，睡得香香的。'
  if (poemData.value.title === '静夜思') return '夜晚月光亮亮的，想起远方的家。'
  if (poemData.value.title === '咏鹅') return '白鹅在水里快乐地游来游去。'
  if (poemData.value.title === '悯农') return '每一粒米饭都来得很辛苦。'
  return '一起走进古诗里的画面吧。'
})

const poemText = computed(() => {
  if (Array.isArray(poemData.value.content)) {
    return poemData.value.content.join('，')
  }

  return String(poemData.value.content || '')
})

const poemLines = computed(() => {
  if (Array.isArray(poemData.value.content)) {
    return poemData.value.content
  }

  return String(poemData.value.content || '')
    .split(/[，,。；;！!？?\n]/)
    .map((line) => line.trim())
    .filter(Boolean)
})

const getPoemStaticFrameUrl = (index, options = {}) => {
  const { useTitle = false, ext = 'jpg' } = options
  const id = poemData.value.id || poemData.value.poem_id || poemId.value
  const title = poemData.value.title || poemData.value.poem_title || ''
  const folder = useTitle ? title : id

  if (!folder && folder !== 0) return ''

  return normalizeAssetUrl(`/static/images/poems/${folder}/frame_${index}.${ext}`)
}

const getFrameFallbackUrls = (index) => {
  return [
    getPoemStaticFrameUrl(index, { ext: 'jpg' }),
    getPoemStaticFrameUrl(index, { ext: 'png' }),
    getPoemStaticFrameUrl(index, { useTitle: true, ext: 'jpg' }),
    getPoemStaticFrameUrl(index, { useTitle: true, ext: 'png' })
  ].filter(Boolean)
    .filter((url, urlIndex, arr) => arr.indexOf(url) === urlIndex)
}

const getPoetName = () => {
  return poemData.value.author || poemData.value.poet_name || '古代诗人'
}

const getPoetDynasty = () => {
  return poemData.value.dynasty || '唐'
}

const loadingPoemLine = computed(() => {
  return poemLines.value[0] || poemText.value || '让诗句慢慢变成画面'
})

const poetAvatarImage = computed(() => {
  return poetAvatarUrl.value || getPoetAvatarStaticUrl(getPoetName()) || '/static/孟浩然.png'
})

const currentFrame = computed(() => {
  return aiFrames.value[currentFrameIndex.value] || null
})

const currentFrameImage = computed(() => {
  return currentFrame.value?.image_url || ''
})

const hasFrameImages = computed(() => {
  return aiFrames.value.length > 0
})

const canFinishStudy = computed(() => {
  return playbackCompleted.value && !isImageLoading.value
})

const subtitleFirst = computed(() => {
  if (currentFrame.value?.line) {
    return currentFrame.value.line
  }

  return poemLines.value[0] || ''
})

const subtitleSecond = computed(() => {
  if (currentFrame.value?.line) {
    return ''
  }

  return poemLines.value[1] || ''
})

const handlePoetAvatarError = () => {
  if (poetAvatarUrl.value) {
    poetAvatarUrl.value = ''
    return
  }

  console.log('诗人头像加载失败，使用本地默认头像')
}

const clearLoadingTimer = () => {
  if (loadingTimer) {
    clearInterval(loadingTimer)
    loadingTimer = null
  }
}

const startImageLoadingProgress = () => {
  clearLoadingTimer()
  isImageLoading.value = true
  loadingPercent.value = 6
  loadingMessage.value = '正在铺开画卷，请稍等一下'

  const startTime = Date.now()

  loadingTimer = setInterval(() => {
    const elapsed = Date.now() - startTime
    const nextPercent = Math.min(92, 6 + Math.round((elapsed / 120000) * 86))
    loadingPercent.value = Math.max(loadingPercent.value, nextPercent)

    if (loadingPercent.value < 30) {
      loadingMessage.value = '正在理解诗句里的景色和情绪'
    } else if (loadingPercent.value < 62) {
      loadingMessage.value = '正在画出连续的小分镜'
    } else if (loadingPercent.value < 88) {
      loadingMessage.value = '正在整理图片资源，缓存后下次会更快'
    } else {
      loadingMessage.value = '快完成啦，马上进入播放'
    }
  }, 700)
}

const finishImageLoading = (callback) => {
  clearLoadingTimer()
  loadingPercent.value = 100
  loadingMessage.value = '画面准备好了，马上播放'

  setTimeout(() => {
    isImageLoading.value = false

    if (typeof callback === 'function') {
      callback()
    }
  }, 360)
}

const stopImageLoadingWithFallback = () => {
  clearLoadingTimer()
  loadingPercent.value = 100
  loadingMessage.value = '配图暂不可用，先用默认动画继续观看'

  setTimeout(() => {
    isImageLoading.value = false
  }, 520)
}

const handleFrameImageError = (index, err) => {
  const frame = aiFrames.value[index]
  const failedUrls = Array.isArray(frame?.failed_urls) ? frame.failed_urls : []
  const currentUrl = frame?.image_url || ''
  const fallbackUrls = Array.isArray(frame?.fallback_urls) ? frame.fallback_urls : []

  const nextUrl = fallbackUrls.find((url) => {
    return url && url !== currentUrl && !failedUrls.includes(url)
  })

  console.log('分镜图片加载失败：', {
    index,
    image_url: currentUrl,
    next_url: nextUrl,
    error: err
  })

  if (nextUrl) {
    aiFrames.value.splice(index, 1, {
      ...frame,
      image_url: nextUrl,
      frame_key: `${frame.index ?? index}-${nextUrl}`,
      failed_urls: [...failedUrls, currentUrl].filter(Boolean)
    })
  }
}

const clearFrameTimers = () => {
  if (frameTimer) {
    clearTimeout(frameTimer)
    frameTimer = null
  }

  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

const startFramePlayback = (options = {}) => {
  const { autoRead = true } = options

  clearFrameTimers()
  playbackCompleted.value = false

  if (!aiFrames.value.length) {
    progressPercent.value = 100
    playbackCompleted.value = true
    return
  }

  currentFrameIndex.value = 0
  progressPercent.value = 0

  if (autoRead) {
    playPoemAudio({
      restart: true,
      silent: true
    })
  }

  const durations = aiFrames.value.map((item) => {
    const duration = Number(item.duration_ms || item.duration || 3000)
    const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : 3000

    return Math.max(650, Math.round(safeDuration * FRAME_PLAYBACK_SPEED))
  })

  const totalDuration = durations.reduce((sum, item) => sum + item, 0)

  if (!totalDuration) {
    progressPercent.value = 0
    return
  }

  const startTime = Date.now()

  progressTimer = setInterval(() => {
    const used = Date.now() - startTime
    progressPercent.value = Math.min(100, Math.round((used / totalDuration) * 100))
  }, 120)

  const playFrame = (index) => {
    currentFrameIndex.value = index

    frameTimer = setTimeout(() => {
      if (index >= aiFrames.value.length - 1) {
        progressPercent.value = 100
        playbackCompleted.value = true
        clearFrameTimers()
        return
      }

      playFrame(index + 1)
    }, durations[index])
  }

  playFrame(0)
}

const normalizeFrameList = (rawFrames = []) => {
  const frameMap = new Map()

  rawFrames.forEach((item = {}, fallbackIndex) => {
    const frameIndex = Number(item.index ?? fallbackIndex)
    const safeIndex = Number.isFinite(frameIndex) ? frameIndex : fallbackIndex
    const imageUrl = (
      item.image_url ||
      item.imageUrl ||
      item.local_url ||
      item.localUrl ||
      item.local_path ||
      item.localPath ||
      item.image_path ||
      item.imagePath ||
      item.path ||
      item.url ||
      item.image ||
      item.src ||
      ''
    )

    const normalizedImageUrl = normalizeAssetUrl(imageUrl)
    const duration = Number(item.duration_ms || item.duration || 3000)
    const fallbackUrls = getFrameFallbackUrls(safeIndex)
    const imageUrlForDisplay = normalizedImageUrl || fallbackUrls[0] || ''

    frameMap.set(safeIndex, {
      ...item,
      index: safeIndex,
      frame_key: `${safeIndex}-${imageUrlForDisplay}`,
      line: item.line || poemLines.value[safeIndex] || '',
      image_url: imageUrlForDisplay,
      fallback_urls: normalizedImageUrl
        ? [normalizedImageUrl, ...fallbackUrls].filter((url, urlIndex, arr) => arr.indexOf(url) === urlIndex)
        : fallbackUrls,
      duration_ms: Number.isFinite(duration) && duration > 0 ? Math.max(800, duration) : 3000
    })
  })

  // 以诗句数量为准补齐缺失图片。
  // 解决“春晓后端 static 已有 4 张，但接口/缓存只返回 2 张时前端只能播 2 张”的问题。
  poemLines.value.forEach((line, index) => {
    if (!frameMap.has(index)) {
      const fallbackUrls = getFrameFallbackUrls(index)
      const imageUrlForDisplay = fallbackUrls[0] || ''

      frameMap.set(index, {
        index,
        frame_key: `${index}-${imageUrlForDisplay}`,
        line,
        image_url: imageUrlForDisplay,
        fallback_urls: fallbackUrls,
        duration_ms: 3000,
        from_static_fallback: true
      })
    }
  })

  return Array.from(frameMap.values())
    .filter((item) => item.image_url)
    .sort((a, b) => a.index - b.index)
}

const loadPoetAvatar = async () => {
  const poetName = getPoetName()
  const dynasty = getPoetDynasty()

  // 先直接尝试后端静态目录里的头像，比如 /static/images/poets/李白.jpg。
  // 这样即使生成接口暂时不可用，已有图片也能显示。
  poetAvatarUrl.value = getPoetAvatarStaticUrl(poetName)

  try {
    const res = await API.generatePoetAvatar({
      poet_name: poetName,
      dynasty
    })

    const avatarUrl = res?.avatar_url || res?.data?.avatar_url || ''

    if (res?.success && avatarUrl) {
      poetAvatarUrl.value = normalizeAssetUrl(avatarUrl)
    }
  } catch (err) {
    console.log('诗人形象接口暂不可用，继续使用静态头像', err)
  }
}

const loadAiFrames = async () => {
  startImageLoadingProgress()

  try {
    const res = await API.generateImage(poemData.value)

    const rawFrames = res?.frames || res?.data?.frames || []

    if (!res?.success || !Array.isArray(rawFrames) || !rawFrames.length) {
      console.log('AI 配图暂不可用，使用默认动画', res)
      progressPercent.value = 0
      stopImageLoadingWithFallback()
      return
    }

    if (res?.from_cache || res?.data?.from_cache) {
      loadingMessage.value = '缓存命中，马上进入播放'
    }

    aiFrames.value = normalizeFrameList(rawFrames)

    if (!aiFrames.value.length) {
      stopImageLoadingWithFallback()
      return
    }

    finishImageLoading(() => {
      startFramePlayback({
        autoRead: true
      })
    })
  } catch (err) {
    console.log('AI 配图接口暂不可用，使用默认动画', err)
    progressPercent.value = 0
    stopImageLoadingWithFallback()
  }
}

onLoad(async (options) => {
  pageAlive = true
  studyStartTime = Date.now()
  studyRecorded = false
  poemId.value = options.poem_id || 'poem_001'
  poemData.value = getLocalPoemById(poemId.value)
  aiFrames.value = []
  currentFrameIndex.value = 0
  progressPercent.value = 0
  playbackCompleted.value = false
  poetAvatarUrl.value = ''
  isImageLoading.value = true
  loadingPercent.value = 6
  loadingMessage.value = '正在铺开画卷，请稍等一下'
  clearFrameTimers()
  clearLoadingTimer()

  try {
    const detailRes = await API.getPoemDetail(poemId.value)

    if (detailRes && detailRes.success && detailRes.data) {
      poemData.value = detailRes.data
    }
  } catch (err) {
    console.log('古诗详情接口暂不可用，使用本地数据', err)
  }

  loadPoetAvatar()
  loadAiFrames()
})

const toast = (title) => {
  uni.showToast({
    title,
    icon: 'none'
  })
}

const recordStudyOnce = async () => {
  if (studyRecorded) return

  const usedSeconds = Math.max(1, Math.round((Date.now() - studyStartTime) / 1000))

  try {
    await API.addRecord(poemId.value, usedSeconds)
    studyRecorded = true
  } catch (err) {
    console.log('学习记录接口暂不可用，先跳过', err)
  }
}

const finishStudy = async () => {
  if (!canFinishStudy.value) {
    toast('先完整看完一遍哦')
    return
  }

  stopAudio()
  clearFrameTimers()
  await recordStudyOnce()
  showGuide.value = true
}

const stopAudio = (options = {}) => {
  const { cancelPending = true } = options

  if (cancelPending) {
    audioRequestToken += 1
  }
  if (audioContext) {
    try {
      audioContext.stop()
      audioContext.destroy()
    } catch (err) {
      console.log('停止朗读失败：', err)
    }

    audioContext = null
  }

  isPlayingAudio.value = false
}

const playPoemAudio = async (options = {}) => {
  const { restart = false, silent = false } = options

  if (ttsLoading.value) return

  if (isPlayingAudio.value) {
    if (!restart) return
    stopAudio()
  }

  const text = poemText.value.trim()

  if (!text) {
    if (!silent) toast('暂无可朗读的诗句')
    return
  }

  const requestToken = audioRequestToken + 1
  audioRequestToken = requestToken
  ttsLoading.value = true

  try {
    const res = await API.textToSpeech(text, 'child')

    if (requestToken !== audioRequestToken || !pageAlive) {
      return
    }

    const audioUrl = res?.audio_url || res?.url || res?.data?.audio_url || res?.data?.url || ''

    if (res && res.success && audioUrl) {
      stopAudio({
        cancelPending: false
      })

      audioContext = uni.createInnerAudioContext()
      audioContext.src = normalizeAssetUrl(audioUrl)
      audioContext.autoplay = true

      audioContext.onEnded(() => {
        stopAudio()
      })

      audioContext.onError((err) => {
        console.log('朗读播放失败：', err)
        stopAudio()
        if (!silent) toast('朗读播放失败')
      })

      isPlayingAudio.value = true
      audioContext.play()
    } else if (!silent) {
      toast(res?.message || res?.error || '语音生成失败')
    }
  } catch (err) {
    console.log('语音朗读接口失败：', err)
    if (!silent && requestToken === audioRequestToken && pageAlive) {
      toast('语音朗读暂不可用')
    }
  } finally {
    if (requestToken === audioRequestToken) {
      ttsLoading.value = false
    }
  }
}

const toggleReadPoem = async () => {
  if (isPlayingAudio.value) {
    stopAudio()
    return
  }

  await playPoemAudio({
    restart: false,
    silent: false
  })
}

const replayStudy = () => {
  showGuide.value = false
  studyStartTime = Date.now()
  studyRecorded = false
  playbackCompleted.value = false
  startFramePlayback({
    autoRead: true
  })
}

const cleanupStudyPlayback = () => {
  pageAlive = false
  stopAudio()
  clearFrameTimers()
  clearLoadingTimer()
}

onHide(() => {
  cleanupStudyPlayback()
})

onUnload(() => {
  cleanupStudyPlayback()
})

const goBack = () => {
  cleanupStudyPlayback()

  uni.navigateBack({
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = '#/pages/index/index'
      }
    }
  })
}

const goChat = () => {
  cleanupStudyPlayback()

  uni.navigateTo({
    url: `/pages/chat/chat?poem_id=${poemData.value.id}`,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = `#/pages/chat/chat?poem_id=${poemData.value.id}`
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
}

.video-app {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: 100vw;
  max-height: 100vh;
  background: #fffbf0;
  overflow: hidden;
  border-radius: 0;
}

.topbar {
  position: absolute;
  top: 7px;
  left: 16px;
  right: 16px;
  height: 44px;
  z-index: 50;
}

.back-btn {
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
}

.title-pill {
  position: absolute;
  left: 50%;
  top: 0;
  transform: translateX(-50%);
  height: 42px;
  min-width: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  padding: 6px 18px;
  border-radius: 999px;
  border: 4px solid #ffe057;
  color: #5d4e8c;
  font-size: 17px;
  font-weight: 950;
}

.done-btn {
  position: absolute;
  right: 0;
  top: 4px;
  height: 36px;
  background: #66cdaa;
  color: #ffffff;
  font-size: 15px;
  font-weight: 900;
  border-radius: 999px;
  border: 0;
  padding: 0 22px;
  box-shadow: 0 7px 16px rgba(102, 205, 170, 0.28);
}

.done-btn.disabled,
.done-btn[disabled] {
  opacity: 0.55;
  background: #c8c0dc;
  color: #ffffff;
  box-shadow: none;
}

.video-stage {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, #e0f2fe, #fef3c7);
  overflow: hidden;
}

.ai-frame-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  opacity: 0;
  transition: opacity 0.28s ease;
  pointer-events: none;
}

.ai-frame-image.active {
  opacity: 1;
  z-index: 2;
}

.sun {
  position: absolute;
  top: 58px;
  left: 82px;
  width: 56px;
  height: 56px;
  background: #ffd93d;
  border-radius: 50%;
  box-shadow: 0 0 30px rgba(255, 217, 61, 0.55);
}

.cloud {
  position: absolute;
  font-size: 48px;
  opacity: 0.66;
  animation: cloudFloat 8s ease-in-out infinite;
}

.cloud-one {
  top: 84px;
  left: 250px;
}

.cloud-two {
  top: 126px;
  right: 210px;
  animation-delay: 1.2s;
}

@keyframes cloudFloat {
  50% {
    transform: translateX(34px);
  }
}

.mountain {
  position: absolute;
  bottom: 0;
  width: 380px;
  height: 175px;
  clip-path: polygon(50% 0%, 100% 100%, 0 100%);
  background: rgba(102, 205, 170, 0.28);
}

.mountain-one {
  left: 30px;
}

.mountain-two {
  right: 70px;
  background: rgba(93, 78, 140, 0.13);
}

.willow {
  position: absolute;
  right: 145px;
  bottom: 112px;
  font-size: 68px;
  animation: sway 4s ease-in-out infinite;
}

@keyframes sway {
  50% {
    transform: rotate(4deg);
  }
}

.bird {
  position: absolute;
  font-size: 30px;
  animation: birdFly 7s linear infinite;
}

.bird-one {
  top: 130px;
  left: 200px;
}

.bird-two {
  top: 170px;
  left: 395px;
  animation-delay: 1.2s;
}

@keyframes birdFly {
  0% {
    transform: translate(-80px, 20px);
  }

  50% {
    transform: translate(130px, -20px);
  }

  100% {
    transform: translate(-80px, 20px);
  }
}

.scene-card {
  position: absolute;
  left: 50%;
  top: 52%;
  transform: translate(-50%, -50%);
  width: 350px;
  height: 142px;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.52);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
}

.scene-child,
.scene-bed {
  font-size: 54px;
}

.scene-text {
  width: 118px;
  color: #5d4e8c;
  font-size: 16px;
  font-weight: 900;
  line-height: 1.5;
}

.subtitle-box {
  position: absolute;
  left: 50%;
  bottom: 24px;
  transform: translateX(-50%);
  width: 70%;
  background: rgba(255, 255, 255, 0.9);
  padding: 10px 24px 10px 62px;
  border-radius: 24px;
  text-align: center;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
  border: 2px solid #fff;
  z-index: 30;
}

.voice-btn {
  position: absolute;
  left: 18px;
  top: 10px;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #fff2cc;
  color: #5d4e8c;
  font-size: 18px;
  line-height: 34px;
  text-align: center;
  box-shadow: 0 4px 0 rgba(255, 190, 75, 0.7);
}

.voice-btn.playing {
  background: #e0f2fe;
  color: #2563eb;
  box-shadow: 0 4px 0 rgba(96, 165, 250, 0.55);
}

.voice-btn[disabled] {
  opacity: 0.72;
}

.subtitle-text {
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 4px;
  color: #5d4e8c;
}

.active-text {
  color: #ff8e53;
}

.progress-track {
  width: 100%;
  height: 5px;
  background: #eeeeee;
  border-radius: 999px;
  margin-top: 12px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  width: 0;
  background: #ff8e53;
  border-radius: 999px;
  transition: width 0.12s linear;
}


.loading-screen {
  position: absolute;
  inset: 0;
  z-index: 200;
  overflow: hidden;
  background:
    radial-gradient(circle at 16% 20%, rgba(255, 224, 87, 0.4), transparent 24%),
    radial-gradient(circle at 85% 18%, rgba(102, 205, 170, 0.24), transparent 25%),
    linear-gradient(180deg, #fffaf0 0%, #fff2db 45%, #e8f8ee 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-cloud {
  position: absolute;
  font-size: 46px;
  opacity: 0.72;
  animation: loadingCloudFloat 7s ease-in-out infinite;
}

.loading-cloud-one {
  left: 92px;
  top: 70px;
}

.loading-cloud-two {
  right: 94px;
  top: 105px;
  animation-delay: 1.1s;
}

@keyframes loadingCloudFloat {
  50% {
    transform: translateX(28px) translateY(-4px);
  }
}

.loading-moon {
  position: absolute;
  right: 168px;
  top: 40px;
  width: 62px;
  height: 62px;
  border-radius: 50%;
  background: #fff7bf;
  box-shadow: 0 0 32px rgba(255, 214, 86, 0.42);
  display: grid;
  place-items: center;
  color: #c89a34;
  font-size: 20px;
  font-weight: 950;
}

.loading-bamboo {
  position: absolute;
  bottom: 18px;
  font-size: 64px;
  opacity: 0.72;
  animation: loadingSway 4s ease-in-out infinite;
}

.loading-bamboo-left {
  left: 70px;
}

.loading-bamboo-right {
  right: 70px;
  animation-delay: 0.9s;
}

@keyframes loadingSway {
  50% {
    transform: rotate(4deg) translateY(-3px);
  }
}

.loading-card {
  position: relative;
  z-index: 3;
  width: 468px;
  min-height: 230px;
  border-radius: 34px;
  padding: 24px 34px 22px;
  background: rgba(255, 255, 255, 0.9);
  border: 4px solid rgba(255, 224, 87, 0.78);
  box-shadow: 0 24px 48px rgba(109, 82, 46, 0.16);
  text-align: center;
}

.loading-icon-wrap {
  position: relative;
  width: 88px;
  height: 60px;
  margin: 0 auto 8px;
}

.loading-scroll {
  position: absolute;
  left: 9px;
  top: 8px;
  font-size: 42px;
}

.loading-brush {
  position: absolute;
  right: 6px;
  top: 0;
  font-size: 40px;
  transform-origin: 30% 80%;
  animation: brushPaint 1.35s ease-in-out infinite;
}

@keyframes brushPaint {
  0%, 100% {
    transform: rotate(-12deg) translateY(0);
  }

  50% {
    transform: rotate(18deg) translateY(6px);
  }
}

.loading-title {
  color: #5d4e8c;
  font-size: 24px;
  font-weight: 950;
  letter-spacing: 1px;
}

.loading-desc {
  margin-top: 8px;
  color: #7a719c;
  font-size: 14px;
  font-weight: 850;
}

.loading-line {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  margin-top: 12px;
  padding: 6px 18px;
  border-radius: 999px;
  background: #fff7df;
  color: #ff8e53;
  font-size: 17px;
  font-weight: 950;
  letter-spacing: 3px;
}

.loading-progress-track {
  width: 100%;
  height: 12px;
  margin-top: 18px;
  border-radius: 999px;
  background: #efeaf8;
  overflow: hidden;
  box-shadow: inset 0 2px 5px rgba(104, 85, 135, 0.1);
}

.loading-progress-bar {
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #66cdaa, #ffd93d, #ff8e53);
  transition: width 0.5s ease;
}

.loading-foot {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #8a80aa;
  font-size: 13px;
  font-weight: 900;
}

.guide-mask {
  position: absolute;
  inset: 0;
  background: rgba(93, 78, 140, 0.2);
  backdrop-filter: blur(8px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.guide-card {
  width: 650px;
  min-height: 240px;
  background: #ffffff;
  border-radius: 40px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.22);
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 30px;
}

.guide-avatar-wrap {
  width: 128px;
  height: 128px;
  background: #ffd93d;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.guide-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
}

.guide-content {
  flex: 1;
}

.guide-title {
  color: #5d4e8c;
  font-size: 25px;
  font-weight: 900;
}

.guide-text {
  margin-top: 10px;
  color: #666666;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.6;
}

.orange-text {
  color: #ff8e53;
  font-weight: 900;
}

.guide-buttons {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}

.guide-btn {
  border: 0;
  border-radius: 999px;
  padding: 9px 20px;
  font-size: 14px;
  font-weight: 900;
}

.orange-btn {
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: #fff;
  box-shadow: 0 5px 0 #f16012;
}

.white-btn {
  background: #fff;
  color: #6a5f97;
  box-shadow: 0 5px 0 rgba(220, 211, 236, 0.9);
}
</style>
