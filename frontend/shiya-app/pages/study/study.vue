<template>
  <view class="page-root">
    <view class="study-app">
      <view class="page">
        <view class="topbar">
          <button class="back" @tap="goBack">‹</button>

          <view class="title-pill">
            <view class="logo">🌱</view>
            <text>诗意学习</text>
          </view>

          <button class="next-btn" @tap="goChat">和诗人聊聊 →</button>
        </view>

        <view class="main-layout">
          <view class="left-panel">
            <view class="video-card">
              <view v-if="hasAiFrames" class="ai-stage">
                <image
                  class="ai-image"
                  :src="currentFrame.image_url"
                  mode="aspectFill"
                />

                <view class="frame-mask"></view>

                <view class="frame-caption">
                  <view class="frame-line">{{ currentFrame.line }}</view>
                </view>

                <view class="frame-index">
                  {{ currentFrameIndex + 1 }} / {{ frames.length }}
                </view>
              </view>

              <view v-else class="fallback-stage">
                <view class="sun"></view>
                <view class="cloud cloud-one">☁️</view>
                <view class="cloud cloud-two">☁️</view>
                <view class="mountain mountain-one"></view>
                <view class="mountain mountain-two"></view>
                <view class="scene-child">👧</view>
                <view class="fallback-text">
                  {{ imageLoading ? '正在为这首诗作画...' : '先看默认诗意画面' }}
                </view>
              </view>
            </view>

            <view class="control-row">
              <button class="control-btn primary" @tap="replayFrames">
                {{ hasAiFrames ? '再看一遍' : '播放画面' }}
              </button>

              <button class="control-btn secondary" :disabled="imageLoading" @tap="loadAiFrames">
                {{ imageLoading ? '生成中...' : '重新生成配图' }}
              </button>

              <button class="control-btn finish" @tap="finishStudy">学完了</button>
            </view>

            <view v-if="imageError" class="error-tip">
              {{ imageError }}
            </view>
          </view>

          <view class="right-panel">
            <view class="poem-card">
              <button
                class="voice-btn"
                :class="{ playing: audioPlaying, loading: audioLoading }"
                @tap.stop="togglePoemAudio"
              >
                <text v-if="audioLoading">…</text>
                <text v-else-if="audioPlaying">🔊</text>
                <text v-else>🔈</text>
              </button>

              <view class="poem-title">{{ poemData.title }}</view>
              <view class="poem-author">{{ poemData.dynasty }} · {{ poemData.author }}</view>

              <scroll-view class="poem-scroll" scroll-y>
                <view
                  v-for="(line, index) in poemLines"
                  :key="`${line}-${index}`"
                  class="poem-line"
                  :class="{ active: index === currentFrameIndex }"
                  @tap="selectFrame(index)"
                >
                  <text class="line-index">{{ index + 1 }}</text>
                  <text class="line-text">{{ line }}</text>
                </view>
              </scroll-view>
            </view>

            <view class="explain-card">
              <view class="explain-title">诗芽小讲解</view>
              <scroll-view class="explain-scroll" scroll-y>
                <view class="explain-text">
                  {{ poemData.translation || '这首诗描写了诗人看到的景色和心里的感受。你可以一边看画面，一边读诗句。' }}
                </view>
              </scroll-view>
            </view>

            <view class="tag-row">
              <view
                v-for="tag in poemTags"
                :key="tag"
                class="tag"
              >
                {{ tag }}
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { API, getLocalPoemById, normalizeAssetUrl } from '@/utils/api.js'

const poemId = ref('poem_001')
const poemData = ref(getLocalPoemById('poem_001'))

const frames = ref([])
const currentFrameIndex = ref(0)
const imageLoading = ref(false)
const imageError = ref('')

const audioLoading = ref(false)
const audioPlaying = ref(false)
const audioContext = ref(null)
const audioUrl = ref('')

const startTime = ref(Date.now())
let playTimer = null

const poemLines = computed(() => {
  if (Array.isArray(poemData.value.content)) {
    return poemData.value.content.filter(Boolean)
  }

  return String(poemData.value.content || '')
    .split(/[，,。\n]/)
    .map((line) => line.trim())
    .filter(Boolean)
})

const poemTags = computed(() => {
  if (Array.isArray(poemData.value.tags) && poemData.value.tags.length > 0) {
    return poemData.value.tags.slice(0, 4)
  }

  return ['古诗', '诗意', '学习']
})

const hasAiFrames = computed(() => frames.value.length > 0)

const currentFrame = computed(() => {
  return frames.value[currentFrameIndex.value] || {
    line: poemLines.value[currentFrameIndex.value] || poemLines.value[0] || '',
    image_url: ''
  }
})

