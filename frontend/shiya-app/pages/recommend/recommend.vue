<template>
  <view class="page-root">
    <view class="search-page" :style="scaleStyle">
      <image class="page-bg" src="/static/final-ui/search-page.png" mode="scaleToFill" />
      <button class="back-hotspot art-back" @tap="goHome" aria-label="返回"><image src="/static/final-ui/nav-back.png" mode="aspectFit" /></button>
      <view class="page-title" @tap.stop="speakText('找古诗')">找古诗</view>

      <button class="search-trigger" @tap="openSearchDialog" aria-label="打开搜索">
        <text>诗名、作者或主题</text>
      </button>

      <view class="filter-row">
        <view v-for="item in filters" :key="item.value" :class="{ active: activeFilter === item.value }" @tap="selectFilter(item.value)">{{ item.label }}</view>
      </view>

      <view v-if="loading" class="message">正在翻阅诗卷……</view>
      <view v-else-if="visiblePoems.length === 0" class="message">没有找到相关古诗，换个词试试吧</view>
      <view v-else class="poem-grid">
        <view v-for="poem in visiblePoems" :key="poem.id" class="poem-card">
          <image src="/static/final-ui/poem-card-transparent.png" mode="scaleToFill" />
          <view class="poem-content">
            <view class="poem-title" :class="{ 'long-title': isLongPoemTitle(poem.title), 'extra-long-title': isExtraLongPoemTitle(poem.title) }" @tap.stop="speakText(poem.title)">{{ poem.title }}</view>
            <view class="poem-author" @tap.stop="speakPoemAuthor(poem)">{{ poem.dynasty }} · {{ poem.author }}</view>
            <scroll-view class="poem-lines" scroll-y :show-scrollbar="false">
              <text v-for="line in poemLines(poem)" :key="line" @tap.stop="speakText(line)">{{ line }}</text>
            </scroll-view>

            <view class="poem-open" @tap.stop="selectPoem(poem)">打开画卷</view>
          </view>
        </view>
      </view>

      <button class="page-arrow left" @tap="goPrevPage"><image src="/static/final-ui/nav-left.png" mode="aspectFit" /></button>
      <button class="page-arrow right" @tap="goNextPage"><image src="/static/final-ui/nav-right.png" mode="aspectFit" /></button>
      <view class="result-count">共找到 {{ filteredPoems.length }} 首</view>

      <view v-if="showSearchDialog" class="search-dialog-mask" @tap="showSearchDialog = false">
        <view class="search-dialog" @tap.stop>
          <button class="dialog-close" @tap="showSearchDialog = false">×</button>
          <view class="dialog-title" @tap.stop="speakText('搜索结果')">搜索结果</view>
          <view class="dialog-search-row">
            <input v-model="keyword" placeholder="输入诗名、诗人或主题" confirm-type="search" @confirm="doSearch" />
            <button @tap="doSearch">搜索</button>
          </view>
          <view v-if="loading" class="dialog-message">正在翻阅诗卷……</view>
          <view v-else-if="!searchResults.length" class="dialog-message">输入诗名、作者或主题后点击搜索</view>
          <scroll-view v-else class="dialog-results" scroll-y>
            <view v-for="poem in searchResults" :key="'search-' + poem.id" class="dialog-poem">
              <view class="dialog-poem-title" @tap.stop="speakText(poem.title)">{{ poem.title }}</view>
              <view class="dialog-poem-author" @tap.stop="speakPoemAuthor(poem)">{{ poem.dynasty }} · {{ poem.author }}</view>
              <view class="dialog-poem-preview" @tap.stop="speakText(poem.content_preview || poemLines(poem).join('，'))">{{ poem.content_preview || poemLines(poem).join('，') }}</view>
              <view class="dialog-poem-open" @tap.stop="selectPoem(poem)">打开画卷</view>
            </view>
          </scroll-view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { API, LOCAL_POEMS, searchLocalPoems } from '@/utils/api.js'
import { speakText } from '@/utils/speech.js'

const DESIGN_WIDTH = 1672
const DESIGN_HEIGHT = 770
const scale = ref(1)
const keyword = ref('')
const loading = ref(false)
const showSearchDialog = ref(false)
const searchResults = ref([])
const activeFilter = ref('all')
const pageIndex = ref(0)
const results = ref([...LOCAL_POEMS])
const scaleStyle = computed(() => `transform: scale(${scale.value});`)
const filters = [
  { label: '全部', value: 'all' },
  { label: '春日', value: '春' },
  { label: '月夜', value: '月' },
  { label: '山水', value: '山' },
  { label: '动物', value: '动物' }
]
const isLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 4
const isExtraLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 6

const updateScale = () => {
  try {
    const info = uni.getSystemInfoSync()
    scale.value = Number(Math.min((info.windowWidth || DESIGN_WIDTH) / DESIGN_WIDTH, (info.windowHeight || DESIGN_HEIGHT) / DESIGN_HEIGHT).toFixed(4)) || 1
  } catch (err) { scale.value = 1 }
}

