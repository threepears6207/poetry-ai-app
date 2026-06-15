<template>
  <view class="page-root">
    <view class="recommend-app" :style="appScaleStyle">
      <view class="page">
        <view class="topbar">
          <view class="back" @tap.stop="goHome">‹</view>

          <view class="title-pill">
            <view class="logo">🌱</view>
            <text>诗芽推荐</text>
          </view>

          <view class="top-placeholder"></view>
        </view>

        <view class="main-layout">
          <view class="left-panel">
            <view class="section-head">
              <view class="section-title">📖 继续学习下一首</view>

              <view class="filter-row">
                <view
                  v-for="item in filters"
                  :key="item.value"
                  class="filter-chip"
                  :class="{ active: activeFilter === item.value }"
                  @tap="activeFilter = item.value"
                >
                  {{ item.label }}
                </view>
              </view>
            </view>

            <scroll-view class="poem-list" scroll-y>
              <view
                v-for="poem in filteredPoems"
                :key="poem.id"
                class="poem-card"
                @tap="selectPoem(poem)"
              >
                <view class="poem-icon">{{ poem.icon || '📜' }}</view>

                <view class="poem-info">
                  <view class="poem-name-row">
                    <text class="poem-name">{{ poem.title }}</text>
                    <text v-if="poem.badge" class="badge">{{ poem.badge }}</text>
                  </view>

                  <view class="poem-author">{{ poem.dynasty }} · {{ poem.author }}</view>

                  <view class="poem-tags">
                    <text
                      v-for="tag in poem.tags"
                      :key="tag"
                      class="poem-tag"
                    >
                      {{ tag }}
                    </text>
                  </view>

                  <view v-if="poem.reason" class="reason-text">
                    {{ poem.reason }}
                  </view>
                </view>

                <view class="poem-arrow">›</view>
              </view>

              <view v-if="filteredPoems.length === 0" class="empty-box">
                暂时没有推荐，稍后再试试
              </view>
            </scroll-view>
          </view>

          <view class="right-panel">
            <view class="daily-card">
              <view class="daily-star">🌟</view>
              <view class="daily-title">每日一首</view>
              <view class="daily-text">
                今日推荐《悯农》<br />
                一起珍惜粮食吧！
              </view>

              <button class="daily-btn" @tap="goStudy('poem_004')">
                去看看
              </button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { API, LOCAL_POEMS } from '@/utils/api.js'

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

const currentPoemId = ref('poem_001')
const activeFilter = ref('all')
const recommendList = ref([])

const filters = [
  { label: '全部', value: 'all' },
  { label: '春天', value: 'spring' },
  { label: '动物', value: 'animal' },
  { label: '自然', value: 'nature' }
]

const categoryMap = {
  春天: 'spring',
  自然: 'nature',
  儿童启蒙: 'nature',
  动物: 'animal',
  月亮: 'nature',
  思乡: 'nature',
  劳动: 'nature',
  珍惜粮食: 'nature',
  登高: 'nature',
  黄河: 'nature',
  励志: 'nature'
}

const getPoemIcon = (title) => {
  if (title === '春晓') return '🌸'
  if (title === '静夜思') return '🌙'
  if (title === '咏鹅') return '🦢'
  if (title === '悯农') return '🌾'
  if (title === '登鹳雀楼') return '🏯'
  return '📜'
}

const getReason = (title) => {
  if (title === '静夜思') return '适合继续学习月亮和思乡主题'
  if (title === '咏鹅') return '内容简单，适合儿童启蒙'
  if (title === '悯农') return '可以学习珍惜粮食'
  if (title === '登鹳雀楼') return '适合学习登高望远的画面'
  return '适合作为下一首学习'
}

const buildLocalRecommend = () => {
  return LOCAL_POEMS
    .filter(item => item.id !== currentPoemId.value)
    .map(item => {
      const categories = item.tags
        .map(tag => categoryMap[tag])
        .filter(Boolean)

      return {
        ...item,
        icon: getPoemIcon(item.title),
        categories,
        badge: item.id === 'poem_002' ? '✨ 推荐' : '',
        reason: getReason(item.title)
      }
    })
}

onLoad(async (options) => {
  currentPoemId.value = options.poem_id || 'poem_001'
  recommendList.value = buildLocalRecommend()

  try {
    const res = await API.getRecommend(5)

    if (res && res.success && Array.isArray(res.data) && res.data.length > 0) {
      recommendList.value = res.data.map(item => {
        const local = LOCAL_POEMS.find(poem => poem.id === item.id || poem.id === item.poem_id)

        return {
          ...(local || item),
          id: item.id || item.poem_id || local?.id,
          title: item.title || local?.title,
          author: item.author || local?.author,
          dynasty: item.dynasty || local?.dynasty || '唐',
          tags: item.tags || local?.tags || [],
          icon: getPoemIcon(item.title || local?.title),
          categories: (item.tags || local?.tags || [])
            .map(tag => categoryMap[tag])
            .filter(Boolean),
          badge: item.badge || '✨ 推荐',
          reason: item.reason || getReason(item.title || local?.title)
        }
      })
    }
  } catch (err) {
    console.log('推荐接口暂不可用，使用本地推荐', err)
  }
})

