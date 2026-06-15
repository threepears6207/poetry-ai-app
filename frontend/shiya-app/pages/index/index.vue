<template>
  <view class="page-root">
    <view class="app-container" @tap="showAgeList = false">
      <view class="cloud-bg">☁️</view>

      <view class="mountain-bg">
        <view class="mountain mountain-a"></view>
        <view class="mountain mountain-b"></view>
        <view class="mountain mountain-c"></view>
      </view>

      <view class="header">
        <view class="brand-pill">
          <view class="brand-icon">🌱</view>
          <text class="brand-title">诗芽小学堂</text>
        </view>

        <view class="age-area" @tap.stop>
          <button class="parent-btn" @tap="goPage('/pages/parent/parent')">家长端</button>

          <text class="age-label">选择你的年龄：</text>

          <view class="age-select" @tap.stop="showAgeList = !showAgeList">
            <text>{{ selectedAge }}</text>
            <text class="age-arrow">⌄</text>
          </view>

          <view v-if="showAgeList" class="age-dropdown">
            <view
              v-for="age in ageList"
              :key="age"
              class="age-option"
              :class="{ active: selectedAge === age }"
              @tap.stop="chooseAge(age)"
            >
              {{ age }}
            </view>
          </view>
        </view>
      </view>

      <view class="main-layout">
        <view class="left-panel">
          <view class="action-button camera-button" @tap="goPage('/pages/camera/camera')">
            <view class="action-icon-circle">
              <text class="action-icon">📷</text>
            </view>
            <text class="action-title">拍照识别</text>
          </view>

          <view class="action-button search-button" @tap="openSearch">
            <view class="action-icon-circle">
              <text class="action-icon">📜</text>
            </view>
            <text class="action-title">搜索古诗</text>
            <text class="mic-icon">🎙️</text>
          </view>
        </view>

        <view class="right-panel">
          <view class="today-card" @tap="goStudy('poem_001')">
            <view class="yellow-side-line"></view>

            <view class="today-left">
              <view class="today-tags">
                <view class="small-tag spring-tag">
                  <text class="tag-icon">☀️</text>
                  <text>春天</text>
                </view>

                <view class="small-tag bird-tag">
                  <text class="tag-icon">🐦</text>
                  <text>小鸟</text>
                </view>

                <text class="today-hint">今天学这个</text>
              </view>

              <view class="today-title-row">
                <text class="poem-title">春晓</text>
                <text class="poem-author">孟浩然</text>
              </view>
            </view>

            <view class="play-button">
              <text class="play-icon">▶</text>
            </view>
          </view>

          <view class="review-card" @tap="goPage('/pages/review/review')">
            <view class="review-header">
              <view class="review-title-row">
                <text class="review-title">巩固练习</text>
                <view class="review-arrow">
                  <text>›</text>
                </view>
              </view>

              <view class="review-count">
                <text>{{ reviewLearningCount }}首待巩固</text>
              </view>
            </view>

            <view class="review-list">
              <view
                v-for="poem in homeReviewPreview"
                :key="poem.key"
                class="review-poem-card"
                :class="poem.passed ? 'done-card' : 'pending-card'"
              >
                <view class="review-poem-icon-wrap">
                  <text class="review-poem-icon">{{ poem.icon }}</text>
                </view>

                <view class="review-poem-info">
                  <text class="review-poem-name">{{ poem.title }}</text>
                  <text
                    class="review-poem-status"
                    :class="poem.passed ? 'done-text' : 'pending-text'"
                  >
                    {{ poem.passed ? '已巩固' : '待巩固' }}
                  </text>
                </view>
              </view>

              <view v-if="homeReviewPoems.length > 2" class="more-card">
                <text>···</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="footer-decoration">
        <text>🌱</text>
        <text class="seedling-two">🌱</text>
      </view>

      <view v-if="showSearchPanel" class="search-mask" @tap="closeSearch">
        <view class="search-panel" @tap.stop>
          <view class="search-head">
            <view>
              <view class="search-title">搜索古诗</view>
              <view class="search-sub">输入诗名、作者、主题都可以</view>
            </view>

            <button class="search-close" @tap="closeSearch">×</button>
          </view>

          <view class="search-input-row">
            <input
              class="search-input"
              v-model="keyword"
              placeholder="例如：春、李白、月亮"
              confirm-type="search"
              @confirm="doSearch"
            />

            <button class="search-btn" @tap="doSearch">搜索</button>
          </view>

          <scroll-view class="search-results" scroll-y>
            <view
              v-for="item in searchResults"
              :key="item.id"
              class="search-item"
              @tap="selectPoem(item)"
            >
              <view class="search-poem-icon">📜</view>

              <view class="search-info">
                <view class="search-name-row">
                  <text class="search-name">{{ item.title }}</text>
                  <text class="search-author">{{ item.dynasty }} · {{ item.author }}</text>
                </view>

                <view class="search-preview">{{ item.content_preview }}</view>
              </view>

              <view class="search-arrow">›</view>
            </view>

            <view v-if="searchResults.length === 0" class="empty-result">
              没有找到相关古诗
            </view>
          </scroll-view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { API, LOCAL_POEMS, searchLocalPoems } from '@/utils/api.js'

