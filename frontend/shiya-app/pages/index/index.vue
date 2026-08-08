<template>
  <view class="page-root">
    <view class="town" :style="townScaleStyle" @tap="showAgeList = false">
      <image class="town-bg" src="/static/final-ui/town-bg.png" mode="scaleToFill" />

      <view class="brand" aria-label="诗芽小学堂">
        <image src="/static/final-ui/brand-logo.png" mode="widthFix" />
      </view>

      <view class="top-actions" @tap.stop>
        <view class="age-control" @tap="showAgeList = !showAgeList">
          <image src="/static/final-ui/age.png" mode="scaleToFill" />
          <text>{{ selectedAge }}</text>
        </view>
        <view class="parent-control" @tap="goPage('/pages/parent/parent')">
          <image src="/static/final-ui/parent.png" mode="scaleToFill" />
          <text>家长端</text>
        </view>
        <view v-if="showAgeList" class="age-menu">
          <view v-for="age in ageList" :key="age" :class="{ active: age === selectedAge }" @tap="chooseAge(age)">{{ age }}</view>
        </view>
      </view>

      <view class="town-entry camera-entry" :class="{ pressed: pressedEntry === 'camera' }" @tap="openCamera">
        <image src="/static/final-ui/town-camera.png" mode="scaleToFill" />
      </view>

      <view class="town-entry today-entry" :class="{ pressed: pressedEntry === 'today' }" @tap="openLottery">
        <image src="/static/final-ui/town-today.png" mode="scaleToFill" />
      </view>

      <view class="town-entry search-entry" :class="{ pressed: pressedEntry === 'search' }" @tap="openSearch">
        <image src="/static/final-ui/town-search.png" mode="scaleToFill" />
      </view>

      <view class="town-entry practice-entry" :class="{ pressed: pressedEntry === 'practice' }" @tap="openPractice">
        <image src="/static/final-ui/town-practice.png" mode="scaleToFill" />
      </view>

      <view class="town-entry stamps-entry" :class="{ pressed: pressedEntry === 'stamps' }" @tap="openStamps">
        <image src="/static/final-ui/town-stamps.png" mode="scaleToFill" />
      </view>

      <view v-if="showLottery" class="modal-mask" @tap="showLottery = false">
        <view class="lottery-modal" @tap.stop>
          <image src="/static/final-ui/lottery.png" mode="scaleToFill" />
          <button class="modal-close" @tap.stop="showLottery = false" aria-label="关闭"></button>
          <view class="lottery-copy">
            <text class="lottery-kicker">抽到啦！</text>
            <text class="lottery-title" :class="{ 'long-title': isLongPoemTitle(dailyPoem.title) }">{{ dailyPoem.title }}</text>
            <text class="lottery-author">{{ dailyPoem.dynasty }} · {{ dailyPoem.author }}</text>
            <text class="lottery-line">{{ dailyLine }}</text>
          </view>
          <view class="lottery-actions">
            <button class="scroll-button primary" @tap="goStudy">打开画卷</button>
            <button class="scroll-button secondary" @tap="drawAgain">再抽一次</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { API, LOCAL_POEMS } from '@/utils/api.js'

const DESIGN_WIDTH = 1672
const DESIGN_HEIGHT = 770
const townScale = ref(1)
const townScaleStyle = computed(() => `transform: scale(${townScale.value});`)

const updateScale = () => {
  try {
    const info = uni.getSystemInfoSync()
    const width = Number(info.windowWidth || info.screenWidth || DESIGN_WIDTH)
    const height = Number(info.windowHeight || info.screenHeight || DESIGN_HEIGHT)
    townScale.value = Number(Math.min(width / DESIGN_WIDTH, height / DESIGN_HEIGHT).toFixed(4)) || 1
  } catch (err) {
    townScale.value = 1
  }
}

