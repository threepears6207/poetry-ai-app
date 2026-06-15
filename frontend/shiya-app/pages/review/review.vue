<template>
  <view class="page-root">
    <view class="review-app" :style="appScaleStyle">
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

            <scroll-view class="poem-list" scroll-y>
              <view v-if="isLoadingList" class="list-message">
                正在加载巩固任务...
              </view>

              <view v-else-if="!reviewPoems.length" class="list-message">
                暂无需要巩固的古诗
              </view>

              <block v-else>
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
              </block>
            </scroll-view>

            <view v-if="listError" class="list-warning">
              {{ listError }}
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
                <view class="stat-value">{{ currentStats.total }}</view>
                <view class="stat-label">已学古诗</view>
              </view>

              <view class="stat-card">
                <view class="stat-value">{{ currentStats.mastered }}</view>
                <view class="stat-label">已掌握</view>
              </view>

              <view class="stat-card">
                <view class="stat-value">{{ currentStats.learning }}</view>
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
                :class="{ active: activeReadLine === index, completed: completedReadLines.includes(index) }"
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
                完成当前句跟读获得评分
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
                {{ isScoring ? '⏳ 正在评分' : isRecording ? '🔴 正在聆听' : '🎙️ 跟读录音' }}
              </button>
            </view>

            <view class="read-feedback" :class="{ success: earnedStars > 0 }">
              {{ readFeedback }}
            </view>

            <view class="complete-btn-row">
              <button
                class="complete-btn"
                :class="{ disabled: !allReadLinesPassed }"
                @tap="allReadLinesPassed ? goMatch() : toastNeedRecord()"
              >
                {{ allReadLinesPassed ? '下一步：连连看' : '请先逐句完成跟读' }}
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
            <view class="complete-text">{{ resultSubmitText }}</view>
            <button class="complete-btn" :disabled="isSubmittingResult" @tap="backToMain">
              {{ isSubmittingResult ? '正在保存...' : '返回巩固主页' }}
            </button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { API, LOCAL_POEMS, normalizeAssetUrl } from '@/utils/api.js'

const DESIGN_WIDTH = 844
const DESIGN_HEIGHT = 390
const appScale = ref(1)

const appScaleStyle = computed(() => `transform: scale(${appScale.value});`)

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

  if (typeof uni.onWindowResize === 'function') {
    uni.onWindowResize(handleAppResize)
  }
})

onUnmounted(() => {
  if (typeof uni.offWindowResize === 'function') {
    uni.offWindowResize(handleAppResize)
  }
})

const reviewStep = ref('main')
const currentReviewKey = ref('poem_001')

const selectedLeft = ref(null)
const matchedIds = ref([])
const matchFeedback = ref('💡 请按照古诗第 1、2、3、4 句的顺序完成配对')
const matchSuccess = ref(false)

const activeReadLine = ref(0)
const earnedStars = ref(0)
const isRecording = ref(false)
const isReading = ref(false)
const isScoring = ref(false)
const readFeedback = ref('💡 小朋友要一句一句听范读，再一句一句录音跟读哦！')
const completedReadLines = ref([])

const isLoadingList = ref(false)
const listError = ref('')
const isSubmittingResult = ref(false)
const resultSubmitted = ref(false)

const audioContext = ref(null)
const readLineTimer = ref(null)
const recorderManager = ref(null)
const recordStopTimer = ref(null)
const browserMediaRecorder = ref(null)
const browserAudioChunks = ref([])
const browserAudioStream = ref(null)
const lineAudioUrlCache = new Map()
let readingPlaybackToken = 0

const MAX_RECORD_DURATION_MS = 30000

const POEM_ICONS = ['🌸', '🌙', '🦢', '🌾', '🏯', '🌿', '🍃', '⭐']

const extractArrayPayload = (payload) => {
  const candidates = [
    payload,
    payload?.data,
    payload?.items,
    payload?.poems,
    payload?.list,
    payload?.results,
    payload?.records,
    payload?.data?.items,
    payload?.data?.poems,
    payload?.data?.list,
    payload?.data?.results,
    payload?.data?.records
  ]

  return candidates.find(item => Array.isArray(item)) || []
}

const extractObjectPayload = (payload) => {
  return payload?.data?.poem ||
    payload?.data?.item ||
    payload?.poem ||
    payload?.item ||
    payload?.data ||
    payload ||
    {}
}

