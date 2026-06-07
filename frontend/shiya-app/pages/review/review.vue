<template>
  <view class="page-root">
    <view class="review-app">
      <view class="page">
        <view class="topbar">
          <button class="back" @tap="backAction">‹</button>

          <view class="title-pill">
            <view class="logo">
              {{ reviewStep === 'main' ? '🌱' : reviewStep === 'read' ? '🎙️' : '🧩' }}
            </view>
            <text>{{ reviewTitle }}</text>
          </view>

          <view class="top-placeholder"></view>
        </view>

        <!-- 巩固主页 -->
        <view v-if="reviewStep === 'main'" class="review-body">
          <view class="left-panel">
            <view class="section-title">📚 选择要巩固的古诗</view>

            <view class="poem-list">
              <view
                v-for="poem in reviewPoems"
                :key="poem.key"
                class="review-poem-item"
                @tap="startReview(poem.key)"
              >
                <view
                  class="review-poem-icon"
                  :class="poem.status === '已掌握' ? 'mastered-bg' : 'learning-bg'"
                >
                  {{ poem.icon }}
                </view>

                <view class="review-poem-info">
                  <view class="review-poem-name">{{ poem.title }}</view>
                  <view class="review-poem-author">{{ poem.author }}</view>
                </view>

                <view
                  class="review-poem-badge"
                  :class="poem.status === '已掌握' ? 'badge-mastered' : 'badge-learning'"
                >
                  {{ poem.status }}
                </view>

                <view class="review-poem-arrow">›</view>
              </view>
            </view>
          </view>

          <view class="summary-panel">
            <view class="summary-card">
              <view class="summary-icon">🏆</view>

              <view>
                <view class="summary-title">温故而知新</view>
                <view class="summary-sub">每天巩固，记得更牢！</view>
              </view>
            </view>

            <view class="stats-row">
              <view class="stat-card">
                <view class="stat-value">3</view>
                <view class="stat-label">已学古诗</view>
              </view>

              <view class="stat-card">
                <view class="stat-value">1</view>
                <view class="stat-label">已掌握</view>
              </view>

              <view class="stat-card">
                <view class="stat-value">2</view>
                <view class="stat-label">待巩固</view>
              </view>
            </view>
          </view>
        </view>

        <!-- 跟读页面 -->
        <view v-if="reviewStep === 'read'" class="read-body">
          <view class="read-left">
            <view class="poem-info-card">
              <view class="poem-info-emoji">{{ currentReviewPoem.icon }}</view>

              <view>
                <view class="poem-info-title">{{ currentReviewPoem.title }}</view>
                <view class="poem-info-author">{{ currentReviewPoem.author }}</view>
              </view>
            </view>

            <view class="read-poem-display">
              <view
                v-for="(line, index) in currentReviewPoem.lines"
                :key="line"
                class="read-line"
                :class="{ active: activeReadLine === index }"
              >
                {{ line }}
              </view>
            </view>
          </view>

          <view class="read-right">
            <view class="score-card">
              <view v-if="earnedStars > 0" class="score-value">
                {{ earnedStars * 20 }} 分
              </view>

              <view v-else class="score-empty">
                点击跟读获得评分
              </view>

              <view class="stars">
                <text v-for="i in 5" :key="i" class="star">
                  {{ earnedStars > 0 && i <= earnedStars ? '🌟' : '⭐' }}
                </text>
              </view>
            </view>

            <view class="read-buttons">
              <button class="read-btn play-btn" @tap="playReading">
                {{ isReading ? '⏹ 停止范读' : '🔊 听范读' }}
              </button>

              <button
                class="read-btn record-btn"
                :class="{ recording: isRecording }"
                @tap="recordReading"
              >
                {{ isRecording ? '🔴 正在聆听' : '🎙️ 跟读录音' }}
              </button>
            </view>

            <view class="read-feedback" :class="{ success: earnedStars > 0 }">
              {{ readFeedback }}
            </view>

            <view class="complete-btn-row">
              <button
                class="complete-btn"
                :class="{ disabled: earnedStars === 0 }"
                @tap="earnedStars > 0 ? goMatch() : toastNeedRecord()"
              >
                下一步：连连看
              </button>
            </view>
          </view>
        </view>

        <!-- 连连看页面 -->
        <view v-if="reviewStep === 'match'" class="match-body">
          <view class="match-instruction">
            请按古诗第 1、2、3、4 句顺序完成配对。不能跳着选哦！
          </view>

          <view class="match-columns">
            <view class="match-col">
              <view class="match-col-label">📝 诗句开头</view>

              <view
                v-for="item in currentPairs"
                :key="'left-' + item.id"
                class="match-card left-card"
                :class="{
                  selected: selectedLeft === item.id,
                  matched: matchedIds.includes(item.id)
                }"
                @tap="selectLeft(item.id)"
              >
                <text class="line-index">{{ item.id }}</text>
                <text>{{ item.left }}</text>
              </view>
            </view>

            <view class="match-col">
              <view class="match-col-label">📝 诗句结尾</view>

              <view
                v-for="item in rightPairs"
                :key="'right-' + item.id"
                class="match-card right-card"
                :class="{ matched: matchedIds.includes(item.id) }"
                @tap="selectRight(item.id)"
              >
                {{ item.right }}
              </view>
            </view>
          </view>

          <view class="match-feedback" :class="{ success: matchSuccess }">
            {{ matchFeedback }}
          </view>

          <view v-if="matchedIds.length === currentPairs.length" class="complete-overlay">
            <view class="complete-emoji">🏆</view>
            <view class="complete-text">巩固完成！跟读和连连看都完成啦！</view>
            <button class="complete-btn" @tap="backToMain">返回巩固主页</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, onUnmounted } from 'vue'
