<template>
  <view class="page-root">
    <view class="parent-app">
      <view class="page">
        <view class="topbar">
          <view class="back" @tap.stop="goBack">‹</view>

          <view class="title-pill">
            <view class="logo">🌱</view>
            <text>家长端</text>
          </view>

          <view class="top-placeholder"></view>
        </view>

        <view class="content">
          <view class="left-panel">
            <view class="summary-card">
              <view>
                <view class="summary-title">今日学习<br />小朋友表现很棒</view>
                <view class="summary-sub">
                  已完成 {{ summary.learned_count }} 首古诗学习
                </view>
              </view>

              <view class="kid-icon">👧</view>
            </view>

            <view class="stats">
              <view class="stat-card">
                <view class="stat-label">已学古诗</view>
                <view class="stat-value">
                  {{ summary.learned_count }}
                  <text class="stat-unit">首</text>
                </view>
              </view>

              <view class="stat-card">
                <view class="stat-label">累计时长</view>
                <view class="stat-value duration-value">
                  {{ formatDuration(summary.total_duration_seconds) }}
                </view>
              </view>
            </view>

            <view class="manage-card">
              <view class="manage-row">
                <view>
                  <view class="manage-text">每日使用提醒</view>
                  <view class="manage-sub">
                    {{ reminderEnabled ? '已开启：建议每天不超过 20 分钟' : '已关闭：暂不提醒' }}
                  </view>
                </view>

                <view
                  class="switch"
                  :class="{ off: !reminderEnabled }"
                  @tap="toggleReminder"
                ></view>
              </view>
            </view>
          </view>

          <view class="right-panel">
            <view class="section-title">📚 最近学习记录</view>

            <scroll-view class="record-list" scroll-y>
              <view v-if="loading" class="empty-state">
                正在加载学习统计...
              </view>

              <view v-else-if="displayRecords.length === 0" class="empty-state">
                暂无学习记录，快去学习一首古诗吧～
              </view>

              <view
                v-else
                v-for="item in displayRecords"
                :key="item.key"
                class="record-item"
              >
                <view class="record-icon">{{ item.icon }}</view>

                <view class="record-main">
                  <view class="record-name">《{{ item.title }}》</view>
                  <view class="record-desc">{{ item.desc }}</view>
                </view>
				
				<view class="record-time">
				  {{ item.timeLabel }} : {{ item.timeValue }}
				</view>
              </view>
            </scroll-view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { API } from '@/utils/api.js'

const reminderEnabled = ref(true)
const loading = ref(false)

const summary = ref({
  learned_count: 0,
  record_count: 0,
  total_duration_seconds: 0,
  learned_poems: [],
  recent_records: []
})

const formatDuration = (seconds) => {
  const total = Number(seconds || 0)

  if (total < 60) {
    return `${total} 秒`
  }

  const minutes = Math.floor(total / 60)
  const restSeconds = total % 60

  if (minutes < 60) {
    return restSeconds > 0 ? `${minutes} 分 ${restSeconds} 秒` : `${minutes} 分`
  }

  const hours = Math.floor(minutes / 60)
  const restMinutes = minutes % 60

  return restMinutes > 0 ? `${hours} 小时 ${restMinutes} 分` : `${hours} 小时`
}

const formatDurationCompact = (seconds) => {
  return formatDuration(seconds).replace(/\s+/g, '')
}

const getPoemIcon = (poem) => {
  const title = poem?.title || ''
  const tags = poem?.tags || []
  const tagText = Array.isArray(tags) ? tags.join('') : String(tags)

  if (title.includes('春') || tagText.includes('春')) return '🌸'
  if (title.includes('鹅') || tagText.includes('动物')) return '🦢'
  if (title.includes('月') || tagText.includes('月') || tagText.includes('思乡')) return '🌙'
  if (title.includes('农') || tagText.includes('劳动')) return '🌾'
  if (title.includes('楼') || tagText.includes('登高')) return '🏯'
  if (title.includes('蜂')) return '🐝'

  return '📖'
}

const hasDurationField = (item = {}) => {
  return (
    item.total_duration_seconds !== undefined ||
    item.latest_duration_seconds !== undefined ||
    item.duration_seconds !== undefined ||
    item.total_duration !== undefined ||
    item.duration !== undefined
  )
}

const getLatestDurationSeconds = (item = {}) => {
  return Number(
    item.latest_duration_seconds ??
    item.duration_seconds ??
    item.duration ??
    0
  )
}