const splitPoemText = (text = '') => {
  return String(text || '')
    .split(/[，,。；;！!？?\n]/)
    .map(line => line.trim())
    .filter(Boolean)
}

const extractPoemLines = (poem = {}) => {
  const source = poem.lines || poem.content || poem.poem_content || poem.poemContent

  if (Array.isArray(source)) {
    return source
      .map(line => String(line || '').trim())
      .filter(Boolean)
  }

  return splitPoemText(source)
}

const splitLineToPair = (line = '', index = 0) => {
  const cleanLine = String(line || '')
    .replace(/[，,。；;！!？?\s]/g, '')
    .trim()

  if (!cleanLine) {
    return {
      id: index + 1,
      left: `第 ${index + 1} 句`,
      right: ''
    }
  }

  const splitIndex = cleanLine.length <= 3
    ? Math.max(1, cleanLine.length - 1)
    : Math.min(2, cleanLine.length - 1)

  return {
    id: index + 1,
    left: cleanLine.slice(0, splitIndex),
    right: cleanLine.slice(splitIndex)
  }
}

const buildPairsFromLines = (lines = []) => {
  return lines.map((line, index) => splitLineToPair(line, index))
}

const normalizePairs = (pairs = [], lines = []) => {
  if (Array.isArray(pairs) && pairs.length) {
    return pairs
      .map((item, index) => ({
        id: Number(item.id || index + 1),
        left: String(item.left || item.start || item.front || '').trim(),
        right: String(item.right || item.end || item.back || '').trim()
      }))
      .filter(item => item.left || item.right)
  }

  return buildPairsFromLines(lines)
}

const getLocalPoemByAnyId = (poemId = '') => {
  return LOCAL_POEMS.find(item => item.id === poemId || item.poem_id === poemId) || null
}

const getAuthorText = (poem = {}) => {
  const author = poem.author || poem.poet_name || poem.poetName || ''
  const dynasty = poem.dynasty || ''

  if (!author && !dynasty) return '未知作者'

  if (String(author).includes('·')) return String(author)

  return dynasty ? `${dynasty} · ${author || '未知作者'}` : String(author)
}

const normalizePassed = (payload, defaultValue = false) => {
  const value = payload?.data?.status ?? payload?.data?.passed ?? payload?.status ?? payload?.passed ?? payload?.mastered ?? payload?.completed ?? payload?.is_passed ?? payload

  if (typeof value === 'boolean') return value

  if (typeof value === 'number') return value > 0

  if (typeof value === 'string') {
    const lowerValue = value.toLowerCase()

    if (
      value.includes('已掌握') ||
      value.includes('已通过') ||
      value.includes('完成') ||
      lowerValue.includes('passed') ||
      lowerValue.includes('mastered') ||
      lowerValue.includes('completed') ||
      lowerValue.includes('done')
    ) {
      return true
    }

    if (
      value.includes('待') ||
      value.includes('未') ||
      lowerValue.includes('learning') ||
      lowerValue.includes('pending') ||
      lowerValue.includes('todo')
    ) {
      return false
    }
  }

  return defaultValue
}

const normalizeReviewPoem = (rawItem = {}, index = 0) => {
  const item = typeof rawItem === 'string'
    ? { poem_id: rawItem }
    : rawItem?.poem || rawItem?.poem_info || rawItem?.data || rawItem || {}

  const poemId = String(
    item.poem_id ||
    item.poemId ||
    item.id ||
    item.key ||
    `poem_${String(index + 1).padStart(3, '0')}`
  )

  const localPoem = getLocalPoemByAnyId(poemId) || {}
  const poem = {
    ...localPoem,
    ...item
  }

  const lines = extractPoemLines(poem)
  const pairs = normalizePairs(poem.pairs, lines)
  const passed = normalizePassed(poem, false)

  return {
    key: poemId,
    poem_id: poemId,
    title: poem.title || poem.poem_title || poem.poemTitle || `古诗 ${index + 1}`,
    author: getAuthorText(poem),
    dynasty: poem.dynasty || localPoem.dynasty || '',
    icon: poem.icon || POEM_ICONS[index % POEM_ICONS.length],
    status: passed ? '已掌握' : '待巩固',
    passed,
    lines,
    pairs
  }
}