onLoad(async (options) => {
  poemId.value = options.poem_id || options.id || 'poem_001'
  poemData.value = getLocalPoemById(poemId.value)
  startTime.value = Date.now()

  await loadPoemDetail()
  await loadAiFrames()
})

onUnmounted(() => {
  clearPlayTimer()
  stopPoemAudio()
})

const clearPlayTimer = () => {
  if (playTimer) {
    clearTimeout(playTimer)
    playTimer = null
  }
}

const getPoemReadText = () => {
  const poem = poemData.value || {}
  const title = poem.title || ''
  const dynasty = poem.dynasty || ''
  const author = poem.author || ''

  const content = Array.isArray(poem.content)
    ? poem.content.join('，')
    : String(poem.content || '')

  return `${title}，${dynasty}，${author}。${content}`
}

const stopPoemAudio = () => {
  if (audioContext.value) {
    try {
      audioContext.value.stop()
      audioContext.value.destroy()
    } catch (err) {
      console.log('停止朗读失败：', err)
    }
  }

  audioContext.value = null
  audioPlaying.value = false
}

const playPoemAudio = (url) => {
  stopPoemAudio()

  const finalUrl = normalizeAssetUrl(url)

  if (!finalUrl) {
    uni.showToast({
      title: '朗读地址为空',
      icon: 'none'
    })
    return
  }

  const ctx = uni.createInnerAudioContext()
  audioContext.value = ctx

  ctx.src = finalUrl
  ctx.autoplay = true

  ctx.onPlay(() => {
    audioPlaying.value = true
  })

  ctx.onEnded(() => {
    audioPlaying.value = false
    audioContext.value = null
  })

  ctx.onStop(() => {
    audioPlaying.value = false
  })

  ctx.onError((err) => {
    console.log('朗读播放失败：', err)
    audioPlaying.value = false
    audioContext.value = null

    uni.showToast({
      title: '朗读播放失败',
      icon: 'none'
    })
  })

  ctx.play()
}

const togglePoemAudio = async () => {
  if (audioLoading.value) return

  if (audioPlaying.value) {
    stopPoemAudio()
    return
  }

  if (audioUrl.value) {
    playPoemAudio(audioUrl.value)
    return
  }

  try {
    audioLoading.value = true

    const res = await API.textToSpeech(getPoemReadText())

    const url =
      res?.audio_url ||
      res?.url ||
      res?.data?.audio_url ||
      res?.data?.url ||
      ''

    if (res && res.success && url) {
      audioUrl.value = url
      playPoemAudio(url)
    } else {
      uni.showToast({
        title: res?.error || res?.message || '朗读生成失败',
        icon: 'none'
      })
    }
  } catch (err) {
    console.log('生成朗读失败：', err)

    uni.showToast({
      title: '朗读接口不可用',
      icon: 'none'
    })
  } finally {
    audioLoading.value = false
  }
}

const loadPoemDetail = async () => {
  try {
    const res = await API.getPoemDetail(poemId.value)

    if (res && res.success && res.data) {
      poemData.value = {
        ...res.data,
        content: Array.isArray(res.data.content)
          ? res.data.content
          : String(res.data.content || '').split(/[，,。\n]/).filter(Boolean)
      }
    }
  } catch (err) {
    console.log('古诗详情接口暂不可用，使用本地数据：', err)
  }
}

const normalizeFrames = (rawFrames) => {
  return (rawFrames || [])
    .filter((frame) => frame && frame.image_url)
    .map((frame, index) => ({
      index: Number(frame.index ?? index),
      line: frame.line || poemLines.value[index] || '',
      image_url: normalizeAssetUrl(frame.image_url),
      duration_ms: Number(frame.duration_ms || 3000)
    }))
    .sort((a, b) => a.index - b.index)
}

const loadAiFrames = async () => {
  if (imageLoading.value) return

  imageLoading.value = true
  imageError.value = ''

  try {
    uni.showLoading({
      title: '正在作画...'
    })

    const res = await API.generateImage(poemData.value)

    if (res && res.success && Array.isArray(res.frames) && res.frames.length > 0) {
      frames.value = normalizeFrames(res.frames)
      currentFrameIndex.value = 0
      replayFrames()
    } else {
      frames.value = []
      imageError.value = res?.error || 'AI 配图暂时不可用，已显示默认画面。'
    }
  } catch (err) {
    console.log('AI 配图接口失败：', err)
    frames.value = []
    imageError.value = 'AI 配图接口暂时没有连上，请检查后端 /generate/image 和大模型 Key。'
  } finally {
    uni.hideLoading()
    imageLoading.value = false
  }
}