import { API, normalizeAssetUrl } from '@/utils/api.js'

const reviewStep = ref('main')
const currentReviewKey = ref('chunxiao')

const selectedLeft = ref(null)
const matchedIds = ref([])
const matchFeedback = ref('💡 请按照古诗第 1、2、3、4 句的顺序完成配对')
const matchSuccess = ref(false)

const activeReadLine = ref(0)
const earnedStars = ref(0)
const isRecording = ref(false)
const isReading = ref(false)
const readFeedback = ref('💡 先听范读，然后点击录音按钮开始跟读吧！')

const audioContext = ref(null)
const readLineTimer = ref(null)
const lineAudioUrlCache = new Map()
let readingPlaybackToken = 0

const reviewPoems = [
  {
    key: 'yonge',
    title: '咏鹅',
    author: '唐 · 骆宾王',
    icon: '🦢',
    status: '已掌握',
    lines: ['鹅，鹅，鹅', '曲项向天歌', '白毛浮绿水', '红掌拨清波'],
    pairs: [
      { id: 1, left: '鹅，鹅', right: '鹅' },
      { id: 2, left: '曲项', right: '向天歌' },
      { id: 3, left: '白毛', right: '浮绿水' },
      { id: 4, left: '红掌', right: '拨清波' }
    ]
  },
  {
    key: 'chunxiao',
    title: '春晓',
    author: '唐 · 孟浩然',
    icon: '🌸',
    status: '待巩固',
    lines: ['春眠不觉晓', '处处闻啼鸟', '夜来风雨声', '花落知多少'],
    pairs: [
      { id: 1, left: '春眠', right: '不觉晓' },
      { id: 2, left: '处处', right: '闻啼鸟' },
      { id: 3, left: '夜来', right: '风雨声' },
      { id: 4, left: '花落', right: '知多少' }
    ]
  },
  {
    key: 'jingyesi',
    title: '静夜思',
    author: '唐 · 李白',
    icon: '🌙',
    status: '待巩固',
    lines: ['床前明月光', '疑是地上霜', '举头望明月', '低头思故乡'],
    pairs: [
      { id: 1, left: '床前', right: '明月光' },
      { id: 2, left: '疑是', right: '地上霜' },
      { id: 3, left: '举头', right: '望明月' },
      { id: 4, left: '低头', right: '思故乡' }
    ]
  }
]

const currentReviewPoem = computed(() => {
  return reviewPoems.find(item => item.key === currentReviewKey.value) || reviewPoems[1]
})

const currentPairs = computed(() => currentReviewPoem.value.pairs)

const rightPairs = computed(() => {
  return [...currentPairs.value].reverse()
})

const reviewTitle = computed(() => {
  if (reviewStep.value === 'main') return '巩固练习'
  if (reviewStep.value === 'read') return '古诗跟读'
  return '古诗连连看'
})

const clearReadLineTimer = () => {
  if (readLineTimer.value) {
    clearInterval(readLineTimer.value)
    readLineTimer.value = null
  }
}

