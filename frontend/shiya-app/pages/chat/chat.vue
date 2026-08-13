<template>
  <view class="page-root">
    <view class="chat-app" :style="appScaleStyle">
      <image class="chat-bg" src="/static/final-ui/chat_with_poet.jpg" mode="scaleToFill" />
      <view class="page">
        <view class="topbar">
          <view class="back art-back-small" @tap.stop="goBack"><image src="/static/final-ui/nav-back.png" mode="aspectFit" /></view>

          <view class="title-pill" @tap.stop="speakText('和诗人聊聊')">
            <view class="logo">🌱</view>
            <text>和诗人聊聊</text>
          </view>

          <button
            class="next-btn"
            :class="{ active: canNext }"
            @tap="handleNext"
          >
            下一步 →
          </button>
        </view>

        <view class="main-layout">
          <view class="poet-stage">
            <view class="poet-name" @tap.stop="speakText(poemData.author)">{{ poemData.author }}</view>

            <view class="left-poem-card">
              <view class="left-poem-title">正在学习《{{ poemData.title }}》</view>
              <view class="left-poem-author">{{ poemData.dynasty }} · {{ poemData.author }}</view>
            </view>

            <image class="poet-img-large" :src="poetAvatarImage" mode="aspectFill" @error="handlePoetAvatarError"></image>
          </view>

          <view class="dialog-panel">
            <scroll-view class="chat-card" scroll-y :scroll-top="chatScrollTop">
              <view
                v-for="(msg, index) in messages"
                :key="index"
                class="bubble-row"
                :class="msg.role"
              >
                <view v-if="msg.role === 'poet'" class="mini-avatar">
                  <image class="poet-face-image" :src="poetAvatarImage" mode="aspectFill" @error="handlePoetAvatarError"></image>
                </view>

                <view class="bubble-stack">
                  <view class="bubble">{{ msg.text }}</view>

                  <view
                    v-if="msg.role === 'poet' && msg.audioUrl"
                    class="audio-status"
                    :class="{ speaking: msg.audioState === 'playing' }"
                  >
                    <text class="audio-icon">{{ msg.audioState === 'playing' ? '🔊' : '🎧' }}</text>
                    <text class="audio-text">{{ getAudioStateText(msg) }}</text>
                    <button class="replay-btn" @tap.stop="replayPoetAudio(index)">
                      {{ msg.audioState === 'playing' ? '重播' : '重新播放' }}
                    </button>
                  </view>
                </view>
              </view>

              <view v-if="isReplying" class="bubble-row poet">
                <view class="mini-avatar">
                  <image class="poet-face-image" :src="poetAvatarImage" mode="aspectFill" @error="handlePoetAvatarError"></image>
                </view>

                <view class="bubble">正在想一想怎么回答你……</view>
              </view>

              <view class="suggest-box">
                <view class="suggest-title">接下来想问：</view>

                <view class="chips">
                  <view
                    v-for="item in suggestions"
                    :key="item"
                    class="chip"
                    @tap="askSuggestion(item)"
                  >
                    {{ item }}
                  </view>
                </view>
              </view>
            </scroll-view>

            <view class="input-bar">
              <button
                class="mode-btn"
                :class="{ recording: isVoiceRecording }"
                @tap="switchInputMode"
              >
                {{ inputMode === 'voice' ? '⌨️' : '🎙️' }}
              </button>

              <button
                v-if="inputMode === 'voice'"
                class="voice-hold-btn"
                :class="{ recording: isVoiceRecording, recognizing: isRecognizingVoice }"
                @touchstart.stop.prevent="handleVoiceTouchStart"
                @touchend.stop.prevent="handleVoicePressEnd"
                @touchcancel.stop.prevent="handleVoicePressEnd"
                @mousedown.stop.prevent="handleVoiceMouseStart"
                @mouseup.stop.prevent="handleVoicePressEnd"
                @mouseleave.stop.prevent="handleVoicePressEnd"
                @longpress.stop.prevent="handleVoiceLongPress"
              >
                <text class="voice-hold-icon">{{ isVoiceRecording ? '🔴' : '🎙️' }}</text>
                <text>{{ isRecognizingVoice ? '正在识别...' : isVoiceRecording ? '松开发送' : '按住 说话' }}</text>
              </button>

              <input
                v-else
                class="text-input"
                v-model="userInput"
                placeholder="问问诗人这首诗里的问题"
                confirm-type="send"
                @confirm="sendMessage"
              />

              <button v-if="inputMode === 'text'" class="send-btn" @tap="sendMessage">➤</button>
            </view>
          </view>
        </view>
      </view>

      <view v-if="showReviewGuide" class="review-guide-mask">
        <view class="review-guide-card">
          <view class="review-guide-title">学完这首古诗啦</view>
          <view class="review-guide-text">小朋友，你已经学完了这首古诗，想要点亮的话就去练一练吧~</view>
          <view class="review-guide-actions">
            <button class="review-guide-btn primary" @tap="goReview">去练一练</button>
            <button class="review-guide-btn secondary" @tap="goHome">返回主页</button>
          </view>
          <view class="review-guide-checkbox" @tap="skipReviewGuideToday = !skipReviewGuideToday">
            <view class="checkbox-box" :class="{ checked: skipReviewGuideToday }">{{ skipReviewGuideToday ? '✓' : '' }}</view>
            <text>今日不再提示</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { API, getLocalPoemById, normalizeAssetUrl, getPoetAvatarStaticUrl } from '@/utils/api.js'
import { speakText } from '@/utils/speech.js'
import { isLiveAsrActive, startLiveAsr, stopLiveAsr } from '@/utils/live-asr.js'