const getSafeFrameIndex = (index) => {
  if (!hasAiFrames.value) {
    return Math.min(Math.max(index, 0), Math.max(poemLines.value.length - 1, 0))
  }

  return Math.min(Math.max(index, 0), frames.value.length - 1)
}

const selectFrame = (index) => {
  clearPlayTimer()
  currentFrameIndex.value = getSafeFrameIndex(index)
}

const replayFrames = () => {
  clearPlayTimer()
  currentFrameIndex.value = 0

  if (!hasAiFrames.value) {
    uni.showToast({
      title: '正在播放默认画面',
      icon: 'none'
    })
    return
  }

  playNextFrame()
}

const playNextFrame = () => {
  clearPlayTimer()

  if (!hasAiFrames.value) return

  const frame = currentFrame.value
  const duration = Math.max(1500, Number(frame.duration_ms || 3000))

  playTimer = setTimeout(() => {
    if (currentFrameIndex.value >= frames.value.length - 1) {
      clearPlayTimer()
      return
    }

    currentFrameIndex.value += 1
    playNextFrame()
  }, duration)
}

const finishStudy = async () => {
  const durationSeconds = Math.max(1, Math.round((Date.now() - startTime.value) / 1000))

  try {
    await API.addRecord(poemId.value, durationSeconds)

    uni.showToast({
      title: '已记录学习',
      icon: 'none'
    })
  } catch (err) {
    console.log('学习记录接口失败：', err)

    uni.showToast({
      title: '学习记录暂未保存',
      icon: 'none'
    })
  }

  goChat()
}

const goChat = () => {
  clearPlayTimer()
  stopPoemAudio()

  uni.navigateTo({
    url: `/pages/chat/chat?poem_id=${poemId.value}`,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = `#/pages/chat/chat?poem_id=${poemId.value}`
      }
    }
  })
}