const destroyCurrentAudio = () => {
  const currentAudio = audioContext.value
  audioContext.value = null

  if (!currentAudio) return

  try {
    currentAudio.stop()
  } catch (err) {
    console.log('停止范读音频失败：', err)
  }

  try {
    currentAudio.destroy()
  } catch (err) {
    console.log('销毁范读音频失败：', err)
  }
}

const stopReadingAudio = () => {
  readingPlaybackToken += 1
  clearReadLineTimer()
  destroyCurrentAudio()

  isReading.value = false
  activeReadLine.value = -1
}

const getReadingLines = () => {
  const poem = currentReviewPoem.value

  return Array.isArray(poem.lines)
    ? poem.lines.map(line => String(line || '').trim()).filter(Boolean)
    : []
}

const getLineAudioCacheKey = () => {
  const poem = currentReviewPoem.value
  const poemKey = poem.key || poem.title || 'review-poem'

  return `${poemKey}:${getReadingLines().join('|')}`
}

const loadLineAudioUrls = async () => {
  const lines = getReadingLines()
  const cacheKey = getLineAudioCacheKey()

  if (lineAudioUrlCache.has(cacheKey)) {
    return lineAudioUrlCache.get(cacheKey)
  }

  const audioUrls = await Promise.all(
    lines.map(async (line) => {
      const res = await API.textToSpeech(line, 'child')

      if (!res || !res.success || !res.audio_url) {
        throw new Error(`范读生成失败：${line}`)
      }

      return normalizeAssetUrl(res.audio_url)
    })
  )

  lineAudioUrlCache.set(cacheKey, audioUrls)

  return audioUrls
}

const playSingleLineAudio = (url, lineIndex, token) => {
  return new Promise((resolve, reject) => {
    if (!url || token !== readingPlaybackToken) {
      resolve('cancelled')
      return
    }

    destroyCurrentAudio()

    const innerAudio = uni.createInnerAudioContext()
    audioContext.value = innerAudio

    let hasPlayCalled = false
    let hasSettled = false

    const settle = (result) => {
      if (hasSettled) return

      hasSettled = true

      if (audioContext.value === innerAudio) {
        audioContext.value = null
      }

      try {
        innerAudio.destroy()
      } catch (err) {
        console.log('销毁单句范读音频失败：', err)
      }

      resolve(result)
    }

    innerAudio.autoplay = false
    innerAudio.src = normalizeAssetUrl(url)

    innerAudio.onCanplay(() => {
      if (hasPlayCalled) return

      hasPlayCalled = true

      setTimeout(() => {
        if (token !== readingPlaybackToken) {
          settle('cancelled')
          return
        }

        innerAudio.play()
      }, 120)
    })

    innerAudio.onPlay(() => {
      if (token !== readingPlaybackToken) return

      isReading.value = true
      activeReadLine.value = lineIndex
      readFeedback.value = `🔊 正在范读第 ${lineIndex + 1} 句：${getReadingLines()[lineIndex]}`
    })

    innerAudio.onEnded(() => {
      settle('ended')
    })

    innerAudio.onStop(() => {
      if (token !== readingPlaybackToken) return
      settle('stopped')
    })

    innerAudio.onError((err) => {
      if (token !== readingPlaybackToken) {
        settle('cancelled')
        return
      }

      reject(err)
    })
  })
}

const playLineAudioQueue = async (audioUrls, token) => {
  const lines = getReadingLines()

  for (let index = 0; index < audioUrls.length; index += 1) {
    if (token !== readingPlaybackToken) return

    const result = await playSingleLineAudio(audioUrls[index], index, token)

    if (result === 'cancelled' || result === 'stopped') return

    if (token === readingPlaybackToken && index < lines.length - 1) {
      activeReadLine.value = index + 1
    }
  }

  if (token !== readingPlaybackToken) return

  clearReadLineTimer()
  destroyCurrentAudio()
  isReading.value = false
  activeReadLine.value = -1
  readFeedback.value = '✅ 范读结束，现在可以开始跟读啦！'
}