const selectedAge = ref('4 岁')
const ageList = ['3 岁', '4 岁', '5 岁', '6 岁', '7 岁']
const showAgeList = ref(false)
const showLottery = ref(false)
const pressedEntry = ref('')
const dailyPoem = ref(LOCAL_POEMS[0])
const isLongPoemTitle = (title = '') => Array.from(String(title).replace(/\s/g, '')).length > 4
const dailyLine = computed(() => {
  const content = dailyPoem.value?.content
  if (!Array.isArray(content)) return String(content || '')
  // 先拿前两句拼接
  const twoSentence = content.slice(0, 2).join('，')
  // 单句超过5字 / 两句总长度过长，只显示第一句
  if (content[0].length > 5 || twoSentence.length > 12) {
    return content[0]
  }
  return twoSentence
})

const ageNumber = () => Number(String(selectedAge.value).match(/\d+/)?.[0] || 4)

const goPage = (url) => {
  uni.navigateTo({
    url,
    fail: () => {
      if (typeof window !== 'undefined') window.location.href = `#${url}`
    }
  })
}

const chooseAge = async (age) => {
  selectedAge.value = age
  showAgeList.value = false
  uni.setStorageSync('shiYaChildAgeText', age)
  uni.setStorageSync('shiYaChildAge', ageNumber())
  await loadDailyPoem()
}

const loadDailyPoem = async () => {
  try {
    const poem = await API.getDailyRecommendation(ageNumber())
    if (poem?.id) dailyPoem.value = poem
  } catch (err) {
    const index = (new Date().getDate() + ageNumber()) % LOCAL_POEMS.length
    dailyPoem.value = LOCAL_POEMS[index] || LOCAL_POEMS[0]
  }
}

const drawDailyPoem = async () => {
  await loadDailyPoem()
  showLottery.value = true
}

const activateEntry = (name, action) => {
  if (pressedEntry.value) return
  pressedEntry.value = name
  setTimeout(() => {
    pressedEntry.value = ''
    action()
  }, 150)
}

const openCamera = () => activateEntry('camera', () => goPage('/pages/camera/camera'))
const openLottery = () => activateEntry('today', drawDailyPoem)
const openSearch = () => activateEntry('search', () => goPage('/pages/recommend/recommend?mode=search'))
const openPractice = () => activateEntry('practice', () => goPage('/pages/review/review'))
const openStamps = () => activateEntry('stamps', () => goPage('/pages/collection/collection'))

const drawAgain = async () => {
  try {
    const poem = await API.getDailyRecommendation(ageNumber(), dailyPoem.value?.id || '')
    if (poem?.id) dailyPoem.value = poem
  } catch (err) {
    const currentIndex = Math.max(0, LOCAL_POEMS.findIndex(item => item.id === dailyPoem.value?.id))
    dailyPoem.value = LOCAL_POEMS[(currentIndex + 1) % LOCAL_POEMS.length]
  }
}

const goStudy = () => {
  if (!dailyPoem.value?.id) return
  showLottery.value = false
  goPage(`/pages/study/study?poem_id=${dailyPoem.value.id}`)
}

const handleResize = () => updateScale()

onMounted(() => {
  updateScale()
  const saved = uni.getStorageSync('shiYaChildAgeText')
  if (ageList.includes(saved)) selectedAge.value = saved
  if (typeof uni.onWindowResize === 'function') uni.onWindowResize(handleResize)
})

onUnmounted(() => {
  if (typeof uni.offWindowResize === 'function') uni.offWindowResize(handleResize)
})

onShow(() => {
  loadDailyPoem()
})
</script>