const filteredPoems = computed(() => {
  if (activeFilter.value === 'all') return recommendList.value

  return recommendList.value.filter(poem => {
    return Array.isArray(poem.categories) && poem.categories.includes(activeFilter.value)
  })
})

const goHome = () => {
  uni.reLaunch({
    url: '/pages/index/index',
    success: () => {
      console.log('已返回主页')
    },
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.replace('#/pages/index/index')
      }
    }
  })
}

const goStudy = (poemId) => {
  uni.navigateTo({
    url: `/pages/study/study?poem_id=${poemId}`,
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.href = `#/pages/study/study?poem_id=${poemId}`
      }
    }
  })
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
  if (!poem.id) {
    uni.showToast({
      title: '这首诗缺少 poem_id',
      icon: 'none'
    })
    return
  }

  preloadPoemImage(poem.id)
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
  color: #5b508d;
}

.recommend-app {
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
  padding: 6px 16px 14px;
  display: grid;
  grid-template-rows: 50px minmax(0, 1fr);
  gap: 0;
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
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.86);
  color: #5b508d;
  font-size: 26px;
  line-height: 36px;
  text-align: center;
  box-shadow: 0 7px 16px rgba(112, 79, 54, 0.14);
  cursor: pointer;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.title-pill {
  position: absolute;
  left: 50%;
  top: -2px;
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
  font-size: 16px;
}

.top-placeholder {
  width: 36px;
}

.main-layout {
  height: calc(100% + 8px);
  min-height: 0;
  display: flex;
  gap: 16px;
  padding-top: 0;
  transform: translateY(-8px);
}

.left-panel {
  flex: 1.6;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.right-panel {
  flex: 0.9;
  min-width: 0;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 18px;
  font-weight: 900;
  color: #5b508d;
}

.filter-row {
  display: flex;
  gap: 6px;
}

.filter-chip {
  padding: 5px 14px;
  border-radius: 999px;
  border: 2px solid transparent;
  background: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  font-weight: 800;
  color: #9a90c0;
}

.filter-chip.active {
  background: #fff4e6;
  color: #ff914d;
  border-color: #ffb78c;
}

.poem-list {
  flex: 1;
  height: 100%;
  min-height: 0;
}

.poem-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 6px 14px rgba(74, 55, 42, 0.08);
  margin-bottom: 8px;
}

.poem-card:active {
  transform: scale(0.98);
}

.poem-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 26px;
  background: #fff8ee;
  flex-shrink: 0;
}

.poem-info {
  flex: 1;
  min-width: 0;
}

.poem-name-row {
  font-size: 16px;
  font-weight: 900;
  color: #5b508d;
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge {
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 10px;
  font-weight: 900;
  background: #fff4e6;
  color: #ff914d;
}

.poem-author {
  font-size: 11px;
  font-weight: 800;
  color: #9a90c0;
  margin-top: 2px;
}

.poem-tags {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.poem-tag {
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 9px;
  font-weight: 900;
  background: #ecfbff;
  color: #42a8c7;
}

.reason-text {
  margin-top: 4px;
  color: #ff914d;
  font-size: 11px;
  font-weight: 800;
}

.poem-arrow {
  color: #cbc3e8;
  font-size: 18px;
}

.empty-box {
  margin-top: 50px;
  text-align: center;
  color: #999999;
  font-size: 14px;
  font-weight: 800;
}

.daily-card {
  height: 100%;
  border-radius: 24px;
  background: linear-gradient(135deg, #fff8e7 0%, #fffdf5 100%);
  box-shadow: 0 8px 20px rgba(74, 55, 42, 0.1);
  padding: 16px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
}

.daily-star {
  font-size: 52px;
  animation: floatStar 3s ease-in-out infinite;
}

@keyframes floatStar {
  50% {
    transform: translateY(-10px);
  }
}

.daily-title {
  font-size: 19px;
  font-weight: 900;
  color: #5b508d;
}

.daily-text {
  font-size: 13px;
  font-weight: 800;
  color: #9a90c0;
  line-height: 1.5;
}

.daily-btn {
  padding: 10px 24px;
  border-radius: 99px;
  border: 0;
  background: linear-gradient(180deg, #ffac68, #ff7d32);
  color: #fff;
  font-size: 14px;
  font-weight: 900;
  box-shadow: 0 5px 0 #f16012, 0 8px 16px rgba(236, 98, 34, 0.2);
}
</style>