const DESIGN_WIDTH = 1672
const DESIGN_HEIGHT = 770
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

  poetAudioRequestToken += 1
  stopChatReplyAudio(false)
})

onUnload(() => {
  poetAudioRequestToken += 1
  stopLiveAsr()
  stopChatReplyAudio(false)
})

const poemId = ref('poem_001')
const poemData = ref(getLocalPoemById('poem_001'))
const childAge = ref(4)

const normalizeAge = (value) => {
  const match = String(value || '').match(/\d+/)
  return match ? Number(match[0]) : 4
}

const userInput = ref('')
const inputMode = ref('voice')
const chatScrollTop = ref(0)
const canNext = ref(false)
const showReviewGuide = ref(false)
const skipReviewGuideToday = ref(false)
const isReplying = ref(false)
const poetAvatarUrl = ref('')
const replyAudioContext = ref(null)
const playingAudioMessageIndex = ref(-1)
const currentReplyAudioUrl = ref('')
let poetAudioRequestToken = 0

const isVoiceRecording = ref(false)
const isRecognizingVoice = ref(false)
const isVoicePressing = ref(false)
const lastVoiceTouchTime = ref(0)
const chatRecorderManager = ref(null)
const chatRecordStopTimer = ref(null)
const chatBrowserMediaRecorder = ref(null)
const chatBrowserAudioChunks = ref([])
const chatBrowserAudioStream = ref(null)

const MAX_CHAT_RECORD_DURATION_MS = 30000
let chatRequestToken = 0

const poetAvatarImage = computed(() => {
  return poetAvatarUrl.value || getPoetAvatarStaticUrl(getPoetName()) || '/static/meng-haoran.png'
})

const messages = ref([])

// 这个 history 是专门传给后端 /chat 的
// 后端需要的格式是：
// [
//   { role: 'user', content: '...' },
//   { role: 'assistant', content: '...' }
// ]
const history = ref([])

const suggestions = ref([
  '这首诗是什么意思？',
  '诗人当时开心吗？',
  '这句诗里有什么画面？',
  '这首诗适合什么时候读？'
])

const getChatReplyAudioPath = (res = {}) => {
  return res?.audio?.url || res?.audio_url || ''
}

const normalizeChatAudioUrl = (url = '') => {
  const value = String(url || '').trim()

  if (!value) return ''

  if (value.startsWith('data:audio') || value.startsWith('blob:')) {
    return value
  }

  return normalizeAssetUrl(value)
}

const updateAudioMessageState = (index, audioState) => {
  if (index < 0 || !messages.value[index] || !messages.value[index].audioUrl) return

  messages.value[index] = {
    ...messages.value[index],
    audioState
  }
}

const getAudioStateText = (msg = {}) => {
  if (msg.audioState === 'playing') return '诗人正在说话'
  if (msg.audioState === 'loading') return '准备播放...'
  if (msg.audioState === 'error') return '语音暂时不能播放'
  return '语音已就绪'
}

const cleanupReplyAudio = (audioContext) => {
  if (replyAudioContext.value !== audioContext) return

  replyAudioContext.value = null
  playingAudioMessageIndex.value = -1
  currentReplyAudioUrl.value = ''
}

const destroyReplyAudioContext = (audioContext) => {
  if (!audioContext) return

  try {
    if (typeof audioContext.pause === 'function') {
      audioContext.pause()
    }
  } catch (err) {
    console.log('暂停诗人语音失败：', err)
  }

  try {
    if (typeof audioContext.stop === 'function') {
      audioContext.stop()
    }
  } catch (err) {
    console.log('停止诗人语音失败：', err)
  }

  try {
    if (typeof audioContext.destroy === 'function') {
      audioContext.destroy()
    }
  } catch (err) {
    console.log('释放诗人语音失败：', err)
  }

  try {
    if ('src' in audioContext) {
      audioContext.src = ''
    }
  } catch (err) {
    console.log('清空诗人语音地址失败：', err)
  }
}

const stopChatReplyAudio = (resetMessageState = true) => {
  const currentIndex = playingAudioMessageIndex.value

  if (resetMessageState && currentIndex >= 0) {
    updateAudioMessageState(currentIndex, 'ready')
  }

  const audioContext = replyAudioContext.value
  replyAudioContext.value = null
  playingAudioMessageIndex.value = -1
  currentReplyAudioUrl.value = ''

  destroyReplyAudioContext(audioContext)
}

const playByUniInnerAudioContext = (audioUrl, messageIndex, showFailToast = false) => {
  let audioContext = null

  try {
    audioContext = uni.createInnerAudioContext()
  } catch (err) {
    console.log('创建诗人语音播放器失败：', err)
    updateAudioMessageState(messageIndex, 'error')
    return
  }

  replyAudioContext.value = audioContext
  playingAudioMessageIndex.value = messageIndex
  currentReplyAudioUrl.value = audioUrl
  updateAudioMessageState(messageIndex, 'loading')

  // 部分 Android/uni-app 运行环境只暴露 obeyMuteSwitch 的只读 getter，
  // 直接赋值会抛异常并让已经成功的 /chat 请求被外层 catch 误判为失败。
  // 自动播放不依赖该属性，因此这里不再修改它。
  audioContext.autoplay = false
  audioContext.src = audioUrl

  audioContext.onPlay(() => {
    if (replyAudioContext.value !== audioContext) return
    updateAudioMessageState(messageIndex, 'playing')
  })

  audioContext.onEnded(() => {
    if (replyAudioContext.value !== audioContext) return
    updateAudioMessageState(messageIndex, 'ready')
    cleanupReplyAudio(audioContext)
    destroyReplyAudioContext(audioContext)
  })

  audioContext.onStop(() => {
    if (replyAudioContext.value !== audioContext) return
    updateAudioMessageState(messageIndex, 'ready')
    cleanupReplyAudio(audioContext)
  })

  audioContext.onError((err) => {
    if (replyAudioContext.value !== audioContext) return

    console.log('诗人语音播放失败：', err)
    updateAudioMessageState(messageIndex, 'error')
    cleanupReplyAudio(audioContext)
    destroyReplyAudioContext(audioContext)

    if (showFailToast) {
      toast('语音播放失败，请稍后再试')
    }
  })

  try {
    audioContext.play()
  } catch (err) {
    console.log('启动诗人语音失败：', err)
    updateAudioMessageState(messageIndex, 'error')
    cleanupReplyAudio(audioContext)
    destroyReplyAudioContext(audioContext)

    if (showFailToast) {
      toast('语音播放失败，请稍后再试')
    }
  }
}