const poemSearchText = (poem) => `${poem.title || ''}${poem.author || ''}${(poem.tags || []).join('')}${(poem.content || []).join('')}`
const speakPoemAuthor = (poem) => {
  const dynasty = String(poem?.dynasty || '').trim()
  const author = String(poem?.author || '').trim()
  speakText(`${dynasty}${dynasty && !dynasty.endsWith('代') ? '代' : ''}${dynasty && author ? '，' : ''}${author}`)
}
const filteredPoems = computed(() => {
  if (activeFilter.value === 'all') return results.value
  if (activeFilter.value === '动物') return results.value.filter(item => /鹅|鸟|动物|鱼|蜂|蝉/.test(poemSearchText(item)))
  return results.value.filter(item => poemSearchText(item).includes(activeFilter.value))
})
const maxPage = computed(() => Math.max(0, Math.ceil(filteredPoems.value.length / 4) - 1))
const visiblePoems = computed(() => filteredPoems.value.slice(pageIndex.value * 4, pageIndex.value * 4 + 4))
const poemLines = (poem) => {
  if (Array.isArray(poem.content)) return poem.content.filter(Boolean)
  return String(poem.content || poem.content_preview || '').split(/[，。\n]/).filter(Boolean)
}
const selectFilter = (value) => {
  activeFilter.value = value
  pageIndex.value = 0
}

const openSearchDialog = () => {
  showSearchDialog.value = true
  searchResults.value = []
}

const goPrevPage = () => {
  pageIndex.value = pageIndex.value > 0 ? pageIndex.value - 1 : maxPage.value
}

const goNextPage = () => {
  pageIndex.value = pageIndex.value < maxPage.value ? pageIndex.value + 1 : 0
}

const doSearch = async () => {
  const value = keyword.value.trim()
  showSearchDialog.value = true
  loading.value = true
  pageIndex.value = 0
  activeFilter.value = 'all'
  try {
    const response = await API.searchPoems(value)
    if (response?.success && Array.isArray(response.data)) searchResults.value = response.data
    else searchResults.value = searchLocalPoems(value)
  } catch (err) {
    searchResults.value = searchLocalPoems(value)
  } finally {
    loading.value = false
  }
}

const goHome = () => uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/index/index' }) })
const selectPoem = (poem) => {
  if (!poem?.id) return
  speakText(poem.title)
  API.getPoemDetail(poem.id).then(res => {
    if (res?.success && res.data) API.preloadGenerateImage(res.data)
  }).catch(() => {})
  uni.navigateTo({ url: `/pages/study/study?poem_id=${poem.id}` })
}