const buildFallbackReviewPoems = () => {
  return LOCAL_POEMS.slice(0, 3).map((poem, index) => normalizeReviewPoem(poem, index))
}

const mergePoemStatus = (poem = {}, statusPayload = {}) => {
  const passed = normalizePassed(statusPayload, poem.passed)

  return {
    ...poem,
    passed,
    status: passed ? '已掌握' : '待巩固'
  }
}

const reviewPoems = ref(buildFallbackReviewPoems())

const currentReviewPoem = computed(() => {
  return reviewPoems.value.find(item => item.key === currentReviewKey.value) ||
    reviewPoems.value[0] ||
    buildFallbackReviewPoems()[0]
})

const currentPairs = computed(() => currentReviewPoem.value.pairs || [])

const allReadLinesPassed = computed(() => {
  const lines = getReadingLines()

  return lines.length > 0 && completedReadLines.value.length >= lines.length
})

const rightPairs = computed(() => {
  return [...currentPairs.value].reverse()
})

const currentStats = computed(() => {
  const total = reviewPoems.value.length
  const mastered = reviewPoems.value.filter(item => item.passed || item.status === '已掌握').length

  return {
    total,
    mastered,
    learning: Math.max(total - mastered, 0)
  }
})

const reviewTitle = computed(() => {
  if (reviewStep.value === 'main') return '巩固练习'
  if (reviewStep.value === 'read') return '古诗跟读'
  return '古诗连连看'
})

const resultSubmitText = computed(() => {
  if (isSubmittingResult.value) return '正在保存巩固结果...'
  if (resultSubmitted.value) return '巩固完成！结果已保存啦！'
  return '巩固完成！跟读和连连看都完成啦！'
})

const updateReviewPoem = (key, updater) => {
  reviewPoems.value = reviewPoems.value.map(item => {
    if (item.key !== key) return item

    return typeof updater === 'function'
      ? updater(item)
      : {
          ...item,
          ...updater
        }
  })
}

const refreshPoemStatus = async (poemKey) => {
  const poem = reviewPoems.value.find(item => item.key === poemKey)

  if (!poem || !poem.poem_id) return

  try {
    const res = await API.getConsolidationStatus(poem.poem_id)
    updateReviewPoem(poem.key, item => mergePoemStatus(item, res))
  } catch (err) {
    console.log('查询巩固状态失败：', err)
  }
}

const hydratePoemDetailsForList = async () => {
  if (!reviewPoems.value.length) return

  const hydratedPoems = await Promise.all(
    reviewPoems.value.map(async (poem, index) => {
      if ((poem.lines || []).length && (poem.pairs || []).length) {
        return poem
      }

      if (!poem.poem_id) return poem

      try {
        const detailRes = await API.getPoemDetail(poem.poem_id)
        const detail = extractObjectPayload(detailRes)
        const hydrated = normalizeReviewPoem(
          {
            ...poem,
            ...detail,
            poem_id: poem.poem_id
          },
          index
        )

        return {
          ...hydrated,
          passed: poem.passed,
          status: poem.status
        }
      } catch (err) {
        console.log(`获取 ${poem.poem_id} 详情失败：`, err)
        return poem
      }
    })
  )

  reviewPoems.value = hydratedPoems
}

const refreshStatusesForList = async () => {
  if (!reviewPoems.value.length) return

  const poemsWithStatus = await Promise.all(
    reviewPoems.value.map(async (poem) => {
      if (!poem.poem_id) return poem

      try {
        const res = await API.getConsolidationStatus(poem.poem_id)
        return mergePoemStatus(poem, res)
      } catch (err) {
        console.log(`查询 ${poem.poem_id} 巩固状态失败：`, err)
        return poem
      }
    })
  )

  reviewPoems.value = poemsWithStatus
}

const loadConsolidationList = async () => {
  isLoadingList.value = true
  listError.value = ''

  try {
    const res = await API.getConsolidationList()
    const list = extractArrayPayload(res)

    reviewPoems.value = list.map((item, index) => normalizeReviewPoem(item, index))

    if (reviewPoems.value.length) {
      currentReviewKey.value = reviewPoems.value[0].key
    }

    await hydratePoemDetailsForList()
    await refreshStatusesForList()
  } catch (err) {
    console.log('加载巩固列表失败：', err)

    const fallbackPoems = buildFallbackReviewPoems()
    reviewPoems.value = fallbackPoems
    currentReviewKey.value = fallbackPoems[0]?.key || 'poem_001'
    listError.value = '巩固接口暂不可用，当前显示本地演示数据'
  } finally {
    isLoadingList.value = false
  }
}

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