const selectedAge = ref('4 岁')
const showAgeList = ref(false)
const ageList = ['3 岁', '4 岁', '5 岁', '6 岁', '7 岁']

const CHILD_AGE_TEXT_KEY = 'shiYaChildAgeText'
const CHILD_AGE_KEY = 'shiYaChildAge'

const getAgeNumber = (ageText) => {
  const match = String(ageText || '').match(/\d+/)
  return match ? Number(match[0]) : 4
}

const showSearchPanel = ref(false)
const keyword = ref('')
const searchResults = ref(searchLocalPoems(''))

const POEM_ICONS = ['🌸', '🌙', '🦢', '🌾', '🏯', '🌿', '🍃', '⭐']
const homeReviewPoems = ref([])

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

const normalizePassed = (payload, defaultValue = false) => {
  const value = payload?.data?.status ?? payload?.data?.passed ?? payload?.status ?? payload?.passed ?? payload?.mastered ?? payload?.completed ?? payload?.is_passed ?? payload

  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value > 0

  if (typeof value === 'string') {
    const lowerValue = value.toLowerCase()

    if (
      value.includes('已掌握') ||
      value.includes('已通过') ||
      value.includes('已巩固') ||
      value.includes('完成') ||
      lowerValue.includes('passed') ||
      lowerValue.includes('mastered') ||
      lowerValue.includes('completed') ||
      lowerValue.includes('done')
    ) {
      return true
    }
  }

  return defaultValue
}

const getLocalPoemByAnyId = (poemId = '') => {
  return LOCAL_POEMS.find(item => item.id === poemId || item.poem_id === poemId) || null
}

const normalizeHomeReviewPoem = (rawItem = {}, index = 0) => {
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

  const passed = normalizePassed(poem, false)

  return {
    key: poemId,
    poem_id: poemId,
    title: poem.title || poem.poem_title || poem.poemTitle || `古诗 ${index + 1}`,
    icon: poem.icon || POEM_ICONS[index % POEM_ICONS.length],
    passed
  }
}

const buildFallbackHomeReviewPoems = () => {
  return LOCAL_POEMS.slice(0, 3).map((poem, index) => normalizeHomeReviewPoem(poem, index))
}

const homeReviewPreview = computed(() => homeReviewPoems.value.slice(0, 2))

const reviewLearningCount = computed(() => {
  return homeReviewPoems.value.filter(item => !item.passed).length
})

const loadHomeReviewPoems = async () => {
  homeReviewPoems.value = buildFallbackHomeReviewPoems()

  try {
    const res = await API.getConsolidationList()
    const list = extractArrayPayload(res)

    if (list.length) {
      homeReviewPoems.value = list.map((item, index) => normalizeHomeReviewPoem(item, index))
    }
  } catch (err) {
    console.log('首页巩固列表接口暂不可用，使用本地数据', err)
  }
}

onMounted(() => {
  const savedAge = uni.getStorageSync(CHILD_AGE_TEXT_KEY)

  if (savedAge && ageList.includes(savedAge)) {
    selectedAge.value = savedAge
  }

  uni.setStorageSync(CHILD_AGE_TEXT_KEY, selectedAge.value)
  uni.setStorageSync(CHILD_AGE_KEY, getAgeNumber(selectedAge.value))

  loadHomeReviewPoems()
})


const chooseAge = (age) => {
  selectedAge.value = age
  showAgeList.value = false

  uni.setStorageSync(CHILD_AGE_TEXT_KEY, age)
  uni.setStorageSync(CHILD_AGE_KEY, getAgeNumber(age))

  uni.showToast({
    title: `已选择${age}`,
    icon: 'none'
  })
}

const goPage = (url) => {
  uni.navigateTo({
    url,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = `#${url}`
      }
    }
  })
}

const goStudy = (poemId) => {
  goPage(`/pages/study/study?poem_id=${poemId}`)
}

const openSearch = () => {
  showSearchPanel.value = true
  keyword.value = ''
  searchResults.value = searchLocalPoems('')
}

const closeSearch = () => {
  showSearchPanel.value = false
}

const doSearch = async () => {
  const kw = keyword.value.trim()

  try {
    const res = await API.searchPoems(kw)

    if (res && res.success && Array.isArray(res.data)) {
      searchResults.value = res.data
      return
    }
  } catch (err) {
    console.log('搜索接口暂不可用，使用本地数据', err)
  }

  searchResults.value = searchLocalPoems(kw)
}