const playByBrowserAudio = (audioUrl, messageIndex, showFailToast = false) => {
  const audioContext = new Audio(audioUrl)

  replyAudioContext.value = audioContext
  playingAudioMessageIndex.value = messageIndex
  currentReplyAudioUrl.value = audioUrl
  updateAudioMessageState(messageIndex, 'loading')

  audioContext.preload = 'auto'

  audioContext.onplaying = () => {
    if (replyAudioContext.value !== audioContext) return
    updateAudioMessageState(messageIndex, 'playing')
  }

  audioContext.onended = () => {
    if (replyAudioContext.value !== audioContext) return
    updateAudioMessageState(messageIndex, 'ready')
    cleanupReplyAudio(audioContext)
    destroyReplyAudioContext(audioContext)
  }

  audioContext.onerror = (err) => {
    if (replyAudioContext.value !== audioContext) return

    console.log('浏览器播放诗人语音失败：', err)
    updateAudioMessageState(messageIndex, 'error')
    cleanupReplyAudio(audioContext)
    destroyReplyAudioContext(audioContext)

    if (showFailToast) {
      toast('语音播放失败，请稍后再试')
    }
  }

  const playResult = audioContext.play()

  if (playResult && typeof playResult.catch === 'function') {
    playResult.catch((err) => {
      if (replyAudioContext.value !== audioContext) return

      console.log('浏览器自动播放诗人语音被拦截或失败：', err)
      updateAudioMessageState(messageIndex, 'error')
      cleanupReplyAudio(audioContext)
      destroyReplyAudioContext(audioContext)

      if (showFailToast) {
        toast('语音播放失败，请稍后再试')
      }
    })
  }
}

const playPoetAudio = (audioPath, messageIndex, showFailToast = false) => {
  const audioUrl = normalizeChatAudioUrl(audioPath)

  if (!audioUrl) return

  stopChatReplyAudio()

  try {
    if (typeof uni.createInnerAudioContext === 'function') {
      playByUniInnerAudioContext(audioUrl, messageIndex, showFailToast)
      return
    }

    if (typeof Audio !== 'undefined') {
      playByBrowserAudio(audioUrl, messageIndex, showFailToast)
      return
    }

    updateAudioMessageState(messageIndex, 'error')
  } catch (err) {
    // 播放失败只影响语音，不能把已经成功取得的诗人文字回复变成本地假回复。
    console.log('播放诗人语音时发生兼容错误：', err)
    updateAudioMessageState(messageIndex, 'error')
    stopChatReplyAudio(false)
  }
}

const replayPoetAudio = (messageIndex) => {
  const message = messages.value[messageIndex]

  if (!message?.audioUrl) return

  playPoetAudio(message.audioUrl, messageIndex, true)
}

const appendPoetMessage = (text, res = {}) => {
  const audioUrl = normalizeChatAudioUrl(getChatReplyAudioPath(res))
  const messageIndex = messages.value.length

  messages.value.push({
    role: 'poet',
    text,
    audioUrl,
    audioState: audioUrl ? 'ready' : ''
  })

  if (audioUrl) {
    playPoetAudio(audioUrl, messageIndex)
  }

  return messageIndex
}

const requestPoetMessageAudio = async (text, messageIndex) => {
  const requestToken = ++poetAudioRequestToken

  try {
    const res = await API.generatePoetSpeech(getPoetName(), text)
    if (requestToken !== poetAudioRequestToken) return

    const audioUrl = normalizeChatAudioUrl(getChatReplyAudioPath(res))
    if (!res?.success || !audioUrl || !messages.value[messageIndex]) return

    messages.value[messageIndex] = {
      ...messages.value[messageIndex],
      audioUrl,
      audioState: 'ready'
    }
    playPoetAudio(audioUrl, messageIndex)
  } catch (err) {
    if (requestToken !== poetAudioRequestToken) return
    console.log('诗人文字已显示，语音稍后生成失败：', err)
  }
}


onLoad(async (options) => {
  poemId.value = options.poem_id || 'poem_001'
  childAge.value = normalizeAge(
    options.age ||
    uni.getStorageSync('shiYaChildAge') ||
    uni.getStorageSync('shiYaChildAgeText') ||
    4
  )
  poemData.value = getLocalPoemById(poemId.value)

  // 优先从后端获取古诗详情
  // 如果后端失败，就继续使用 api.js 里的 LOCAL_POEMS 本地数据
  try {
    const detailRes = await API.getPoemDetail(poemId.value)

    if (detailRes && detailRes.success && detailRes.data) {
      poemData.value = detailRes.data
    }
  } catch (err) {
    console.log('古诗详情接口暂不可用，使用本地数据', err)
  }

  loadPoetAvatar()
  await initPoetChat()
})