const getTotalDurationSeconds = (item = {}) => {
  return Number(
    item.total_duration_seconds ??
    item.total_duration ??
    item.duration_seconds ??
    item.duration ??
    item.latest_duration_seconds ??
    0
  )
}

const getRecordPoemId = (item = {}) => {
  return item.poem_id || item.id || item.poem?.id || item.matched_poem?.id || ''
}

const getRecordTitle = (item = {}, poemMap = {}) => {
  const poemId = getRecordPoemId(item)
  const poem = poemMap[poemId] || item.poem || item.matched_poem || {}

  return item.title || item.poem_title || poem.title || '未知古诗'
}

const buildPoemMap = (poems = []) => {
  return poems.reduce((map, poem) => {
    const key = poem.poem_id || poem.id

    if (key) {
      map[key] = poem
    }

    return map
  }, {})
}

const shouldDisplayRecord = (item = {}) => {
  // 有时后端旧数据没有 duration 字段，这种情况下不误删；
  // 明确带有 duration 且为 0 秒的记录才隐藏。
  if (!hasDurationField(item)) return true

  return getTotalDurationSeconds(item) > 0 || getLatestDurationSeconds(item) > 0
}

const getSummaryPayload = (res = {}) => {
  if (res.data && typeof res.data === 'object' && !Array.isArray(res.data)) {
    return res.data
  }

  return res
}

const displayRecords = computed(() => {
  return summary.value.learned_poems
    .filter(shouldDisplayRecord)
    .map((poem, index) => {
      const latestDuration = getLatestDurationSeconds(poem)
      const totalDuration = getTotalDurationSeconds(poem)

      return {
        key: poem.poem_id || poem.id || poem.title || index,
        icon: getPoemIcon(poem),
        title: poem.title || poem.poem_title || '未知古诗',
        desc: `最新学习时长：${formatDuration(latestDuration || totalDuration)}`,
        timeLabel: '总计',
        timeValue: formatDurationCompact(totalDuration || latestDuration)
      }
    })
})

const loadRecordSummary = async () => {
  loading.value = true

  try {
    const res = await API.getRecordSummary()

    if (res && res.success) {
      const payload = getSummaryPayload(res)
      const rawLearnedPoems = Array.isArray(payload.learned_poems)
        ? payload.learned_poems
        : Array.isArray(payload.poems)
          ? payload.poems
          : []

      const rawRecentRecords = Array.isArray(payload.recent_records)
        ? payload.recent_records
        : []

      const hasLearnedDurationInfo = rawLearnedPoems.some(hasDurationField)
      const hasRecentDurationInfo = rawRecentRecords.some(hasDurationField)
      const learnedPoems = rawLearnedPoems.filter(shouldDisplayRecord)
      const recentRecords = rawRecentRecords.filter(shouldDisplayRecord)
      const totalDurationSeconds = hasLearnedDurationInfo
        ? learnedPoems.reduce((sum, poem) => sum + getTotalDurationSeconds(poem), 0)
        : hasRecentDurationInfo
          ? recentRecords.reduce((sum, record) => sum + getLatestDurationSeconds(record), 0)
          : Number(payload.total_duration_seconds || payload.total_duration || 0)

      summary.value = {
        learned_count: hasLearnedDurationInfo
          ? learnedPoems.length
          : Number(payload.learned_count || payload.poem_count || learnedPoems.length || 0),
        record_count: hasRecentDurationInfo
          ? recentRecords.length
          : Number(payload.record_count || recentRecords.length || learnedPoems.length || 0),
        total_duration_seconds: Math.max(0, totalDurationSeconds),
        learned_poems: learnedPoems,
        recent_records: recentRecords
      }
    } else {
      uni.showToast({
        title: '学习统计获取失败',
        icon: 'none'
      })
    }
  } catch (err) {
    console.log('获取学习统计失败：', err)
    uni.showToast({
      title: '接口暂不可用',
      icon: 'none'
    })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRecordSummary()
})

const toggleReminder = () => {
  reminderEnabled.value = !reminderEnabled.value

  uni.showToast({
    title: reminderEnabled.value ? '已开启提醒' : '已关闭提醒',
    icon: 'none'
  })
}

