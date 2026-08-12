<template>
  <view class="page-root">
    <view class="catalog" :style="scaleStyle">
      <image class="catalog-bg" src="/static/final-ui/stamp-page.png" mode="scaleToFill" />
      <button class="back-hotspot art-back" @tap="goBack" aria-label="返回"><image src="/static/final-ui/nav-back.png" mode="aspectFit" /></button>
      <view class="page-title">集章墙</view>

      <view class="card-grid">
        <view v-for="poem in visiblePoems" :key="poem.id" class="poem-card" :class="{ locked: !poem.unlocked }" @tap="openPoem(poem)">
          <image class="card-bg" src="/static/final-ui/collection-card-replacement.png" mode="scaleToFill" />
          <view class="card-name" :class="{ 'long-title': isLongPoemTitle(poem.title), 'extra-long-title': isExtraLongPoemTitle(poem.title) }">{{ poem.title }}</view>
          <image class="card-scene" :src="poem.sceneImage" mode="aspectFill" />
          <view v-if="!poem.unlocked" class="lock-mark">尚未点亮</view>
          <view class="card-author">{{ poem.dynasty }} · {{ poem.author }}</view>
          <image v-if="poem.unlocked" class="card-flower" src="/static/final-ui/flower.png" mode="aspectFit" />
        </view>
      </view>

      <view class="collection-tip">去“练一练”巩固古诗，就能点亮诗卡并获得小红花哦！</view>

      <button class="page-arrow left" :disabled="pageIndex === 0" @tap="pageIndex--" aria-label="上一页"></button>
      <button class="page-arrow right" :disabled="pageIndex >= maxPage" @tap="pageIndex++" aria-label="下一页"></button>
      <view class="page-number">已点亮 {{ unlockedCount }} / {{ allPoems.length }} 首古诗　·　{{ pageIndex + 1 }} / {{ maxPage + 1 }}</view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { API, normalizeAssetUrl } from '@/utils/api.js'

const DESIGN_WIDTH = 1672
const DESIGN_HEIGHT = 770
const scale = ref(1)
const scaleStyle = computed(() => `transform: scale(${scale.value});`)
const completedIds = ref(new Set())
const catalogPoems = ref([])
const pageIndex = ref(0)
const PAGE_SIZE = 4
const isLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 4
const isExtraLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 6

const allPoems = computed(() => catalogPoems.value.map(poem => ({
  ...poem,
  sceneImage: normalizeAssetUrl(`/static/images/poems/${poem.id}/frame_0.jpg`),
  unlocked: completedIds.value.has(String(poem.id))
})))
const maxPage = computed(() => Math.max(0, Math.ceil(allPoems.value.length / PAGE_SIZE) - 1))
const visiblePoems = computed(() => allPoems.value.slice(pageIndex.value * PAGE_SIZE, pageIndex.value * PAGE_SIZE + PAGE_SIZE))
const unlockedCount = computed(() => allPoems.value.filter(item => item.unlocked).length)

const updateScale = () => {
  try {
    const info = uni.getSystemInfoSync()
    scale.value = Number(Math.min((info.windowWidth || DESIGN_WIDTH) / DESIGN_WIDTH, (info.windowHeight || DESIGN_HEIGHT) / DESIGN_HEIGHT).toFixed(4)) || 1
  } catch (err) { scale.value = 1 }
}

const extractList = (payload) => [
  payload,
  payload?.data,
  payload?.items,
  payload?.poems,
  payload?.records,
  payload?.results,
  payload?.data?.items,
  payload?.data?.poems,
  payload?.data?.records,
  payload?.data?.results
].find(Array.isArray) || []

const loadCollection = async () => {
  try {
    const result = await API.getCollectionWall()
    const poems = Array.isArray(result?.poems) ? result.poems : extractList(result)
    catalogPoems.value = poems.map(item => ({
      ...item,
      id: item.id || item.poem_id,
      poem_id: item.poem_id || item.id
    }))
    completedIds.value = new Set(
      poems
        .filter(item => item.collection_state === 'color')
        .map(item => String(item.poem_id || item.id || ''))
        .filter(Boolean)
    )
    pageIndex.value = Math.min(pageIndex.value, maxPage.value)
  } catch (err) {
    console.log('加载集章墙失败：', err)
    catalogPoems.value = []
    completedIds.value = new Set()
  }
}