const getPoemContentText = () => {
  if (!poemData.value) return ''

  if (Array.isArray(poemData.value.content)) {
    return poemData.value.content.join('，')
  }

  return String(poemData.value.content || '')
}

const getPoetName = () => {
  return poemData.value.author || poemData.value.poet_name || '古代诗人'
}

const getPoetDynasty = () => {
  return poemData.value.dynasty || '唐'
}

const handlePoetAvatarError = () => {
  if (poetAvatarUrl.value) {
    poetAvatarUrl.value = ''
    return
  }

  console.log('诗人头像加载失败，使用本地默认头像')
}

const loadPoetAvatar = async () => {
  const poetName = getPoetName()
  const dynasty = getPoetDynasty()

  // 先尝试已有静态头像，比如 /static/images/poets/李白.jpg；
  // 然后继续调用 /generate/peot_avatar，接口返回后再覆盖。
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

const initPoetChat = async () => {
  stopChatReplyAudio(false)

  isReplying.value = true
  messages.value = []
  history.value = []

  try {
    const res = await API.chatWithPoet({
      message: '__init__',
      poet_name: getPoetName(),
      dynasty: getPoetDynasty(),
      poem_title: poemData.value.title || '',
      poem_content: getPoemContentText(),
      history: [],
      age: childAge.value,
      include_audio: false
    })

    if (res && res.success && res.reply) {
      const messageIndex = appendPoetMessage(res.reply, res)
      if (!getChatReplyAudioPath(res)) {
        requestPoetMessageAudio(res.reply, messageIndex)
      }

      history.value = [
        {
          role: 'assistant',
          content: res.reply
        }
      ]
    } else {
      const fallbackText = `小朋友你好，我是${poemData.value.dynasty || '唐'}代诗人${poemData.value.author}。你刚刚学习了《${poemData.value.title}》，现在可以问我问题。`

      appendPoetMessage(fallbackText)

      history.value = [
        {
          role: 'assistant',
          content: fallbackText
        }
      ]
    }
  } catch (err) {
    console.log('诗人开场白接口失败，使用本地开场白', err)

    const fallbackText = `小朋友你好，我是${poemData.value.dynasty || '唐'}代诗人${poemData.value.author}。你刚刚学习了《${poemData.value.title}》，现在可以问我问题。`

    appendPoetMessage(fallbackText)

    history.value = [
      {
        role: 'assistant',
        content: fallbackText
      }
    ]
  } finally {
    isReplying.value = false
    chatScrollTop.value += 200
  }
}

const goBack = () => {
  stopChatReplyAudio(false)

  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
  const fallbackUrl = `/pages/study/study?poem_id=${poemId.value || poemData.id || 'poem_001'}`

  if (pages.length > 1) {
    uni.navigateBack({
      delta: 1,
      fail: () => {
        uni.reLaunch({
          url: fallbackUrl
        })
      }
    })
    return
  }

  uni.reLaunch({
    url: fallbackUrl,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.replace(`#${fallbackUrl}`)
      }
    }
  })
}

const fakeReply = (text) => {
  if (text.includes('意思') || text.includes('什么意思')) {
    return `《${poemData.value.title}》这首诗写的是一个很美的画面。你可以先想一想诗里出现了什么，再慢慢读每一句。`
  }

  if (text.includes('鸟')) {
    return '鸟儿在诗里出现，是为了让画面变得更热闹。小朋友读到鸟叫，就像真的听见春天来了。'
  }

  if (text.includes('开心') || text.includes('心情')) {
    return `写《${poemData.value.title}》的时候，诗人看见眼前的景色，心里有一种特别深的感受，所以把它写成了诗。`
  }

  if (text.includes('为什么')) {
    return '你问得真好。古诗里的每一句话，都是诗人看到、听到或者想到的东西。我们可以一句一句慢慢看。'
  }

  return `小朋友，这个问题问得很好。我们正在学习《${poemData.value.title}》，你可以把诗里的画面想出来，这样就更容易明白它了。`
}


const clearChatRecordStopTimer = () => {
  if (chatRecordStopTimer.value) {
    clearTimeout(chatRecordStopTimer.value)
    chatRecordStopTimer.value = null
  }
}

const canUseUniRecorderManager = () => {
  return typeof uni.getRecorderManager === 'function'
}