const stopReadingAudio = (keepCurrentLine = true) => {
  const currentLineIndex = getCurrentLineIndex()

  readingPlaybackToken += 1
  clearReadLineTimer()
  destroyCurrentAudio()

  isReading.value = false

  if (keepCurrentLine) {
    activeReadLine.value = currentLineIndex
  }
}

const getReadingLines = () => {
  const poem = currentReviewPoem.value

  return Array.isArray(poem.lines)
    ? poem.lines.map(line => String(line || '').trim()).filter(Boolean)
    : []
}

const getLineAudioCacheKey = (lineIndex = activeReadLine.value) => {
  const poem = currentReviewPoem.value
  const poemKey = poem.key || poem.title || 'review-poem'

  return `${poemKey}:${lineIndex}:${getReadingLines()[lineIndex] || ''}`
}

const getCurrentLineIndex = () => {
  const lines = getReadingLines()
  const index = Number(activeReadLine.value)

  if (!lines.length) return 0
  if (index < 0) return 0

  return Math.min(index, lines.length - 1)
}

const getCurrentReadingLine = () => {
  const lines = getReadingLines()

  return lines[getCurrentLineIndex()] || ''
}

const loadCurrentLineAudioUrl = async () => {
  const lineIndex = getCurrentLineIndex()
  const line = getCurrentReadingLine()
  const cacheKey = getLineAudioCacheKey(lineIndex)

  if (lineAudioUrlCache.has(cacheKey)) {
    return lineAudioUrlCache.get(cacheKey)
  }

  const res = await API.textToSpeech(line, 'child')

  if (!res || !res.success || !res.audio_url) {
    throw new Error(`范读生成失败：${line}`)
  }

  const audioUrl = normalizeAssetUrl(res.audio_url)
  lineAudioUrlCache.set(cacheKey, audioUrl)

  return audioUrl
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
      settle(token !== readingPlaybackToken ? 'cancelled' : 'stopped')
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
  activeReadLine.value = getCurrentLineIndex()
  readFeedback.value = '✅ 范读结束，现在可以开始跟读啦！'
}