const resize = () => updateScale()
const loadRecommendations = async () => {
  loading.value = true
  try {
    const response = await API.getRecommend(20, '', uni.getStorageSync('shiYaChildAgeText') || '4岁')
    if (response?.success && Array.isArray(response.data) && response.data.length) {
      results.value = response.data
    }
  } catch (err) {
    console.log('加载推荐诗单失败，使用本地兜底：', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  updateScale()
  loadRecommendations()
  if (typeof uni.onWindowResize === 'function') uni.onWindowResize(resize)
})
onUnmounted(() => {
  if (typeof uni.offWindowResize === 'function') uni.offWindowResize(resize)
})
</script>

<style scoped>
* { box-sizing: border-box; }
button::after { border: 0; }
.page-root { width: 100vw; height: 100vh; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #172421; font-family: "ShiyaZhenKai", "STKaiti", "KaiTi", serif; font-synthesis: none; }
.search-page { position: relative; width: 1672px; height: 770px; flex: 0 0 auto; transform-origin: center; overflow: hidden; }
.page-bg { position: absolute; inset: 0; width: 100%; height: 100%; }
.back-hotspot { position: absolute; left: 24px; top: 14px; }
.art-back { z-index: 70; width: 120px; height: 120px; padding: 0; border: 0; background: transparent; }
.art-back image, .page-arrow image { width: 100%; height: 100%; }
.page-title { position: absolute; left: 570px; top: 35px; width: 532px; height: 96px; display: flex; align-items: center; justify-content: center; color: #704117; font-size: 56px; font-weight: 900; letter-spacing: 14px; }
.search-trigger { position: absolute; right: 38px; top: 22px; width: 385px; height: 80px; padding: 0 24px 0 76px; border: 0; background: transparent; color: #8a7764; font: 700 27px/80px "PingFang SC", sans-serif; text-align: left; }
.filter-row { position: absolute; left: 250px; right: 250px; top: 145px; display: flex; justify-content: center; gap: 20px; }
.filter-row view { min-width: 100px; height: 42px; padding: 0 18px; display: flex; align-items: center; justify-content: center; color: #85562b; font-size: 21px; font-weight: 900; }
.filter-row view.active { color: #65390f; border-bottom: 4px solid #b8792e; }
.poem-grid { position: absolute; left: 208px; top: 210px; width: 1256px; height: 620px; display: flex; justify-content: center; gap: 42px; }
.poem-card { position: relative; width: 272px; height: 476px; overflow: hidden; transition: transform .16s; }
.poem-card:active { transform: translateY(7px) scale(.97); }
.poem-card > image { position: absolute; left: -20px; top: -8px; width: 312px; height: 509px; filter: drop-shadow(0 8px 8px rgba(70, 43, 18, .18)); }
.poem-content { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; color: #6f411b; }
.poem-title { position: absolute; left: 28px; right: 28px; top: 9px; height: 70px; display: flex; align-items: center; justify-content: center; text-align: center; white-space: nowrap; font-size: 34px; font-weight: 900; letter-spacing: 5px; z-index: 5; }
.poem-title.long-title { font-size: 28px; letter-spacing: 1px; }
.poem-title.extra-long-title { left: 50%; right: auto; width: 6em; height: 82px; transform: translateX(-50%); align-content: center; white-space: normal; word-break: break-all; line-height: 1.12; font-size: 24px; letter-spacing: 0; }
.poem-author { position: absolute; left: 28px; right: 28px; top: 104px; text-align: center; font-size: 22px; font-weight: 800; color: #8d5c30; }
.poem-lines { position: absolute; left: 1px; right: 22px; top: 157px; height: 184px; overflow-y: auto; font-size: 23px; font-weight: 700; line-height: 1.25; }
.poem-lines text { display: block; width: 100%; text-align: center; white-space: nowrap; }
.poem-lines text + text { margin-top: 10px; }

.poem-open { position: absolute; left: 40px; right: 40px; top: 350px; height: 62px; display: flex; align-items: center; justify-content: center; color: #704117; font-size: 24px; font-weight: 900; }
.message { position: absolute; left: 380px; top: 420px; width: 912px; text-align: center; color: #82552d; font-size: 32px; font-weight: 900; }
.page-arrow { position: absolute; top: 395px; width: 96px; height: 96px; border: 0; background: transparent; padding: 0; }
.page-arrow.left { left: 102px; }
.page-arrow.right { right: 102px; }
.result-count { position: absolute; left: 720px; bottom: 30px; width: 235px; text-align: center; color: #573116; -webkit-text-stroke: 1px #fff1cf; paint-order: stroke fill; text-shadow: 0 1px 2px rgba(255, 241, 207, .9); font-size: 22px; font-weight: 900; }
/* 手机横屏可读性 */
.page-title { font-size: 64px; }
.filter-row view { font-size: 30px; }
.poem-title { font-size: 40px; }
.poem-title.long-title { font-size: 32px; letter-spacing: 1px; }
.poem-title.extra-long-title { font-size: 27px; letter-spacing: 0; }
.poem-author { font-size: 27px; }
.poem-lines { font-size: 29px; gap: 10px; }
.poem-open { font-size: 32px; }
.result-count { font-size: 30px; }
.message { font-size: 40px; }
.search-dialog-mask { position: absolute; inset: 0; z-index: 80; display: flex; align-items: center; justify-content: center; background: rgba(55, 46, 30, .4); backdrop-filter: blur(6px); }
.search-dialog { position: relative; width: 1040px; height: 650px; padding: 188px 95px 55px; border: 8px solid #b77a32; border-radius: 24px; background: #fff0c8 url('/static/final-ui/page-title-plaque.png') center 18px / 520px 104px no-repeat; box-shadow: 0 22px 55px rgba(58, 37, 17, .35); }
.dialog-close { position: absolute; right: 28px; top: 25px; width: 64px; height: 64px; padding: 0; border: 4px solid #9f672c; border-radius: 50%; background: #f7ce7a; color: #704117; font-size: 48px; line-height: 52px; }
.dialog-title { position: absolute; left: 320px; right: 320px; top: 36px; text-align: center; color: #704117; font-size: 42px; font-weight: 900; }
.dialog-search-row { position: absolute; left: 90px; right: 90px; top: 112px; height: 62px; display: flex; gap: 14px; }
.dialog-search-row input { flex: 1; min-width: 0; height: 62px; padding: 0 24px; border: 3px solid #d5a45e; border-radius: 8px; background: rgba(255,250,226,.95); color: #704117; font-size: 27px; }
.dialog-search-row button { width: 140px; height: 62px; padding: 0; border: 3px solid #a96c2b; border-radius: 8px; background: #eab35f; color: #704117; font-size: 28px; font-weight: 900; }
.dialog-results { width: 100%; height: 100%; }
.dialog-poem { min-height: 108px; margin-bottom: 16px; padding: 18px 28px; border: 3px solid #d5a45e; border-radius: 8px; background: rgba(255, 250, 226, .88); color: #704117; }
.dialog-poem-title { font-size: 32px; font-weight: 900; }
.dialog-poem-author { margin-top: 5px; font-size: 23px; color: #926138; }
.dialog-poem-preview { margin-top: 8px; font-size: 24px; }
.dialog-poem-open { float: right; margin-top: 8px; color: #704117; font-size: 23px; font-weight: 900; }
.dialog-message { padding-top: 90px; text-align: center; color: #82552d; font-size: 34px; font-weight: 900; }
</style>