const requestChatRecordPermission = () => {
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
          content: '请允许使用麦克风，才能把你说的话发给诗人哦。',
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

const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      const result = String(reader.result || '')
      resolve(result.includes(',') ? result.split(',')[1] : result)
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

const stopChatBrowserAudioStream = () => {
  if (!chatBrowserAudioStream.value) return

  chatBrowserAudioStream.value.getTracks().forEach((track) => {
    try {
      track.stop()
    } catch (err) {
      console.log('停止聊天录音麦克风轨道失败：', err)
    }
  })

  chatBrowserAudioStream.value = null
}

const submitVoiceToChat = async (audioBase64, audioFormat = 'mp3') => {
  isRecognizingVoice.value = true

  try {
    const res = await API.speechToText(audioBase64, audioFormat)
    const text = String(res?.text || res?.data?.text || res?.recognized || '').trim()

    if (!res?.success || !text) {
      throw new Error(res?.message || '没有识别到内容')
    }

    userInput.value = text
    // 新增这一行：识别出文字立刻取消“正在识别”状态
    isRecognizingVoice.value = false
    await sendMessage()
  } catch (err) {
    console.log('聊天语音识别失败：', err)
    toast('语音识别失败，请重试')
  } finally {
    isRecognizingVoice.value = false
  }
}

const startChatBrowserRecording = async () => {
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

  chatBrowserAudioStream.value = stream
  chatBrowserMediaRecorder.value = recorder
  chatBrowserAudioChunks.value = []

  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      chatBrowserAudioChunks.value.push(event.data)
    }
  }

  recorder.onstart = () => {
    isVoiceRecording.value = true
    toast('正在录音，松开发送')
  }

  recorder.onerror = (event) => {
    clearChatRecordStopTimer()
    isVoiceRecording.value = false
    stopChatBrowserAudioStream()
    console.log('聊天浏览器录音失败：', event)
    toast('录音失败，请重试')
  }

  recorder.onstop = async () => {
    clearChatRecordStopTimer()
    isVoiceRecording.value = false

    try {
      const audioBlob = new Blob(chatBrowserAudioChunks.value, {
        type: recorder.mimeType || mimeType || 'audio/webm'
      })

      if (!audioBlob.size) {
        throw new Error('没有录到声音')
      }

      const audioBase64 = await blobToBase64(audioBlob)
      const audioFormat = getAudioFormatFromMimeType(audioBlob.type)
      await submitVoiceToChat(audioBase64, audioFormat)
    } catch (err) {
      console.log('提交聊天浏览器录音失败：', err)
      toast('语音识别失败，请重试')
    } finally {
      chatBrowserMediaRecorder.value = null
      chatBrowserAudioChunks.value = []
      stopChatBrowserAudioStream()
    }
  }

  recorder.start()

  chatRecordStopTimer.value = setTimeout(() => {
    if (chatBrowserMediaRecorder.value && chatBrowserMediaRecorder.value.state !== 'inactive') {
      chatBrowserMediaRecorder.value.stop()
    }
  }, MAX_CHAT_RECORD_DURATION_MS)
}

const initChatRecorderManager = () => {
  if (chatRecorderManager.value) return chatRecorderManager.value

  if (!canUseUniRecorderManager()) {
    throw new Error('当前环境不支持 uni.getRecorderManager')
  }

  const recorder = uni.getRecorderManager()
  chatRecorderManager.value = recorder

  recorder.onStart(() => {
    isVoiceRecording.value = true
    toast('正在录音，松开发送')
  })

  recorder.onStop(async (res) => {
    clearChatRecordStopTimer()
    isVoiceRecording.value = false

    try {
      if (!res.tempFilePath) {
        throw new Error('没有拿到录音文件')
      }

      const audioBase64 = await fileToBase64(res.tempFilePath)
      await submitVoiceToChat(audioBase64, 'mp3')
    } catch (err) {
      console.log('提交聊天录音失败：', err)
      toast('语音识别失败，请重试')
    }
  })

  recorder.onError((err) => {
    clearChatRecordStopTimer()
    isVoiceRecording.value = false
    console.log('聊天录音失败：', err)
    toast('录音失败，请重试')
  })

  return recorder
}

const stopVoiceInput = () => {
  clearChatRecordStopTimer()

  if (isLiveAsrActive()) {
    isVoiceRecording.value = false
    isRecognizingVoice.value = true
    stopLiveAsr()
    return
  }

  if (chatBrowserMediaRecorder.value) {
    try {
      if (chatBrowserMediaRecorder.value.state !== 'inactive') {
        chatBrowserMediaRecorder.value.stop()
      }
    } catch (err) {
      console.log('停止浏览器聊天录音失败：', err)
      stopChatBrowserAudioStream()
    }

    return
  }

  try {
    const recorder = initChatRecorderManager()
    recorder.stop()
  } catch (err) {
    console.log('停止聊天录音失败：', err)
  }
}

const switchInputMode = () => {
  if (isVoiceRecording.value) {
    isVoicePressing.value = false
    stopVoiceInput()
  }

  inputMode.value = inputMode.value === 'voice' ? 'text' : 'voice'
}

const isAndroidApp = () => {
  // #ifdef APP-PLUS
  try {
    return uni.getSystemInfoSync()?.platform === 'android'
  } catch (err) {
    return false
  }
  // #endif

  // #ifndef APP-PLUS
  return false
  // #endif
}

const interruptPoetForLiveVoice = () => {
  poetAudioRequestToken += 1
  chatRequestToken += 1
  isReplying.value = false
  stopChatReplyAudio()
}

const startLiveVoiceInput = async () => {
  await startLiveAsr({
    onVoiceStart: interruptPoetForLiveVoice,
    onPartial: () => {},
    onFinal: async (recognizedText) => {
      isVoiceRecording.value = false
      isRecognizingVoice.value = false

      const text = String(recognizedText || '').trim()
      if (!text) {
        toast('没有识别到内容，请再说一次')
        return
      }

      userInput.value = text
      await sendMessage()
    },
    onError: (error) => {
      isVoiceRecording.value = false
      isRecognizingVoice.value = false
      isVoicePressing.value = false
      console.log('实时聊天语音识别失败：', error)
      toast('实时语音识别失败，请重试')
    }
  })

  isVoiceRecording.value = true
  toast('正在聆听，说话即可打断诗人')
  chatRecordStopTimer.value = setTimeout(() => {
    if (isVoiceRecording.value) {
      isVoicePressing.value = false
      stopVoiceInput()
    }
  }, MAX_CHAT_RECORD_DURATION_MS)
}