const playReading = async () => {
  if (isReading.value) {
    stopReadingAudio()
    readFeedback.value = '已停止范读'
    return
  }

  const lines = getReadingLines()

  if (!lines.length) {
    uni.showToast({
      title: '暂无可朗读内容',
      icon: 'none'
    })
    return
  }

  readingPlaybackToken += 1
  const token = readingPlaybackToken

  clearReadLineTimer()
  destroyCurrentAudio()
  activeReadLine.value = -1

  try {
    readFeedback.value = '🔊 正在准备逐句范读，请稍等...'

    uni.showLoading({
      title: '准备范读...'
    })

    const audioUrls = await loadLineAudioUrls()

    uni.hideLoading()

    if (token !== readingPlaybackToken) return

    console.log('巩固页逐句范读 TTS 返回：', audioUrls)

    playLineAudioQueue(audioUrls, token)
  } catch (err) {
    uni.hideLoading()

    if (token !== readingPlaybackToken) return

    console.log('调用逐句范读 TTS 失败：', err)

    clearReadLineTimer()
    destroyCurrentAudio()
    isReading.value = false
    activeReadLine.value = -1
    readFeedback.value = '范读接口暂不可用，请稍后再试'

    uni.showToast({
      title: '范读接口不可用',
      icon: 'none'
    })
  }
}

const backAction = () => {
  stopReadingAudio()

  if (reviewStep.value === 'main') {
    uni.navigateBack({
      fail: () => {
        if (typeof window !== 'undefined') {
          window.location.href = '#/pages/index/index'
        }
      }
    })
  } else {
    backToMain()
  }
}

const startReview = (key) => {
  stopReadingAudio()

  currentReviewKey.value = key

  activeReadLine.value = 0
  earnedStars.value = 0
  isRecording.value = false
  readFeedback.value = '💡 先听范读，然后点击录音按钮开始跟读吧！'

  selectedLeft.value = null
  matchedIds.value = []
  matchFeedback.value = '💡 请按照古诗第 1、2、3、4 句的顺序完成配对'
  matchSuccess.value = false

  reviewStep.value = 'read'
}

const recordReading = () => {
  if (isRecording.value) return

  stopReadingAudio()

  isRecording.value = true
  readFeedback.value = '🎙️ 正在聆听，请大声读出诗句！'
  activeReadLine.value = 0

  setTimeout(() => {
    isRecording.value = false
    activeReadLine.value = -1
    earnedStars.value = 4
    readFeedback.value = '🌟 跟读完成！你获得了 80 分，可以进入连连看啦！'
  }, 1800)
}

const toastNeedRecord = () => {
  uni.showToast({
    title: '请先完成跟读录音',
    icon: 'none'
  })
}

const goMatch = () => {
  stopReadingAudio()

  selectedLeft.value = null
  matchedIds.value = []
  matchFeedback.value = '💡 请先完成第 1 句，再完成第 2、3、4 句'
  matchSuccess.value = false

  reviewStep.value = 'match'
}

const selectLeft = (id) => {
  if (matchedIds.value.includes(id)) return

  const expectedId = matchedIds.value.length + 1

  if (id !== expectedId) {
    selectedLeft.value = null
    matchSuccess.value = false
    matchFeedback.value = `请先完成第 ${expectedId} 句，再选择第 ${id} 句`
    return
  }

  selectedLeft.value = id
  matchSuccess.value = false

  const pair = currentPairs.value.find(item => item.id === id)
  matchFeedback.value = `✅ 已选择第 ${id} 句「${pair.left}」，请点击右边正确结尾`
}

const selectRight = (id) => {
  const expectedId = matchedIds.value.length + 1

  if (!selectedLeft.value) {
    matchFeedback.value = `👆 请先在左边选择第 ${expectedId} 句`
    matchSuccess.value = false
    return
  }

  if (selectedLeft.value !== expectedId) {
    selectedLeft.value = null
    matchSuccess.value = false
    matchFeedback.value = `请按照顺序完成，当前应该完成第 ${expectedId} 句`
    return
  }

  if (selectedLeft.value === id) {
    matchedIds.value.push(id)
    selectedLeft.value = null
    matchSuccess.value = true

    if (matchedIds.value.length === currentPairs.value.length) {
      matchFeedback.value = '🎉 太棒了！四句古诗都按顺序完成了！'
    } else {
      matchFeedback.value = `🎉 第 ${id} 句正确！接下来完成第 ${matchedIds.value.length + 1} 句`
    }
  } else {
    selectedLeft.value = null
    matchSuccess.value = false
    matchFeedback.value = `😅 这一句结尾不对哦，请重新完成第 ${expectedId} 句`
  }
}

