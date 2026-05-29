<template>
  <view class="page-root">
    <view class="video-app">
      <view class="topbar">
        <button class="back-btn" @tap="goBack">‹</button>

        <view class="title-pill">
          正在播放：{{ poemData.title }}
        </view>

        <button class="done-btn" @tap="showGuide = true">
          播完了 ✓
        </button>
      </view>

      <view class="video-stage">
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
      </view>

      <view class="subtitle-box">
        <view class="subtitle-text">
          <text class="active-text">{{ poemData.content[0] }}</text>
          <text>，{{ poemData.content[1] }}。</text>
        </view>

        <view class="progress-track">
          <view class="progress-bar"></view>
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
              <button class="guide-btn white-btn" @tap="replayAudio">再看一遍</button>
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
import { onLoad } from '@dcloudio/uni-app'
import { API, getLocalPoemById } from '@/utils/api.js'

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'

const showGuide = ref(false)
const poemId = ref('poem_001')
const poemData = ref(getLocalPoemById('poem_001'))

const ttsLoading = ref(false)
const audioContext = ref(null)
const lastAudioUrl = ref('')

const sceneText = computed(() => {
  if (poemData.value.title === '春晓') return '春天的早晨，睡得香香的。'
  if (poemData.value.title === '静夜思') return '夜晚月光亮亮的，想起远方的家。'
  if (poemData.value.title === '咏鹅') return '白鹅在水里快乐地游来游去。'
  if (poemData.value.title === '悯农') return '每一粒米饭都来得很辛苦。'
  return '一起走进古诗里的画面吧。'
})

const poemText = computed(() => {
  const title = poemData.value.title || ''
  const author = poemData.value.author || ''
  const content = poemData.value.content || []

  return `${title}，${author}。${content.join('，')}。`
})

onLoad(async (options) => {
  poemId.value = options.poem_id || 'poem_001'
  poemData.value = getLocalPoemById(poemId.value)

  try {
    const detailRes = await API.getPoemDetail(poemId.value)

    if (detailRes && detailRes.success && detailRes.data) {
      poemData.value = detailRes.data
    }
  } catch (err) {
    console.log('古诗详情接口暂不可用，使用本地数据', err)
  }

  try {
    await API.addRecord(poemId.value, 0)
  } catch (err) {
    console.log('学习记录接口暂不可用，先跳过', err)
  }

  setTimeout(() => {
    playPoemAudio()
  }, 500)
})

const requestTTS = (text, voice = 'child') => {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BACKEND_BASE_URL}/tts`,
      method: 'POST',
      data: {
        text,
        voice
      },
      header: {
        'Content-Type': 'application/json'
      },
      timeout: 60000,
      success: (res) => {
        resolve(res.data)
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

const playByUrl = (audioUrl) => {
  if (audioContext.value) {
    audioContext.value.stop()
    audioContext.value.destroy()
  }

  const innerAudioContext = uni.createInnerAudioContext()
  audioContext.value = innerAudioContext

  innerAudioContext.src = audioUrl
  innerAudioContext.autoplay = true

  innerAudioContext.onPlay(() => {
    console.log('开始播放古诗朗读')
  })

  innerAudioContext.onEnded(() => {
    console.log('古诗朗读播放结束')
  })

  innerAudioContext.onError((err) => {
    console.log('音频播放失败：', err)
  })
}

const playPoemAudio = async () => {
  if (ttsLoading.value) return

  ttsLoading.value = true

  try {
    const data = await requestTTS(poemText.value, 'child')

    if (data && data.success && data.audio_url) {
      const audioUrl = `${BACKEND_BASE_URL}${data.audio_url}`
      lastAudioUrl.value = audioUrl
      playByUrl(audioUrl)
    } else {
      console.log('朗读生成失败：', data)
    }
  } catch (err) {
    console.log('TTS 接口调用失败：', err)
  } finally {
    ttsLoading.value = false
  }
}

const replayAudio = () => {
  showGuide.value = false

  if (lastAudioUrl.value) {
    playByUrl(lastAudioUrl.value)
  } else {
    playPoemAudio()
  }
}

const goBack = () => {
  if (audioContext.value) {
    audioContext.value.stop()
    audioContext.value.destroy()
  }

  uni.navigateBack({
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = '#/pages/index/index'
      }
    }
  })
}

const goChat = () => {
  if (audioContext.value) {
    audioContext.value.stop()
    audioContext.value.destroy()
  }

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
  padding: 10px 24px;
  border-radius: 24px;
  text-align: center;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
  border: 2px solid #fff;
  z-index: 30;
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
  background: #ff8e53;
  border-radius: 999px;
  animation: progressMove 4s ease-in-out infinite;
}

@keyframes progressMove {
  0% {
    width: 10%;
  }

  50% {
    width: 80%;
  }

  100% {
    width: 36%;
  }
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