<style scoped>
* { box-sizing: border-box; }
button::after { border: 0; }
.page-root { width: 100vw; height: 100vh; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #172421; font-family: "STKaiti", "KaiTi", "PingFang SC", serif; }
.town { position: relative; width: 1672px; height: 770px; flex: 0 0 auto; overflow: hidden; transform-origin: center; }
.town-bg { position: absolute; inset: 0; width: 100%; height: 100%; }
.brand { position: absolute; left: 18px; top: 0; width: 400px; height: 180px; z-index: 20; filter: drop-shadow(0 6px 5px rgba(84, 54, 24, .2)); }
.brand image { width: 100%; }
.top-actions { position: absolute; top: 24px; right: 30px; display: flex; gap: 18px; z-index: 40; font-family: "PingFang SC", sans-serif; }
.age-control, .parent-control { position: relative; height: 72px; display: flex; align-items: center; justify-content: center; color: #744318; font-weight: 900; font-size: 25px; }
.age-control { width: 178px; padding-right: 20px; }
.parent-control { width: 168px; }
.age-control image, .parent-control image { position: absolute; inset: 0; width: 100%; height: 100%; z-index: -1; }
.age-arrow { position: absolute; right: 29px; top: 19px; }
.age-menu { position: absolute; right: 184px; top: 76px; width: 174px; padding: 10px; border: 4px solid #b9792f; border-radius: 20px; background: #fff1cb; box-shadow: 0 10px 25px rgba(61, 40, 18, .25); }
.age-menu view { height: 50px; border-radius: 13px; display: flex; align-items: center; justify-content: center; color: #795126; font-size: 23px; font-weight: 900; }
.age-menu view.active { background: #df9a42; color: white; }
.town-entry { position: absolute; z-index: 5; transition: transform .15s ease, filter .15s ease; transform-origin: center; }
.town-entry image { position: absolute; max-width: none; max-height: none; pointer-events: none; }
.town-entry.pressed { transform: scale(.9); filter: brightness(1.08) drop-shadow(0 12px 10px rgba(88, 56, 22, .25)); }
.camera-entry { left: 109px; top: 149px; width: 440px; height: 330px; }
.camera-entry image { left: 0; top: 0; width: 440px; height: 330px; }
.today-entry { left: 606px; top: 83px; width: 447px; height: 463px; z-index: 9; }
.today-entry image { left: -232px; top: -22px; width: 900px; height: 500px; }
.today-entry.pressed { transform: none; filter: brightness(1.06) drop-shadow(0 10px 8px rgba(88, 56, 22, .22)); }
.search-entry { left: 105px; top: 395px; width: 521px; height: 294px; }
.search-entry image { left: 0; top: 0; width: 521px; height: 294px; }
.practice-entry { left: 1149px; top: 188px; width: 335px; height: 270px; }
.practice-entry image { left: 0; top: 0; width: 335px; height: 270px; }
.stamps-entry { left: 1120px; top: 412px; width: 450px; height: 250px; }
.stamps-entry image { left: 0; top: 0; width: 450px; height: 250px; }
.modal-mask { position: absolute; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; background: rgba(55, 46, 30, .38); backdrop-filter: blur(5px); }
.lottery-modal { position: relative; width: 790px; height: 584px; animation: reveal .35s ease-out; }
.lottery-modal > image { position: absolute; inset: 0; width: 100%; height: 100%; }
@keyframes reveal { from { transform: scale(.75) rotate(-2deg); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.modal-close { position: absolute; right: 8px; top: 48px; width: 72px; height: 72px; padding: 0; border: 0; background: transparent; z-index: 8; }
.lottery-copy { position: absolute; inset: 0; color: #663c19; text-align: center; pointer-events: none; }
.lottery-kicker { position: absolute; left: 175px; right: 175px; top: 40px; height: 86px; display: flex; align-items: center; justify-content: center; font-size: 42px; font-weight: 900; }
.lottery-title { position: absolute; left: 145px; right: 145px; top: 180px; font-size: 72px; font-weight: 900; letter-spacing: 12px; }
.lottery-title.long-title { font-size: 56px; letter-spacing: 4px; }
.lottery-author { position: absolute; left: 170px; right: 170px; top: 282px; font-size: 30px; font-weight: 800; }
.lottery-line { position: absolute; left: 120px; right: 180px; top: 345px; font-size: 24px; color: #8d623a; }
.lottery-actions { position: absolute; left: 126px; right: 126px; bottom: 70px; height: 82px; display: flex; gap: 39px; }
.scroll-button { flex: 1; height: 82px; padding: 0; border: 0; background: transparent; color: #623a17; font-size: 27px; font-weight: 900; }
.scroll-button.primary, .scroll-button.secondary { background: transparent; box-shadow: none; }
/* 手机横屏可读性 */
.age-control, .parent-control { font-size: 34px; }
.age-menu view { font-size: 30px; }
.lottery-kicker { font-size: 52px; }
.lottery-title { font-size: 78px; }
.lottery-title.long-title { font-size: 60px; letter-spacing: 3px; }
.lottery-author { font-size: 38px; }
.lottery-line { font-size: 34px; }
.scroll-button { font-size: 36px; }
</style>