const backToMain = () => {
  stopReadingAudio()

  reviewStep.value = 'main'

  selectedLeft.value = null
  matchedIds.value = []
  matchFeedback.value = '💡 请按照古诗第 1、2、3、4 句的顺序完成配对'
  matchSuccess.value = false

  activeReadLine.value = 0
  earnedStars.value = 0
  isRecording.value = false
  readFeedback.value = '💡 先听范读，然后点击录音按钮开始跟读吧！'
}

onUnmounted(() => {
  stopReadingAudio()
})
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

.review-app {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: 100vw;
  max-height: 100vh;
  overflow: hidden;
  border-radius: 0;
  background:
    radial-gradient(circle at 8% 12%, rgba(255, 225, 105, 0.22), transparent 22%),
    radial-gradient(circle at 92% 25%, rgba(255, 221, 150, 0.16), transparent 22%),
    linear-gradient(180deg, #fffaf2 0%, #fff1e8 45%, #ffe9df 78%, #fff6ee 100%);
}

.page {
  position: absolute;
  inset: 0;
  padding: 7px 16px 14px;
  display: grid;
  grid-template-rows: 58px minmax(0, 1fr);
  gap: 8px;
  overflow: hidden;
}

.topbar {
  position: relative;
  height: 44px;
  z-index: 20;
}

.back {
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
  min-width: 160px;
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

.logo {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #ff964b;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-size: 16px;
}

.top-placeholder {
  width: 36px;
}

/* 巩固主页 */
.review-body {
  height: 100%;
  display: flex;
  gap: 16px;
  min-height: 0;
}

.left-panel {
  flex: 1.72;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.section-title {
  font-size: 18px;
  font-weight: 900;
  color: #5b508d;
}

.poem-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-poem-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 6px 14px rgba(74, 55, 42, 0.08);
}

.review-poem-item:active,
.match-card:active {
  transform: scale(0.98);
}

.review-poem-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 24px;
  flex-shrink: 0;
}

.mastered-bg {
  background: #e6fff7;
}

.learning-bg {
  background: #fff4e6;
}

.review-poem-info {
  flex: 1;
}

.review-poem-name {
  font-size: 16px;
  font-weight: 900;
  color: #5b508d;
}

.review-poem-author {
  font-size: 11px;
  font-weight: 800;
  color: #9a90c0;
  margin-top: 2px;
}

.review-poem-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
}

.badge-mastered {
  background: #e6fff7;
  color: #2cbf9d;
}

.badge-learning {
  background: #fff4e6;
  color: #ff914d;
}

.review-poem-arrow {
  color: #cbc3e8;
  font-size: 18px;
}

.summary-panel {
  flex: 0.82;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  justify-content: flex-start;
  margin-top: 34px;
}