const goBack = () => {
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []

  if (pages.length > 1) {
    uni.navigateBack({
      delta: 1,
      fail: () => {
        uni.reLaunch({
          url: '/pages/index/index'
        })
      }
    })
    return
  }

  uni.reLaunch({
    url: '/pages/index/index',
    fail: () => {
      if (typeof window !== 'undefined') {
        window.location.replace('#/pages/index/index')
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
  color: #5b508d;
}

.parent-app {
  position: relative;
  width: 844px;
  height: 390px;
  max-width: 100vw;
  max-height: 100vh;
  overflow: hidden;
  border-radius: 0;
  background:
    radial-gradient(circle at 8% 6%, rgba(255, 225, 105, 0.24), transparent 24%),
    radial-gradient(circle at 92% 18%, rgba(255, 221, 150, 0.18), transparent 24%),
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
  color: #ffffff;
  font-size: 18px;
}

.top-placeholder {
  width: 36px;
}

.content {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 16px;
}

.left-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: 122px 82px minmax(0, 1fr);
  gap: 10px;
}

.summary-card {
  border-radius: 30px;
  padding: 16px;
  background: linear-gradient(135deg, #b9f1e6 0%, #fff8dc 100%);
  box-shadow: 0 12px 22px rgba(104, 80, 52, 0.12);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-title {
  font-size: 23px;
  font-weight: 950;
  color: #5b508d;
  line-height: 1.25;
}

.summary-sub {
  margin-top: 7px;
  font-size: 13px;
  font-weight: 850;
  color: #ff914d;
}

.kid-icon {
  width: 76px;
  height: 76px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.9);
  display: grid;
  place-items: center;
  font-size: 40px;
  box-shadow: 0 8px 16px rgba(104, 80, 52, 0.1);
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-card {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 18px rgba(74, 55, 42, 0.1);
  padding: 13px;
}

.stat-label {
  font-size: 13px;
  font-weight: 900;
  color: #8a80ae;
}

.stat-value {
  margin-top: 7px;
  font-size: 28px;
  font-weight: 950;
  color: #5b508d;
  line-height: 1;
}

.duration-value {
  font-size: 21px;
  line-height: 1.15;
}

.stat-unit {
  font-size: 13px;
  color: #ff914d;
  margin-left: 3px;
}

.manage-card {
  min-height: 0;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 10px 18px rgba(74, 55, 42, 0.1);
  padding: 15px;
  display: grid;
  align-content: center;
}

.manage-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.manage-text {
  font-size: 18px;
  font-weight: 950;
  color: #5b508d;
}

.manage-sub {
  margin-top: 5px;
  font-size: 12px;
  font-weight: 800;
  color: #9a90c0;
  line-height: 1.4;
}

.switch {
  width: 64px;
  height: 36px;
  border-radius: 99px;
  background: #ff9a58;
  position: relative;
  box-shadow: inset 0 -4px 0 rgba(230, 93, 24, 0.35);
  flex-shrink: 0;
}

.switch::after {
  content: "";
  position: absolute;
  right: 5px;
  top: 5px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.18);
}

.switch.off {
  background: #d9d3e8;
  box-shadow: inset 0 -4px 0 rgba(120, 108, 164, 0.25);
}

.switch.off::after {
  right: auto;
  left: 5px;
}

.right-panel {
  min-height: 0;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 13px 24px rgba(74, 55, 42, 0.12);
  padding: 14px;
  display: grid;
  grid-template-rows: 34px minmax(0, 1fr);
  gap: 8px;
  overflow: hidden;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 22px;
  font-weight: 950;
  color: #5b508d;
}

.record-list {
  height: 100%;
  min-height: 0;
}

.record-item {
  min-height: 68px;
  border-radius: 24px;
  background: #fff8ee;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) 112px;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.record-icon {
  width: 48px;
  height: 48px;
  border-radius: 18px;
  background: #eafff9;
  display: grid;
  place-items: center;
  font-size: 24px;
}

.record-main {
  min-width: 0;
}

.record-name {
  font-size: 18px;
  font-weight: 950;
  color: #5b508d;
}

.record-desc {
  margin-top: 4px;
  font-size: 13px;
  font-weight: 800;
  color: #9a90c0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-time {
  justify-self: end;
  width: auto;
  min-width: 100px;
  height: 40px;
  padding: 0 14px;
  border-radius: 20px;
  background: #fff0dc;
  color: #ff914d;
  font-weight: 950;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.record-time-label {
  font-size: 13px;
}

.record-time-value {
  margin-top: 2px;
  font-size: 15px;
}

.empty-state {
  height: 100%;
  min-height: 170px;
  border-radius: 24px;
  background: #fff8ee;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9a90c0;
  font-size: 16px;
  font-weight: 850;
  text-align: center;
  padding: 20px;
}
</style>