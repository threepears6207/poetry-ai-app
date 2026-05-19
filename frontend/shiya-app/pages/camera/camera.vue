<template>
  <view class="page-root">
    <view class="camera-app">
      <view v-if="pageState === 'camera'" class="camera-page">
        <view class="camera-header">
          <button class="camera-back" @tap="goBack">‹</button>

          <view class="camera-title-pill">
            <view class="camera-logo">🌱</view>
            <text>拍照识别</text>
          </view>

          <view class="camera-tip">诗芽可以识别古诗，也能为风景匹配古诗哦！</view>
        </view>

        <view class="camera-shell">
          <view class="camera-card">
            <view class="corner c1"></view>
            <view class="corner c2"></view>
            <view class="corner c3"></view>
            <view class="corner c4"></view>

            <view class="poem-paper">
              <view class="poem-paper-title">{{ matchedPoem.title }}</view>
              <text class="poem-paper-line">春眠不觉晓</text>
              <text class="poem-paper-line">处处闻啼鸟</text>
              <text class="poem-paper-line">夜来风雨声</text>
              <text class="poem-paper-line">花落知多少</text>
            </view>

            <view class="scan-line"></view>
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
          <button class="side-btn" @tap="toast('演示模式：暂不切换摄像头')">
            <text class="side-icon">🔄</text>
            <text>反转</text>
          </button>

          <button class="shoot-btn" @tap="showResult">
            <text class="shoot-icon">📷</text>
            <text>拍摄</text>
          </button>

          <button class="side-btn" @tap="showResult">
            <text class="side-icon">🖼️</text>
            <text>相册</text>
          </button>
        </view>
      </view>

      <view v-if="pageState === 'result'" class="camera-page result-page">
        <view class="camera-header">
          <button class="camera-back" @tap="pageState = 'camera'">‹</button>

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
                <text>春眠不觉晓</text>
                <text>处处闻啼鸟</text>
                <text>夜来风雨声</text>
                <text>花落知多少</text>
              </view>
            </view>

            <view class="tag-panel">
              <view class="tag">🌸 春天</view>
              <view class="tag">🐦 鸟儿</view>
              <view class="tag">🌙 清晨</view>
            </view>
          </view>

          <view class="result-meta">
            <view class="mascot">👧</view>
          </view>

          <view class="speech-area">
            <view class="speech-card">
              诗芽为你找到了最合适的古诗，要不要进入学习？<br />
              进入后可以听朗读、看诗意画面，还能和诗人聊聊这首诗。
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
import { ref } from 'vue'

const pageState = ref('camera')
const mode = ref('poem')

const matchedPoem = ref({
  id: 'poem_001',
  title: '春晓',
  author: '孟浩然',
  dynasty: '唐'
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

const showResult = () => {
  uni.showLoading({
    title: '识别中...'
  })

  setTimeout(() => {
    uni.hideLoading()
    pageState.value = 'result'
  }, 600)
}

const goStudy = () => {
  uni.navigateTo({
    url: `/pages/study/study?poem_id=${matchedPoem.value.id}`,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = `#/pages/study/study?poem_id=${matchedPoem.value.id}`
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
</style>