.summary-card {
  width: 92%;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  border-radius: 24px;
  background: linear-gradient(135deg, #b9f1e6 0%, #fff8dc 100%);
  box-shadow: 0 8px 16px rgba(104, 80, 52, 0.1);
}

.summary-icon {
  width: 52px;
  height: 52px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  display: grid;
  place-items: center;
  font-size: 28px;
  flex-shrink: 0;
}

.summary-title {
  font-size: 18px;
  font-weight: 900;
  color: #5b508d;
}

.summary-sub {
  font-size: 12px;
  font-weight: 800;
  color: #ff914d;
  margin-top: 2px;
}

.stats-row {
  width: 92%;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  gap: 8px;
}

.stat-card {
  flex: 1;
  padding: 10px 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 5px 12px rgba(74, 55, 42, 0.08);
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 900;
  color: #5b508d;
  line-height: 1;
}

.stat-label {
  font-size: 10px;
  font-weight: 800;
  color: #9a90c0;
  margin-top: 2px;
}

/* 跟读页面 */
.read-body {
  height: 100%;
  position: relative;
  display: flex;
  gap: 16px;
  min-height: 0;
}

.read-left {
  flex: 1.05;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.read-right {
  flex: 0.92;
  min-width: 0;
  height: 100%;
  display: grid;
  grid-template-rows: 92px 48px 74px 44px;
  gap: 8px;
  align-content: center;
}

.poem-info-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 8px 16px rgba(74, 55, 42, 0.1);
}

.poem-info-emoji {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: #fff8ee;
  display: grid;
  place-items: center;
  font-size: 28px;
}

.poem-info-title {
  font-size: 20px;
  font-weight: 900;
  color: #5b508d;
}

.poem-info-author {
  font-size: 13px;
  font-weight: 800;
  color: #ff914d;
  margin-top: 2px;
}

.read-poem-display {
  flex: 1;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 8px 18px rgba(74, 55, 42, 0.1);
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.read-line {
  font-size: 18px;
  font-weight: 900;
  color: #5b508d;
  line-height: 1.6;
  letter-spacing: 2px;
  padding: 6px 10px;
  border-radius: 12px;
}

.read-line.active {
  background: #fff8ee;
  color: #ff914d;
  transform: scale(1.02);
  box-shadow: 0 4px 10px rgba(255, 145, 77, 0.15);
}

.score-card {
  width: 82%;
  margin-left: auto;
  margin-right: auto;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 7px 15px rgba(74, 55, 42, 0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-value {
  font-size: 27px;
  font-weight: 950;
  color: #ff914d;
  line-height: 1;
  margin-bottom: 6px;
}

.score-empty {
  font-size: 15px;
  font-weight: 900;
  color: #9a90c0;
  margin-bottom: 8px;
}

.stars {
  display: flex;
  gap: 3px;
  justify-content: center;
  font-size: 21px;
}

.read-buttons {
  width: 82%;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.read-btn {
  height: 44px;
  padding: 0 17px;
  border-radius: 24px;
  border: 0;
  font-size: 14px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 4px 0 rgba(0, 0, 0, 0.08), 0 6px 14px rgba(74, 55, 42, 0.1);
}

.play-btn {
  background: #e6fff7;
  color: #2cbf9d;
}

.record-btn {
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: #fff;
}

.record-btn.recording {
  background: #ff5252;
  animation: pulseRec 1s ease infinite;
}

@keyframes pulseRec {
  50% {
    box-shadow: 0 0 0 14px rgba(255, 82, 82, 0);
  }
}

.read-feedback {
  width: 82%;
  margin-left: auto;
  margin-right: auto;
  text-align: center;
  padding: 10px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.76);
  font-size: 13px;
  font-weight: 800;
  color: #786ca4;
  min-height: 68px;
  max-height: 74px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.45;
}

.read-feedback.success {
  color: #2cbf9d;
  background: #e6fff7;
}

.complete-btn-row {
  width: 82%;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  justify-content: center;
  align-items: center;
}

.complete-btn {
  width: 178px;
  height: 44px;
  padding: 0;
  border-radius: 999px;
  border: 0;
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: #ffffff;
  font-size: 14px;
  font-weight: 900;
  box-shadow: 0 4px 0 #f16012, 0 8px 14px rgba(236, 98, 34, 0.18);
}

.complete-btn.disabled {
  opacity: 0.55;
}

/* 连连看 */
.match-body {
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.match-instruction {
  text-align: center;
  font-size: 14px;
  font-weight: 800;
  color: #786ca4;
  padding: 8px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
}

.match-columns {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}

.match-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.match-col-label {
  text-align: center;
  font-size: 11px;
  font-weight: 900;
  color: #9a90c0;
  letter-spacing: 1px;
}

.match-card {
  flex: 1;
  min-height: 42px;
  max-height: 64px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 900;
  text-align: center;
  padding: 6px 10px;
  border: 3px solid transparent;
  box-shadow: 0 4px 0 rgba(0, 0, 0, 0.08), 0 6px 12px rgba(74, 55, 42, 0.1);
}

.line-index {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(255, 145, 77, 0.16);
  color: #ff914d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.left-card {
  background: #fff8ee;
  color: #5b508d;
  border-color: #ffe8c4;
}

.right-card {
  background: #f4f1ff;
  color: #5b508d;
  border-color: #e0d8f7;
}

.match-card.selected {
  border-color: #ff914d;
  box-shadow: 0 0 0 5px rgba(255, 145, 77, 0.2), 0 6px 12px rgba(74, 55, 42, 0.15);
  transform: scale(1.03);
  background: #ffffff;
}

.match-card.matched {
  border-color: #2cbf9d;
  background: #e6fff7;
  color: #2cbf9d;
  opacity: 0.75;
  transform: scale(0.95);
}

.match-feedback {
  text-align: center;
  padding: 8px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  font-size: 13px;
  font-weight: 800;
  color: #786ca4;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.match-feedback.success {
  color: #2cbf9d;
  background: #e6fff7;
}

.complete-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.92);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 0;
  z-index: 10;
}

.complete-emoji {
  font-size: 56px;
}

.complete-text {
  font-size: 20px;
  font-weight: 900;
  color: #5b508d;
  text-align: center;
}
</style>