const goBack = () => {
  clearPlayTimer()
  stopPoemAudio()

  uni.navigateBack({
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = '#/pages/index/index'
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

button[disabled] {
  opacity: 0.62;
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

.study-app {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: 100vw;
  max-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 8% 10%, rgba(255, 224, 96, 0.28), transparent 24%),
    radial-gradient(circle at 96% 16%, rgba(150, 212, 255, 0.25), transparent 22%),
    linear-gradient(180deg, #fffaf2 0%, #fff2e9 54%, #ffe9df 100%);
}

.page {
  width: 100%;
  height: 100%;
  padding: 8px 16px 14px;
  display: grid;
  grid-template-rows: 46px minmax(0, 1fr);
  gap: 9px;
}

.topbar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.back {
  position: absolute;
  left: 0;
  top: 5px;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.88);
  color: #5b508d;
  font-size: 26px;
  line-height: 1;
  box-shadow: 0 7px 16px rgba(112, 79, 54, 0.14);
}

.title-pill {
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
  font-weight: 950;
  font-size: 17px;
  letter-spacing: 1px;
  box-shadow: 0 7px 16px rgba(111, 84, 55, 0.09);
}

.logo {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #ff964b;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 18px;
}

.next-btn {
  position: absolute;
  right: 0;
  top: 5px;
  height: 36px;
  border: 0;
  border-radius: 999px;
  padding: 0 16px;
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: white;
  font-size: 14px;
  font-weight: 950;
  box-shadow: 0 5px 0 #f16012;
}

.main-layout {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 232px;
  gap: 12px;
}

.left-panel,
.right-panel {
  min-height: 0;
}

.left-panel {
  display: grid;
  grid-template-rows: minmax(0, 1fr) 50px 20px;
  gap: 10px;
  padding-bottom: 2px;
}

.video-card {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border-radius: 24px;
  border: 4px solid rgba(255, 255, 255, 0.78);
  background: linear-gradient(180deg, #cdefff, #fff4df);
  box-shadow: 0 14px 24px rgba(74, 55, 42, 0.16);
}

.ai-stage,
.fallback-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.ai-image {
  width: 100%;
  height: 100%;
}

.frame-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 58%, rgba(38, 34, 55, 0.62));
}

.frame-caption {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 16px;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
}

.frame-line {
  font-size: 25px;
  font-weight: 950;
  letter-spacing: 4px;
}

.frame-scene {
  margin-top: 5px;
  font-size: 12px;
  font-weight: 850;
  line-height: 1.45;
  opacity: 0.94;
}

.frame-index {
  position: absolute;
  right: 14px;
  top: 12px;
  border-radius: 999px;
  padding: 5px 10px;
  background: rgba(0, 0, 0, 0.38);
  color: white;
  font-size: 12px;
  font-weight: 900;
}

.fallback-stage {
  background:
    radial-gradient(circle at 78% 20%, rgba(255, 217, 99, 0.42), transparent 16%),
    linear-gradient(180deg, #bfeeff 0%, #ecfaff 52%, #fff1d2 100%);
}

.sun {
  position: absolute;
  right: 82px;
  top: 36px;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: #ffd35b;
  box-shadow: 0 0 28px rgba(255, 180, 58, 0.52);
}

.cloud {
  position: absolute;
  color: white;
  font-size: 42px;
  filter: drop-shadow(0 7px 10px rgba(93, 126, 166, 0.16));
}

.cloud-one {
  left: 70px;
  top: 36px;
}

.cloud-two {
  right: 158px;
  top: 78px;
  transform: scale(0.72);
}

.mountain {
  position: absolute;
  bottom: 0;
  width: 230px;
  height: 146px;
  background: #83c7a4;
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
}

.mountain-one {
  left: 60px;
}

.mountain-two {
  left: 220px;
  background: #6fb191;
  transform: scale(1.15);
}

.scene-child {
  position: absolute;
  left: 250px;
  bottom: 30px;
  font-size: 48px;
}

.fallback-text {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  padding: 8px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #5b508d;
  font-size: 14px;
  font-weight: 950;
}

.control-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  align-items: end;
  margin-top: 4px;
}

.control-btn {
  min-height: 42px;
  border: 0;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 950;
  line-height: 42px;
}

.primary {
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: white;
  box-shadow: 0 4px 0 #f16012;
}

.secondary {
  background: white;
  color: #6a5f97;
  box-shadow: 0 4px 0 rgba(220, 211, 236, 0.9);
}

.finish {
  background: linear-gradient(180deg, #8bdc9e, #43b86d);
  color: white;
  box-shadow: 0 4px 0 #319957;
}

.error-tip {
  color: #c46a3b;
  font-size: 12px;
  font-weight: 850;
  padding-left: 6px;
  line-height: 18px;
}

.right-panel {
  display: grid;
  grid-template-rows: minmax(0, 1fr) 82px 30px;
  gap: 8px;
}

.poem-card,
.explain-card {
  min-height: 0;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 20px rgba(112, 79, 54, 0.11);
}

.poem-card {
  position: relative;
  padding: 12px 12px 10px;
  display: grid;
  grid-template-rows: 30px 22px minmax(0, 1fr);
  text-align: center;
  overflow: hidden;
}

.voice-btn {
  position: absolute;
  top: 9px;
  right: 10px;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #fff2d9;
  color: #6a5b86;
  font-size: 16px;
  line-height: 30px;
  text-align: center;
  box-shadow: 0 5px 12px rgba(255, 139, 71, 0.18);
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-btn.playing {
  background: #ffe1b8;
  color: #f1783f;
}

.voice-btn.loading {
  opacity: 0.72;
}

.poem-title {
  color: #4e4775;
  font-size: 22px;
  font-weight: 950;
  letter-spacing: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.poem-author {
  color: #7a6ea1;
  font-size: 13px;
  font-weight: 850;
  letter-spacing: 2px;
}

.poem-scroll {
  min-height: 0;
  height: 100%;
  padding-right: 2px;
}

.poem-line {
  min-height: 34px;
  border-radius: 16px;
  padding: 7px 8px;
  margin-bottom: 7px;
  color: #5d5485;
  background: #fff8ee;
  font-size: 15px;
  font-weight: 900;
  line-height: 1.35;
  display: flex;
  align-items: flex-start;
  gap: 7px;
  text-align: left;
}

.poem-line.active {
  background: #fff0c7;
  color: #f17428;
  box-shadow: inset 0 0 0 2px rgba(255, 166, 82, 0.36);
}

.line-index {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(255, 151, 77, 0.14);
  font-size: 12px;
  line-height: 20px;
}

.line-text {
  min-width: 0;
  flex: 1;
  word-break: break-all;
}

.explain-card {
  padding: 10px 12px;
  display: grid;
  grid-template-rows: 20px minmax(0, 1fr);
}

.explain-title {
  color: #4e4775;
  font-size: 14px;
  font-weight: 950;
}

.explain-scroll {
  height: 100%;
  min-height: 0;
}

.explain-text {
  color: #6f6598;
  font-size: 12px;
  font-weight: 850;
  line-height: 1.45;
  text-align: left;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 7px;
  overflow: hidden;
}

.tag {
  flex-shrink: 0;
  padding: 7px 10px;
  border-radius: 999px;
  background: #ecfbff;
  color: #42a8c7;
  font-size: 12px;
  font-weight: 950;
}
</style>