const startVoiceInput = async () => {
  if (isRecognizingVoice.value || isVoiceRecording.value) return

  const hasPermission = await requestChatRecordPermission()

  if (!hasPermission) {
    toast('未获得麦克风权限')
    return
  }

  try {
    if (isAndroidApp()) {
      await startLiveVoiceInput()
      return
    }

    if (!canUseUniRecorderManager()) {
      await startChatBrowserRecording()
      return
    }

    const recorder = initChatRecorderManager()

    recorder.start({
      duration: MAX_CHAT_RECORD_DURATION_MS,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 96000,
      format: 'mp3'
    })

    isVoiceRecording.value = true

    chatRecordStopTimer.value = setTimeout(() => {
      if (isVoiceRecording.value) {
        isVoicePressing.value = false
        stopVoiceInput()
      }
    }, MAX_CHAT_RECORD_DURATION_MS)
  } catch (err) {
    clearChatRecordStopTimer()
    isVoiceRecording.value = false
    isVoicePressing.value = false
    console.log('启动聊天录音失败：', err)
    toast('录音未启动')
  }
}

const handleVoicePressStart = async () => {
  if (inputMode.value !== 'voice' || isVoicePressing.value || isVoiceRecording.value) return

  isVoicePressing.value = true
  await startVoiceInput()

  if (!isVoicePressing.value && isVoiceRecording.value) {
    stopVoiceInput()
  }
}

const handleVoiceTouchStart = async () => {
  lastVoiceTouchTime.value = Date.now()
  await handleVoicePressStart()
}

const handleVoiceMouseStart = async () => {
  if (Date.now() - lastVoiceTouchTime.value < 700) return
  await handleVoicePressStart()
}

const handleVoicePressEnd = () => {
  if (!isVoicePressing.value && !isVoiceRecording.value) return

  isVoicePressing.value = false

  if (isVoiceRecording.value) {
    stopVoiceInput()
  }
}

const handleVoiceLongPress = () => {}


const sendMessage = async () => {
  const text = userInput.value.trim()
  if (!text) return

  const requestToken = ++chatRequestToken
  poetAudioRequestToken += 1
  stopChatReplyAudio()

  messages.value.push({
    role: 'user',
    text
  })

  userInput.value = ''
  isReplying.value = true
  chatScrollTop.value += 260

  try {
    const res = await API.chatWithPoet({
      message: text,
      poet_name: getPoetName(),
      dynasty: getPoetDynasty(),
      poem_title: poemData.value.title || '',
      poem_content: getPoemContentText(),
      history: history.value,
      age: childAge.value,
      include_audio: false
    })

    if (requestToken !== chatRequestToken) return

    if (res && res.success && res.reply) {
      const messageIndex = appendPoetMessage(res.reply, res)
      if (!getChatReplyAudioPath(res)) {
        requestPoetMessageAudio(res.reply, messageIndex)
      }

      history.value.push({
        role: 'user',
        content: text
      })

      history.value.push({
        role: 'assistant',
        content: res.reply
      })
    } else {
      const fallbackText = fakeReply(text)

      appendPoetMessage(fallbackText)

      history.value.push({
        role: 'user',
        content: text
      })

      history.value.push({
        role: 'assistant',
        content: fallbackText
      })
    }
  } catch (err) {
    if (requestToken !== chatRequestToken) return
    console.log('AI 对话接口暂不可用，使用本地假回复', err)

    const fallbackText = fakeReply(text)

    appendPoetMessage(fallbackText)

    history.value.push({
      role: 'user',
      content: text
    })

    history.value.push({
      role: 'assistant',
      content: fallbackText
    })
  }

  if (requestToken === chatRequestToken) {
    isReplying.value = false
    canNext.value = true
    chatScrollTop.value += 360
  }
}

const askSuggestion = (text) => {
  userInput.value = text
  sendMessage()
}

const handleNext = async () => {
  if (!canNext.value) {
    toast('先和诗人聊一句吧')
    return
  }

  stopChatReplyAudio(false)

  const now = new Date()
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  let suppressedToday = uni.getStorageSync('shiYaSkipReviewGuideDate') === today
  try {
    const reminder = await API.getReminderStatus()
    // 后端抑制状态必须明确属于今天，避免旧缓存/旧服务响应让弹窗永久消失。
    if (reminder?.date === today) {
      suppressedToday = suppressedToday || Boolean(reminder.practice_prompt_suppressed)
    }
  } catch (err) {
    console.log('读取今日巩固提醒状态失败，使用本地状态：', err)
  }
  if (suppressedToday) {
    goHome()
    return
  }

  showReviewGuide.value = true
}

const rememberReviewGuideChoice = async () => {
  if (!skipReviewGuideToday.value) return
  const now = new Date()
  uni.setStorageSync('shiYaSkipReviewGuideDate', `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`)
  try {
    await API.suppressPracticeReminderToday()
  } catch (err) {
    console.log('保存今日不再提醒失败，已保留本地设置：', err)
  }
}

const goReview = async () => {
  await rememberReviewGuideChoice()
  showReviewGuide.value = false
  uni.navigateTo({
    url: '/pages/review/review',
    animationType: 'fade-in',
    animationDuration: 100,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = '#/pages/review/review'
      }
    }
  })
}

const goHome = async () => {
  await rememberReviewGuideChoice()
  showReviewGuide.value = false
  uni.reLaunch({ url: '/pages/index/index' })
}