const goBack = () => uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/index/index' }) })
const openPoem = (poem) => {
  if (!poem.unlocked) {
    uni.showToast({ title: '完成巩固后就能点亮', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/pages/study/study?poem_id=${poem.id}` })
}

const resize = () => updateScale()
onMounted(() => {
  updateScale()
  if (typeof uni.onWindowResize === 'function') uni.onWindowResize(resize)
})
onUnmounted(() => {
  if (typeof uni.offWindowResize === 'function') uni.offWindowResize(resize)
})
onShow(loadCollection)
</script>

<style scoped>
* { box-sizing: border-box; }
button::after { border: 0; }
.page-root { width: 100vw; height: 100vh; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #172421; font-family: "ShiyaZhenKai", "STKaiti", "KaiTi", serif; font-synthesis: none; }
.catalog { position: relative; width: 1672px; height: 770px; flex: 0 0 auto; transform-origin: center; overflow: hidden; }
.catalog-bg { position: absolute; inset: 0; width: 100%; height: 100%; }
.back-hotspot { position: absolute; left: 24px; top: 14px; }
.art-back { z-index: 70; width: 120px; height: 120px; padding: 0; border: 0; background: transparent; }
.art-back image { width: 100%; height: 100%; }
.page-title { position: absolute; left: 570px; top: 35px; width: 532px; height: 78px; display: flex; align-items: center; justify-content: center; color: #744319; font-size: 46px; font-weight: 900; letter-spacing: 14px; }
.card-grid { position: absolute; left: 246px; top: 230px; width: 1180px; height: 273px; display: flex; justify-content: center; align-items: flex-start; gap: 28px; }
.poem-card { position: relative; width: 270px; height: 273px; overflow: visible; transition: transform .16s; }
.poem-card:active { transform: translateY(6px) scale(.98); }
.poem-card.locked { filter: none; opacity: 1; }
.poem-card.locked .card-scene { filter: grayscale(1); opacity: .48; }
.card-bg { position: absolute; inset: 0; width: 270px; height: 273px; }
.card-name { position: absolute; left: 62px; right: 62px; top: 32px; height: 40px; display: flex; align-items: center; justify-content: center; color: #744319; font-size: 24px; font-weight: 900; }
.card-name.long-title { left: 42px; right: 42px; font-size: 20px; }
.card-name.extra-long-title { left: 34px; right: 34px; font-size: 17px; letter-spacing: 0; }
.card-scene { position: absolute; left: 42px; top: 82px; width: 186px; height: 105px; border: 3px solid rgba(133, 84, 42, .42); border-radius: 5px; background: #ead9b8; }
.lock-mark { position: absolute; left: 38px; right: 38px; top: 112px; height: 46px; display: flex; align-items: center; justify-content: center; text-align: center; color: #75471f; -webkit-text-stroke: 1px #fff1cf; paint-order: stroke fill; text-shadow: 0 1px 2px rgba(255, 241, 207, .95); font-size: 18px; font-weight: 900; z-index: 4; }
.card-author { position: absolute; left: 25px; width: 145px; bottom: 28px; height: 34px; display: flex; align-items: center; justify-content: center; color: #81572f; font-size: 18px; font-weight: 800; white-space: nowrap; }
.card-flower { position: absolute; right: 36px; bottom: 22px; width: 50px; height: 50px; z-index: 5; filter: drop-shadow(0 3px 3px rgba(112, 65, 23, .24)); }
.page-arrow {
  position: absolute;
  top: 352px;
  width: 96px;
  height: 96px;
  padding: 0;
  border: 0;
  outline: none;
  box-shadow: none;
  background: transparent;
  -webkit-tap-highlight-color: transparent;
}
.page-arrow::after,
.page-arrow:focus,
.page-arrow:active,
.page-arrow[disabled] {
  border: 0;
  outline: none;
  box-shadow: none;
  background: transparent;
}
.page-arrow.left { left: 78px; }
.page-arrow.right { right: 78px; }
.page-arrow[disabled] { opacity: .25; }
.collection-tip { position: absolute; left: 370px; top: 550px; width: 932px; text-align: center; color: #5f3518; -webkit-text-stroke: 1px #fff1cf; paint-order: stroke fill; text-shadow: 0 1px 2px rgba(255, 241, 207, .9); font-size: 24px; font-weight: 900; }
.page-number { position: absolute; left: 570px; bottom: 120px; width: 532px; height: 44px; display: flex; align-items: center; justify-content: center; text-align: center; color: #5f3518; -webkit-text-stroke: 1px #fff1cf; paint-order: stroke fill; text-shadow: 0 1px 2px rgba(255, 241, 207, .9); font-size: 22px; font-weight: 900; }
/* 手机横屏可读性 */
.page-title { font-size: 60px; }
.card-name { font-size: 30px; }
.card-name.long-title { font-size: 25px; }
.card-name.extra-long-title { font-size: 21px; letter-spacing: 0; }
.lock-mark { font-size: 28px; }
.card-author { font-size: 20px; }
.page-number { font-size: 30px; }
.collection-tip { font-size: 32px; }
</style>