const preloadPoemImage = async (poemId) => {
  try {
    const detailRes = await API.getPoemDetail(poemId)

    if (detailRes?.success && detailRes.data) {
      API.preloadGenerateImage(detailRes.data)
    }
  } catch (err) {
    console.log('预热配图失败，播放页会继续生成', err)
  }
}

const selectPoem = (poem) => {
  closeSearch()

  if (poem?.id) {
    preloadPoemImage(poem.id)
  }

  goStudy(poem.id)
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

.app-container {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: 100vw;
  max-height: 100vh;
  background: linear-gradient(135deg, #fff9f0 0%, #ffe4d6 100%);
  overflow: hidden;
  border-radius: 0;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
  padding: 14px 22px 14px;
  display: flex;
  flex-direction: column;
}

.cloud-bg {
  position: absolute;
  top: 42px;
  left: 240px;
  font-size: 52px;
  opacity: 0.15;
  animation: floatCloud 10s ease-in-out infinite;
  pointer-events: none;
}

@keyframes floatCloud {
  50% {
    transform: translateX(28px);
  }
}

.mountain-bg {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 120px;
  opacity: 0.05;
  pointer-events: none;
}

.mountain {
  position: absolute;
  bottom: 0;
  background: #5d4e8c;
  clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
}

.mountain-a {
  left: 0;
  width: 240px;
  height: 105px;
}

.mountain-b {
  left: 210px;
  width: 300px;
  height: 150px;
}

.mountain-c {
  right: 0;
  width: 330px;
  height: 125px;
}

.header {
  position: relative;
  height: 48px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 900;
}

.brand-pill {
  height: 40px;
  background: rgba(255, 255, 255, 0.8);
  padding: 7px 18px;
  border-radius: 999px;
  border: 2px solid #ffd93d;
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 26px;
  height: 26px;
  background: #ff8e53;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 13px;
}

.brand-title {
  font-size: 18px;
  font-weight: 900;
  color: #5d4e8c;
  letter-spacing: 1px;
}

.age-area {
  position: relative;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 10px;
}

.parent-btn {
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: #66cdaa;
  color: #ffffff;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 900;
  box-shadow: 0 5px 12px rgba(102, 205, 170, 0.24);
}

.age-label {
  font-size: 13px;
  color: #999999;
  font-weight: 800;
}

.age-select {
  height: 32px;
  min-width: 80px;
  padding: 0 12px 0 18px;
  border-radius: 999px;
  background: #ff6b6b;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 900;
  box-shadow: 0 5px 12px rgba(255, 107, 107, 0.24);
}

.age-arrow {
  font-size: 15px;
  margin-top: -4px;
}

.age-dropdown {
  position: absolute;
  right: 0;
  top: 40px;
  width: 96px;
  background: #ffffff;
  border-radius: 18px;
  padding: 6px;
  box-shadow: 0 10px 24px rgba(112, 79, 54, 0.18);
  z-index: 999;
}

.age-option {
  height: 34px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #5d4e8c;
  font-size: 14px;
  font-weight: 900;
}

.age-option.active {
  background: #ff6b6b;
  color: #ffffff;
}

.main-layout {
  flex: 1;
  min-height: 0;
  position: relative;
  z-index: 10;
  display: flex;
  gap: 18px;
}

.left-panel {
  width: 28%;
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.action-button {
  flex: 1;
  border-radius: 36px;
  border: 4px solid #ffffff;
  box-shadow:
    0 10px 15px -5px rgba(0, 0, 0, 0.1),
    inset 0 -6px 12px rgba(0, 0, 0, 0.05),
    inset 0 6px 12px rgba(255, 255, 255, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.action-button:active,
.today-card:active,
.review-card:active {
  transform: scale(0.96);
}

.camera-button {
  background: #ff8e53;
}

.search-button {
  background: #66cdaa;
  position: relative;
}

.action-icon-circle {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}

.action-icon {
  font-size: 24px;
}

.action-title {
  color: #ffffff;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 3px;
}

.mic-icon {
  position: absolute;
  right: 18px;
  bottom: 12px;
  color: rgba(255, 255, 255, 0.42);
  font-size: 14px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.today-card {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #ffffff;
  border-radius: 30px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  padding: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.yellow-side-line {
  position: absolute;
  left: 0;
  top: 0;
  width: 7px;
  height: 100%;
  background: rgba(255, 217, 61, 0.4);
}

.today-left {
  height: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.today-tags {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.small-tag {
  height: 26px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 800;
}

.spring-tag {
  background: #ecfdf5;
  color: #10b981;
  border-color: #d1fae5;
}

.bird-tag {
  background: #eff6ff;
  color: #38bdf8;
  border-color: #dbeafe;
}

.today-hint {
  margin-left: 6px;
  font-size: 15px;
  color: #999999;
  font-weight: 900;
  letter-spacing: 2px;
}

.today-title-row {
  display: flex;
  align-items: flex-end;
}

.poem-title {
  font-size: 50px;
  font-weight: 900;
  line-height: 1;
  color: #5d4e8c;
  letter-spacing: 2px;
}

.poem-author {
  font-size: 20px;
  font-weight: 900;
  color: #ff8e53;
  margin-left: 15px;
  margin-bottom: 3px;
}

.play-button {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff8e53, #e46c2c);
  border: 6px solid #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.play-icon {
  color: #ffffff;
  font-size: 30px;
  margin-left: 4px;
}

.review-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.62);
  border-radius: 30px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  padding: 15px;
  display: flex;
  flex-direction: column;
}

.review-header {
  height: 36px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.review-title-row {
  display: flex;
  align-items: center;
}

.review-title {
  font-size: 20px;
  font-weight: 900;
  color: #5d4e8c;
}

.review-arrow {
  margin-left: 10px;
  width: 26px;
  height: 26px;
  background: #ff8e53;
  color: #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.review-count {
  height: 24px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 142, 83, 0.1);
  color: rgba(255, 142, 83, 0.75);
  font-size: 10px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.review-list {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  overflow: hidden;
}

.review-poem-card {
  width: 176px;
  height: 100%;
  background: #ffffff;
  border-radius: 26px;
  padding: 11px;
  display: flex;
  align-items: center;
  gap: 13px;
  flex-shrink: 0;
}

.pending-card {
  border: 2px dashed rgba(255, 142, 83, 0.4);
}

.done-card {
  border: 2px solid rgba(102, 205, 170, 0.2);
}

.review-poem-icon-wrap {
  width: 58px;
  height: 58px;
  background: #fffbf4;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.review-poem-icon {
  font-size: 32px;
}

.review-poem-info {
  display: flex;
  flex-direction: column;
}

.review-poem-name {
  font-size: 17px;
  font-weight: 900;
  color: #5d4e8c;
}

.review-poem-status {
  font-size: 11px;
  font-weight: 900;
  margin-top: 5px;
}

.pending-text {
  color: #ff8e53;
}

.done-text {
  color: #66cdaa;
}

.more-card {
  width: 50px;
  height: 70%;
  background: rgba(255, 255, 255, 0.25);
  border: 2px dashed #dddddd;
  border-radius: 14px;
  color: #cccccc;
  font-size: 24px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.footer-decoration {
  height: 16px;
  margin-top: 7px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  opacity: 0.22;
  font-size: 12px;
}

.seedling-two {
  transform: rotate(12deg);
}

.search-mask {
  position: absolute;
  inset: 0;
  background: rgba(93, 78, 140, 0.22);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-panel {
  position: relative;
  width: 600px;
  height: 300px;
  background: #ffffff;
  border-radius: 30px;
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.22);
  padding: 22px;
  display: flex;
  flex-direction: column;
}

.search-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 50px;
}

.search-title {
  font-size: 24px;
  font-weight: 900;
  color: #5d4e8c;
}

.search-sub {
  margin-top: 4px;
  font-size: 13px;
  color: #999999;
  font-weight: 800;
}

.search-close {
  position: absolute;
  right: 18px;
  top: 18px;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  background: #f4f1ff;
  color: #5d4e8c;
  font-size: 24px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-input-row {
  margin-top: 16px;
  display: flex;
  gap: 10px;
}

.search-input {
  flex: 1;
  height: 42px;
  border-radius: 21px;
  background: #f7f4ff;
  color: #5d4e8c;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 800;
}

.search-btn {
  width: 90px;
  height: 42px;
  border: 0;
  border-radius: 999px;
  background: #ff8e53;
  color: #ffffff;
  font-size: 15px;
  font-weight: 900;
}

.search-results {
  flex: 1;
  margin-top: 14px;
  min-height: 0;
}

.search-item {
  height: 62px;
  border-radius: 18px;
  background: #fff8ee;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  margin-bottom: 8px;
}

.search-poem-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.search-info {
  flex: 1;
}

.search-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-name {
  font-size: 16px;
  color: #5d4e8c;
  font-weight: 900;
}

.search-author {
  font-size: 12px;
  color: #ff8e53;
  font-weight: 800;
}

.search-preview {
  margin-top: 4px;
  font-size: 12px;
  color: #777777;
  font-weight: 700;
}

.search-arrow {
  font-size: 24px;
  color: #cbc3e8;
}

.empty-result {
  text-align: center;
  color: #999999;
  font-size: 15px;
  font-weight: 800;
  margin-top: 40px;
}
</style>