const toast = (title) => {
  uni.showToast({
    title,
    icon: 'none'
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

.chat-app {
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
    radial-gradient(circle at 8% 8%, rgba(255, 225, 105, 0.28), transparent 24%),
    radial-gradient(circle at 88% 18%, rgba(255, 210, 145, 0.16), transparent 25%),
    linear-gradient(180deg, #fffaf2 0%, #fff1e8 55%, #ffe9df 100%);
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
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  z-index: 9999;
  pointer-events: auto;
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
  color: #fff;
  font-size: 18px;
}

.next-btn {
  position: absolute;
  right: 0;
  top: 4px;
  height: 36px;
  border: 0;
  border-radius: 999px;
  padding: 0 18px;
  background: rgba(255, 255, 255, 0.72);
  color: #aaa0c8;
  font-size: 14px;
  font-weight: 900;
  box-shadow: 0 7px 16px rgba(112, 79, 54, 0.1);
}

.next-btn.active {
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: #ffffff;
}

.main-layout {
  min-height: 0;
  display: grid;
  grid-template-columns: 285px minmax(0, 1fr);
  gap: 16px;
}

.poet-stage {
  position: relative;
  min-width: 0;
  min-height: 0;
  border-radius: 28px;
  background:
    radial-gradient(circle at 50% 84%, rgba(139, 216, 157, 0.28), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.75), rgba(255, 248, 232, 0.9));
  box-shadow: 0 12px 24px rgba(74, 55, 42, 0.13);
  overflow: hidden;
  display: grid;
  place-items: end center;
  padding: 6px 8px 0;

  /* 加上这一行！*/
  height: 100%;
}
.poet-name {
  position: absolute;
  left: 16px;
  top: 16px;
  z-index: 3;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #5b508d;
  font-size: 18px;
  font-weight: 950;
  box-shadow: 0 7px 16px rgba(111, 84, 55, 0.1);
}

.left-poem-card {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 4;
  width: 145px;
  padding: 8px 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 18px rgba(111, 84, 55, 0.13);
  border: 2px solid rgba(255, 224, 87, 0.65);
}

.left-poem-title {
  font-size: 14px;
  font-weight: 950;
  color: #5b508d;
  line-height: 1.2;
}

.left-poem-author {
  margin-top: 3px;
  font-size: 12px;
  font-weight: 900;
  color: #ff914d;
}

.poet-img-large {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center bottom;
  border-radius: 26px 26px 0 0;
  background: #fff8ea;
  /* 这里先不要写 translateY，动画会覆盖 */
  transform: translateX(0);
  animation: poetFloat 2.8s ease-in-out infinite;
  transform-origin: center bottom;
  position: absolute;
  bottom: 0;
  left: 0;
}

@keyframes poetFloat {
  0%, 100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-4px) scale(1.015);
  }
}

.dialog-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) 54px;
  gap: 10px;
}

.chat-card {
  min-height: 0;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 13px 24px rgba(74, 55, 42, 0.12);
  padding: 12px;
  overflow: hidden;
}

.bubble-row {
  display: flex;
  margin: 5px 0;
  gap: 8px;
  align-items: flex-end;
}

.bubble-row.user {
  justify-content: flex-end;
}

.mini-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff0dc;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  overflow: hidden;
}

.mini-avatar image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 18%;
}

.poet-face-image {
  transform: scale(1.85);
  transform-origin: center 22%;
  /* 新增这一行，图片单独上移 */
  transform: scale(1.85) translateY(5px);
}

.bubble-stack {
  max-width: 84%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
}

.bubble-row.user .bubble-stack {
  align-items: flex-end;
}

.bubble {
  max-width: 100%;
  padding: 8px 11px;
  border-radius: 17px;
  font-size: 13px;
  line-height: 1.38;
  font-weight: 850;
}

.poet .bubble {
  background: #f4f1ff;
  color: #645a95;
  border-bottom-left-radius: 8px;
}

