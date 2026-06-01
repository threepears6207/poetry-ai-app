<template>
  <view class="page-root">
    <view class="video-app">
      <view class="topbar">
        <button class="back-btn" @tap="goBack">‹</button>

        <view class="title-pill">
          正在播放：{{ poemData.title }}
        </view>

        <button class="done-btn" @tap="finishStudy">
          播完了 ✓
        </button>
      </view>

      <view class="video-stage">
        <image
          v-if="currentFrameImage"
          class="ai-frame-image"
          :src="currentFrameImage"
          mode="aspectFill"
        ></image>

        <template v-if="!currentFrameImage">
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
            <image class="guide-avatar" src="/static/孟浩然.png" mode="aspectFill"></image>
          </view>

          <view class="guide-content">
            <view class="guide-title">太棒了！我们一起看完了</view>

            <view class="guide-text">
              我是作者<text class="orange-text">{{ poemData.author }}</text>，想知道我写这首诗的时候在想什么吗？快来聊聊吧！
            </view>

            <view class="guide-buttons">
              <button class="guide-btn white-btn" @tap="showGuide = false">再看一遍</button>
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
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { API, getLocalPoemById, normalizeAssetUrl } from '@/utils/api.js'

const showGuide = ref(false)
const poemId = ref('poem_001')
const poemData = ref(getLocalPoemById('poem_001'))
const ttsLoading = ref(false)
const isPlayingAudio = ref(false)
const aiFrames = ref([])
const currentFrameIndex = ref(0)
const progressPercent = ref(0)

let audioContext = null
let studyStartTime = Date.now()
let studyRecorded = false
let frameTimer = null
let progressTimer = null

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

const currentFrame = computed(() => {
  return aiFrames.value[currentFrameIndex.value] || null
})

const currentFrameImage = computed(() => {
  return currentFrame.value?.image_url || ''
})

const subtitleFirst = computed(() => {
  if (currentFrame.value?.line) {
    return currentFrame.value.line
  }

  return poemData.value.content?.[0] || ''
})

const subtitleSecond = computed(() => {
  if (currentFrame.value?.line) {
    return ''
  }

  return poemData.value.content?.[1] || ''
})

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

const startFramePlayback = () => {
  clearFrameTimers()

  if (!aiFrames.value.length) {
    progressPercent.value = 0
    return
  }

  currentFrameIndex.value = 0
  progressPercent.value = 0

  const durations = aiFrames.value.map((item) => {
    return Number(item.duration_ms || item.duration || 3000)
  })

  const totalDuration = durations.reduce((sum, item) => sum + item, 0)
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
        clearFrameTimers()
        return
      }

      playFrame(index + 1)
    }, durations[index])
  }

  playFrame(0)
}

const loadAiFrames = async () => {
  try {
    const res = await API.generateImage(poemData.value)

    const rawFrames = res?.frames || res?.data?.frames || []

    if (!res?.success || !Array.isArray(rawFrames) || !rawFrames.length) {
      console.log('AI 配图暂不可用，使用默认动画', res)
      progressPercent.value = 0
      return
    }

    aiFrames.value = rawFrames
      .map((item, index) => {
        const imageUrl = item.image_url || item.url || item.image || ''

        return {
          ...item,
          index: Number(item.index ?? index),
          line: item.line || poemData.value.content?.[index] || '',
          image_url: normalizeAssetUrl(imageUrl),
          duration_ms: Number(item.duration_ms || item.duration || 3000)
        }
      })
      .filter((item) => item.image_url)
      .sort((a, b) => a.index - b.index)

    startFramePlayback()
  } catch (err) {
    console.log('AI 配图接口暂不可用，使用默认动画', err)
    progressPercent.value = 0
  }
}

onLoad(async (options) => {
  studyStartTime = Date.now()
  studyRecorded = false
  poemId.value = options.poem_id || 'poem_001'
  poemData.value = getLocalPoemById(poemId.value)
  aiFrames.value = []
  currentFrameIndex.value = 0
  progressPercent.value = 0
  clearFrameTimers()

  try {
    const detailRes = await API.getPoemDetail(poemId.value)

    if (detailRes && detailRes.success && detailRes.data) {
      poemData.value = detailRes.data
    }
  } catch (err) {
    console.log('古诗详情接口暂不可用，使用本地数据', err)
  }

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

  const usedSeconds = Math.max(30, Math.round((Date.now() - studyStartTime) / 1000))

  try {
    await API.addRecord(poemId.value, usedSeconds)
    studyRecorded = true
  } catch (err) {
    console.log('学习记录接口暂不可用，先跳过', err)
  }
}

const finishStudy = async () => {
  await recordStudyOnce()
  showGuide.value = true
}

const stopAudio = () => {
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

const toggleReadPoem = async () => {
  if (isPlayingAudio.value) {
    stopAudio()
    return
  }

  if (ttsLoading.value) return

  const text = poemText.value.trim()

  if (!text) {
    toast('暂无可朗读的诗句')
    return
  }

  ttsLoading.value = true

  try {
    const res = await API.textToSpeech(text, 'child')

    const audioUrl = res?.audio_url || res?.url || res?.data?.audio_url || res?.data?.url || ''

    if (res && res.success && audioUrl) {
      stopAudio()

      audioContext = uni.createInnerAudioContext()
      audioContext.src = normalizeAssetUrl(audioUrl)
      audioContext.autoplay = true

      audioContext.onEnded(() => {
        stopAudio()
      })

      audioContext.onError((err) => {
        console.log('朗读播放失败：', err)
        stopAudio()
        toast('朗读播放失败')
      })

      isPlayingAudio.value = true
      audioContext.play()
    } else {
      toast(res?.message || res?.error || '语音生成失败')
    }
  } catch (err) {
    console.log('语音朗读接口失败：', err)
    toast('语音朗读暂不可用')
  } finally {
    ttsLoading.value = false
  }
}

onUnload(() => {
  stopAudio()
  clearFrameTimers()
})

const goBack = () => {
  uni.navigateBack({
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = '#/pages/index/index'
      }
    }
  })
}

const goChat = () => {
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

.video-stage {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, #e0f2fe, #fef3c7);
  overflow: hidden;
}

.ai-frame-image {
  width: 100%;
  height: 100%;
  display: block;
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