const playReading = async () => {
  if (isReading.value) {
    const lineIndex = getCurrentLineIndex()
    stopReadingAudio()
    activeReadLine.value = lineIndex
    readFeedback.value = '已停止范读'
    return
  }

  const line = getCurrentReadingLine()

  if (!line) {
    uni.showToast({
      title: '暂无可朗读内容',
      icon: 'none'
    })
    return
  }

  const lineIndex = getCurrentLineIndex()
  readingPlaybackToken += 1
  const token = readingPlaybackToken

  clearReadLineTimer()
  destroyCurrentAudio()
  activeReadLine.value = lineIndex

  try {
    readFeedback.value = `🔊 正在准备第 ${lineIndex + 1} 句范读，请稍等...`

    uni.showLoading({
      title: '准备范读...'
    })

    const audioUrl = await loadCurrentLineAudioUrl()

    uni.hideLoading()

    if (token !== readingPlaybackToken) return

    console.log('巩固页当前句范读 TTS 返回：', audioUrl)

    const result = await playSingleLineAudio(audioUrl, lineIndex, token)

    if (token !== readingPlaybackToken || result === 'cancelled') return

    isReading.value = false
    activeReadLine.value = lineIndex
    readFeedback.value = `✅ 第 ${lineIndex + 1} 句范读结束，请录音跟读这一句：${line}`
  } catch (err) {
    uni.hideLoading()

    if (token !== readingPlaybackToken) return

    console.log('调用当前句范读 TTS 失败：', err)

    clearReadLineTimer()
    destroyCurrentAudio()
    isReading.value = false
    activeReadLine.value = lineIndex
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

const resetReviewState = () => {
  activeReadLine.value = 0
  earnedStars.value = 0
  completedReadLines.value = []
  isRecording.value = false
  isScoring.value = false
  readFeedback.value = '💡 小朋友要一句一句听范读，再一句一句录音跟读哦！'

  selectedLeft.value = null
  matchedIds.value = []
  matchFeedback.value = '💡 请按照古诗第 1、2、3、4 句的顺序完成配对'
  matchSuccess.value = false
  isSubmittingResult.value = false
  resultSubmitted.value = false
}

const startReview = (key) => {
  stopReadingAudio()

  currentReviewKey.value = key
  resetReviewState()

  reviewStep.value = 'read'
  refreshPoemStatus(key)
}

const clearRecordStopTimer = () => {
  if (recordStopTimer.value) {
    clearTimeout(recordStopTimer.value)
    recordStopTimer.value = null
  }
}

const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onloadend = () => {
      const result = String(reader.result || '')
      resolve(result.includes(',') ? result.split(',').pop() : result)
    }

    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

const stripAudioBase64Prefix = (value = '') => {
  return String(value || '').replace(/^data:audio\/\w+;base64,/, '').replace(/^data:.*?;base64,/, '')
}

const readAudioByFetch = (filePath) => {
  if (typeof fetch !== 'function') {
    return Promise.reject(new Error('当前环境不支持 fetch 读取录音文件'))
  }

  return fetch(filePath)
    .then((res) => {
      if (!res.ok) {
        throw new Error(`fetch 读取录音失败：${res.status}`)
      }

      return res.blob()
    })
    .then(blobToBase64)
}

const readAudioByPlusIo = (filePath) => {
  return new Promise((resolve, reject) => {
    if (typeof plus === 'undefined' || !plus.io) {
      reject(new Error('plus.io 不可用'))
      return
    }

    const tryPaths = [
      filePath,
      String(filePath || '').replace(/^file:\/\//, ''),
      typeof plus.io.convertLocalFileSystemURL === 'function'
        ? plus.io.convertLocalFileSystemURL(filePath)
        : ''
    ].filter(Boolean)

    const tryRead = (index = 0) => {
      const currentPath = tryPaths[index]

      if (!currentPath) {
        reject(new Error('plus.io 读取录音文件失败'))
        return
      }

      plus.io.resolveLocalFileSystemURL(
        currentPath,
        (entry) => {
          entry.file(
            (file) => {
              const reader = new plus.io.FileReader()

              reader.onloadend = (event) => {
                const result = event?.target?.result || reader.result || ''
                const base64 = stripAudioBase64Prefix(result)

                if (!base64) {
                  reject(new Error('plus.io 录音 base64 转换失败'))
                  return
                }

                resolve(base64)
              }

              reader.onerror = () => tryRead(index + 1)
              reader.readAsDataURL(file)
            },
            () => tryRead(index + 1)
          )
        },
        () => tryRead(index + 1)
      )
    }

    tryRead()
  })
}

const fileToBase64 = async (filePath) => {
  if (!filePath) {
    throw new Error('录音文件为空')
  }

  if (typeof uni.getFileSystemManager === 'function') {
    try {
      const res = await new Promise((resolve, reject) => {
        uni.getFileSystemManager().readFile({
          filePath,
          encoding: 'base64',
          success: resolve,
          fail: reject
        })
      })

      if (res?.data) return res.data
    } catch (err) {
      console.log('uni 文件系统读取录音失败，尝试 plus.io / fetch：', err)
    }
  }

  try {
    return await readAudioByPlusIo(filePath)
  } catch (err) {
    console.log('plus.io 读取录音失败，尝试 fetch：', err)
  }

  return readAudioByFetch(filePath)
}

const moveToNextReadLine = () => {
  const lines = getReadingLines()
  const nextIndex = getCurrentLineIndex() + 1

  if (nextIndex < lines.length) {
    activeReadLine.value = nextIndex
    earnedStars.value = 0
    readFeedback.value = `✅ 第 ${nextIndex} 句通过啦！请先听第 ${nextIndex + 1} 句范读，再录音跟读。`
    return
  }

  readFeedback.value = '🎉 全部诗句都跟读通过啦！可以进入连连看啦！'
}

const submitCurrentLineScore = async (tempFilePath) => {
  const lineIndex = getCurrentLineIndex()
  const line = getReadingLines()[lineIndex] || ''

  if (!tempFilePath || !line) {
    throw new Error('录音文件或诗句为空')
  }

  isScoring.value = true
  readFeedback.value = `⏳ 正在给第 ${lineIndex + 1} 句评分...`

  const audioBase64 = await fileToBase64(tempFilePath)
  const res = await API.scoreReading(audioBase64, line, 'mp3')
  const stars = Number(res?.stars || 0)
  const score = Number(res?.score || stars * 20 || 0)
  const passed = Boolean(res?.passed)

  earnedStars.value = stars

  if (passed) {
    if (!completedReadLines.value.includes(lineIndex)) {
      completedReadLines.value = [...completedReadLines.value, lineIndex].sort((a, b) => a - b)
    }

    moveToNextReadLine()
    return
  }

  activeReadLine.value = lineIndex
  readFeedback.value = res?.message || `😅 第 ${lineIndex + 1} 句得了 ${score} 分，再听一遍范读后重新录音吧！`
}

const requestRecordPermission = () => {
  return new Promise((resolve) => {
    if (!canUseUniRecorderManager()) {
      resolve(true)
      return
    }

    if (typeof uni.authorize !== 'function') {
      resolve(true)
      return
    }

    uni.authorize({
      scope: 'scope.record',
      success: () => resolve(true),
      fail: () => {
        uni.showModal({
          title: '需要麦克风权限',
          content: '请允许使用麦克风，才能一句一句录音跟读哦。',
          confirmText: '去设置',
          cancelText: '取消',
          success: (modalRes) => {
            if (modalRes.confirm && typeof uni.openSetting === 'function') {
              uni.openSetting({
                success: (settingRes) => {
                  resolve(Boolean(settingRes.authSetting?.['scope.record']))
                },
                fail: () => resolve(false)
              })
              return
            }

            resolve(false)
          },
          fail: () => resolve(false)
        })
      }
    })
  })
}

const stopBrowserAudioStream = () => {
  if (!browserAudioStream.value) return

  browserAudioStream.value.getTracks().forEach((track) => {
    try {
      track.stop()
    } catch (err) {
      console.log('停止浏览器麦克风轨道失败：', err)
    }
  })

  browserAudioStream.value = null
}

const getBrowserAudioMimeType = () => {
  if (typeof MediaRecorder === 'undefined') return ''

  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/wav'
  ]

  return candidates.find(type => MediaRecorder.isTypeSupported(type)) || ''
}

const getAudioFormatFromMimeType = (mimeType = '') => {
  if (mimeType.includes('mp4')) return 'mp4'
  if (mimeType.includes('wav')) return 'wav'
  if (mimeType.includes('mpeg') || mimeType.includes('mp3')) return 'mp3'
  return 'webm'
}

const startBrowserRecording = async (lineIndex, line) => {
  if (
    typeof navigator === 'undefined' ||
    !navigator.mediaDevices ||
    !navigator.mediaDevices.getUserMedia ||
    typeof MediaRecorder === 'undefined'
  ) {
    throw new Error('当前电脑浏览器不支持录音，请用 Chrome/Edge，或在手机真机/小程序/App 中测试')
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mimeType = getBrowserAudioMimeType()
  const recorder = mimeType
    ? new MediaRecorder(stream, { mimeType })
    : new MediaRecorder(stream)

  browserAudioStream.value = stream
  browserMediaRecorder.value = recorder
  browserAudioChunks.value = []

  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      browserAudioChunks.value.push(event.data)
    }
  }

  recorder.onstart = () => {
    isRecording.value = true
    activeReadLine.value = lineIndex
    readFeedback.value = `🎙️ 正在录第 ${lineIndex + 1} 句，请大声读：${line}`
    console.log('浏览器录音已开始')
  }

  recorder.onerror = (event) => {
    clearRecordStopTimer()
    isRecording.value = false
    isScoring.value = false
    stopBrowserAudioStream()
    console.log('浏览器录音失败：', event)
    readFeedback.value = '录音失败，请重新试一次'
    uni.showToast({
      title: '录音失败',
      icon: 'none'
    })
  }

  recorder.onstop = async () => {
    clearRecordStopTimer()
    isRecording.value = false

    try {
      const audioBlob = new Blob(browserAudioChunks.value, {
        type: recorder.mimeType || mimeType || 'audio/webm'
      })

      if (!audioBlob.size) {
        throw new Error('没有录到声音')
      }

      isScoring.value = true
      readFeedback.value = `⏳ 正在给第 ${lineIndex + 1} 句评分...`

      const audioBase64 = await blobToBase64(audioBlob)
      const audioFormat = getAudioFormatFromMimeType(audioBlob.type)
      const res = await API.scoreReading(audioBase64, line, audioFormat)
      const stars = Number(res?.stars || 0)
      const score = Number(res?.score || stars * 20 || 0)
      const passed = Boolean(res?.passed)

      earnedStars.value = stars

      if (passed) {
        if (!completedReadLines.value.includes(lineIndex)) {
          completedReadLines.value = [...completedReadLines.value, lineIndex].sort((a, b) => a - b)
        }

        moveToNextReadLine()
      } else {
        activeReadLine.value = lineIndex
        readFeedback.value = res?.message || `😅 第 ${lineIndex + 1} 句得了 ${score} 分，再听一遍范读后重新录音吧！`
      }
    } catch (err) {
      console.log('浏览器当前句跟读评分失败：', err)
      activeReadLine.value = lineIndex
      readFeedback.value = err?.data?.message || err?.message || '评分接口暂不可用，请检查 /asr/score 是否可用'
      uni.showToast({
        title: '评分失败，请重试',
        icon: 'none'
      })
    } finally {
      isScoring.value = false
      browserMediaRecorder.value = null
      browserAudioChunks.value = []
      stopBrowserAudioStream()
    }
  }

  recorder.start()
  isRecording.value = true

  recordStopTimer.value = setTimeout(() => {
    if (isRecording.value && browserMediaRecorder.value) {
      try {
        browserMediaRecorder.value.stop()
      } catch (err) {
        console.log('自动停止浏览器录音失败：', err)
      }
    }
  }, MAX_RECORD_DURATION_MS)
}

const canUseUniRecorderManager = () => {
  return typeof uni.getRecorderManager === 'function'
}

const initRecorderManager = () => {
  if (recorderManager.value) return recorderManager.value

  if (!canUseUniRecorderManager()) {
    throw new Error('当前环境不支持 uni.getRecorderManager')
  }

  const recorder = uni.getRecorderManager()
  recorderManager.value = recorder

  recorder.onStart(() => {
    isRecording.value = true
    console.log('录音已开始')
  })

  recorder.onStop(async (res) => {
    clearRecordStopTimer()
    isRecording.value = false

    try {
      if (!res.tempFilePath) {
        throw new Error('没有拿到录音文件')
      }

      await submitCurrentLineScore(res.tempFilePath)
    } catch (err) {
      console.log('当前句跟读评分失败：', err)
      readFeedback.value = err?.data?.message || err?.message || '评分接口暂不可用，请检查 /asr/score 是否可用'
      uni.showToast({
        title: '评分失败，请重试',
        icon: 'none'
      })
    } finally {
      isScoring.value = false
    }
  })

  recorder.onError((err) => {
    clearRecordStopTimer()
    isRecording.value = false
    isScoring.value = false
    console.log('录音失败：', err)
    readFeedback.value = '录音失败，请重新试一次'
    uni.showToast({
      title: '录音失败',
      icon: 'none'
    })
  })

  return recorder
}

const stopCurrentRecording = () => {
  clearRecordStopTimer()

  if (browserMediaRecorder.value) {
    try {
      if (browserMediaRecorder.value.state !== 'inactive') {
        browserMediaRecorder.value.stop()
      }
    } catch (err) {
      console.log('停止浏览器录音失败：', err)
      stopBrowserAudioStream()
    }

    return
  }

  try {
    const recorder = initRecorderManager()
    recorder.stop()
  } catch (err) {
    console.log('停止录音失败：', err)
  }
}

const recordReading = async () => {
  if (isScoring.value) return

  if (isRecording.value) {
    stopCurrentRecording()
    return
  }

  const lineIndex = getCurrentLineIndex()
  const line = getReadingLines()[lineIndex] || ''

  if (!line) {
    uni.showToast({
      title: '暂无可跟读内容',
      icon: 'none'
    })
    return
  }

  stopReadingAudio(true)

  const hasPermission = await requestRecordPermission()

  if (!hasPermission) {
    activeReadLine.value = lineIndex
    readFeedback.value = '请先打开麦克风权限，再录音跟读这一句哦。'
    uni.showToast({
      title: '未获得录音权限',
      icon: 'none'
    })
    return
  }

  earnedStars.value = 0
  activeReadLine.value = lineIndex
  readFeedback.value = `🎙️ 正在请求麦克风权限，请允许后朗读第 ${lineIndex + 1} 句`

  try {
    if (!canUseUniRecorderManager()) {
      await startBrowserRecording(lineIndex, line)
      return
    }

    const recorder = initRecorderManager()

    recorder.start({
      duration: MAX_RECORD_DURATION_MS,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 96000,
      format: 'mp3'
    })

    // 部分端不会立即触发 onStart，先把按钮状态切到录音中；失败会走 onError 或 catch 恢复。
    isRecording.value = true
    readFeedback.value = `🎙️ 正在录第 ${lineIndex + 1} 句，请大声读：${line}`

    recordStopTimer.value = setTimeout(() => {
      if (isRecording.value) {
        stopCurrentRecording()
      }
    }, MAX_RECORD_DURATION_MS)
  } catch (err) {
    clearRecordStopTimer()
    isRecording.value = false
    isScoring.value = false
    activeReadLine.value = lineIndex
    console.log('启动录音失败：', err)
    readFeedback.value = err?.message || '录音没有启动，请检查麦克风权限后重试'
    uni.showToast({
      title: '录音未启动',
      icon: 'none'
    })
  }
}

const toastNeedRecord = () => {
  uni.showToast({
    title: '请先逐句完成跟读',
    icon: 'none'
  })
}

const goMatch = () => {
  stopReadingAudio()

  selectedLeft.value = null
  matchedIds.value = []
  matchFeedback.value = '💡 请先完成第 1 句，再完成第 2、3、4 句'
  matchSuccess.value = false
  isSubmittingResult.value = false
  resultSubmitted.value = false

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

const submitConsolidationPassed = async () => {
  if (isSubmittingResult.value || resultSubmitted.value) return

  const poem = currentReviewPoem.value

  if (!poem || !poem.poem_id) return

  isSubmittingResult.value = true
  matchFeedback.value = '🎉 太棒了！正在保存巩固结果...'

  try {
    await API.submitConsolidationResult(poem.poem_id, true)

    resultSubmitted.value = true
    updateReviewPoem(poem.key, {
      passed: true,
      status: '已掌握'
    })

    matchFeedback.value = '🎉 太棒了！巩固结果已保存！'
  } catch (err) {
    console.log('提交巩固结果失败：', err)

    matchFeedback.value = '🎉 练习已完成，但巩固结果保存失败，请稍后再试'

    uni.showToast({
      title: '结果保存失败',
      icon: 'none'
    })
  } finally {
    isSubmittingResult.value = false
  }
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
      submitConsolidationPassed()
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
  completedReadLines.value = []
  isRecording.value = false
  isScoring.value = false
  readFeedback.value = '💡 小朋友要一句一句听范读，再一句一句录音跟读哦！'
}

onMounted(() => {
  loadConsolidationList()
})

onUnmounted(() => {
  stopReadingAudio()
  clearRecordStopTimer()
  if (isRecording.value) {
    stopCurrentRecording()
  }

  stopBrowserAudioStream()
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
  max-width: none;
  max-height: none;
  transform-origin: center center;
  will-change: transform;
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
  min-height: 0;
}

.section-title {
  font-size: 18px;
  font-weight: 900;
  color: #5b508d;
}

.poem-list {
  flex: 1;
  min-height: 0;
  max-height: 244px;
  overflow: hidden;
}

.poem-list :deep(.uni-scroll-view-content),
.poem-list ::v-deep .uni-scroll-view-content {
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

.read-line.completed {
  border-color: rgba(82, 196, 26, 0.35);
  background: rgba(230, 255, 247, 0.94);
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
.list-message {
  min-height: 96px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  color: #9a90c0;
  font-size: 14px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 14px rgba(74, 55, 42, 0.08);
}

.list-warning {
  padding: 7px 12px;
  border-radius: 14px;
  background: rgba(255, 244, 230, 0.9);
  color: #ff914d;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.4;
}

.complete-btn[disabled] {
  opacity: 0.65;
}

</style>