.user .bubble {
  background: linear-gradient(180deg, #ffac68, #ff853b);
  color: #fff;
  border-bottom-right-radius: 8px;
}

.audio-status {
  display: flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  min-height: 26px;
  padding: 3px 5px 3px 7px;
  border-radius: 999px;
  background: #fff7e9;
  color: #ff914d;
  font-size: 11px;
  font-weight: 950;
  box-shadow: inset 0 -1px 0 rgba(255, 145, 77, 0.12);
}

.audio-status.speaking {
  background: #eafff9;
  color: #2cbf9d;
}

.audio-icon {
  line-height: 1;
}

.audio-text {
  max-width: 92px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.replay-btn {
  height: 22px;
  margin: 0;
  padding: 0 8px;
  border: 0;
  border-radius: 999px;
  background: #ffffff;
  color: #5b508d;
  font-size: 11px;
  font-weight: 950;
  line-height: 22px;
  box-shadow: 0 2px 5px rgba(111, 84, 55, 0.1);
}

.suggest-box {
  margin: 6px 0 2px 40px;
  padding: 8px;
  border-radius: 18px;
  background: #fff7e9;
}

.suggest-title {
  font-size: 13px;
  font-weight: 950;
  color: #ff914d;
  margin-bottom: 7px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.chip {
  border-radius: 999px;
  padding: 5px 9px;
  background: #eafff9;
  color: #2cbf9d;
  font-size: 12px;
  font-weight: 950;
}

.input-bar {
  height: 54px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 2px 0;
}

.mode-btn,
.send-btn {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 50%;
  font-size: 20px;
  flex-shrink: 0;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  line-height: 1;
}

.mode-btn {
  background: #eafff9;
  color: #2cbf9d;
  box-shadow: 0 5px 0 #b9eee0;
}

.mode-btn.recording {
  background: #ffe8e8;
  color: #ff4d4f;
  box-shadow: 0 5px 0 #ffc1c1;
}

.voice-hold-btn {
  flex: 1;
  min-width: 0;
  height: 44px;
  border: 0;
  border-radius: 22px;
  background: #f7f4ff;
  color: #5b508d;
  font-size: 15px;
  font-weight: 950;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 14px;
  box-shadow: inset 0 -2px 0 rgba(91, 80, 141, 0.08);
  line-height: 1;
  user-select: none;
}

.voice-hold-btn.recording {
  background: #ffe8e8;
  color: #ff4d4f;
  box-shadow: inset 0 -2px 0 rgba(255, 77, 79, 0.12);
}

.voice-hold-btn.recognizing {
  background: #fff7e9;
  color: #ff914d;
}

.voice-hold-icon {
  font-size: 18px;
  line-height: 1;
}

.send-btn {
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: #fff;
  box-shadow: 0 5px 0 #f16012;
}

.text-input {
  flex: 1;
  min-width: 0;
  height: 44px;
  border: 0;
  border-radius: 22px;
  background: #f7f4ff;
  color: #5b508d;
  font-size: 14px;
  font-weight: 850;
  padding: 0 14px;
}
.art-back-small { width: 52px; height: 52px; padding: 0; border: 0; background: transparent; }
.art-back-small image { width: 100%; height: 100%; }

/* 新版诗人对话底图布局，保留原有对话、语音和接口逻辑。 */
.chat-app { width: 1672px; height: 770px; flex: 0 0 auto; background: transparent; }
.chat-bg { position: absolute; inset: 0; width: 100%; height: 100%; }
.page { position: absolute; inset: 0; padding: 0; display: block; overflow: hidden; }
.topbar { position: absolute; inset: 0; height: auto; pointer-events: none; }
.topbar .back { left: 18px; top: 14px; width: 112px; height: 112px; pointer-events: auto; }
.topbar .title-pill { display: none; }
.next-btn { right: 28px; top: 26px; width: 178px; height: 70px; padding: 0; border: 0; background: transparent; box-shadow: none; color: transparent; pointer-events: auto; }
.next-btn.active { background: transparent; color: transparent; filter: brightness(1.05); }
.main-layout { position: absolute; inset: 0; display: block; }
.poet-stage { position: absolute; left: 164px; top: 78px; width: 485px; height: 610px; padding: 0; border-radius: 0; background: transparent; box-shadow: none; overflow: hidden; display: block; }
.poet-img-large { left: 100px; top: 82px; bottom: auto; width: 300px; height: 360px; border-radius: 0; background: transparent; object-fit: contain; }
.poet-name { left: 92px; right: 92px; top: 500px; height: 55px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 0; background: transparent; box-shadow: none; color: #704117; font-size: 34px; }
.left-poem-card { display: none; }
.dialog-panel { position: absolute; left: 670px; top: 116px; width: 850px; height: 600px; display: block; }
.chat-card { position: absolute; left: 0; top: 0; width: 100%; height: 480px; padding: 24px 30px; border-radius: 0; background: transparent; box-shadow: none; }
.bubble { font-size: 24px; line-height: 1.45; padding: 13px 18px; }
.mini-avatar { width: 54px; height: 54px; }
.suggest-box { margin: 12px 0 4px 62px; padding: 14px; }
.suggest-title { font-size: 23px; }
.chips { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.chip { min-width: 0; padding: 9px 10px; font-size: 19px; text-align: center; white-space: normal; }
.input-bar { position: absolute; left: 0; right: 0; bottom: 0; height: 92px; padding: 0; gap: 12px; }
.mode-btn { width: 92px; height: 92px; opacity: 0; }
.voice-hold-btn { height: 82px; border: 0; background: transparent; box-shadow: none; color: transparent; font-size: 25px; }
.voice-hold-btn.recording, .voice-hold-btn.recognizing { background: rgba(255,255,255,.45); color: #8b4b2a; }
.text-input { height: 72px; border-radius: 36px; background: rgba(255,255,255,.82); font-size: 25px; padding: 0 28px; }
.send-btn { width: 72px; height: 72px; font-size: 30px; }
.review-guide-mask { position: absolute; inset: 0; z-index: 120; display: flex; align-items: center; justify-content: center; background: rgba(58, 38, 20, .34); backdrop-filter: blur(8px); }
.review-guide-card { width: 760px; min-height: 390px; padding: 55px 70px 42px; border: 7px solid #a66a2d; border-radius: 20px; background: #fff0c8; box-shadow: 0 24px 60px rgba(58, 37, 17, .38); color: #704117; text-align: center; }
.review-guide-title { font-size: 46px; font-weight: 900; }
.review-guide-text { margin-top: 32px; font-size: 30px; font-weight: 800; line-height: 1.6; }
.review-guide-actions { margin-top: 36px; display: flex; justify-content: center; gap: 28px; }
.review-guide-btn { width: 250px; height: 72px; padding: 0; border: 3px solid #9f672c; border-radius: 8px; font-size: 29px; font-weight: 900; }
.review-guide-btn.primary { background: #d99a49; color: #fff8e7; box-shadow: 0 6px 0 #9f672c; }
.review-guide-btn.secondary { background: #fff9e8; color: #704117; box-shadow: 0 6px 0 #d3aa70; }
.review-guide-checkbox { margin-top: 32px; display: flex; align-items: center; justify-content: center; gap: 14px; font-size: 24px; font-weight: 800; }
.checkbox-box { width: 34px; height: 34px; border: 3px solid #9f672c; border-radius: 5px; display: flex; align-items: center; justify-content: center; background: #fff9e8; color: #fff; font-size: 26px; line-height: 1; }
.checkbox-box.checked { background: #a66a2d; }
</style>
