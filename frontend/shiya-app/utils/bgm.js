const HOME_BGM_PATH = '/static/audio/home-garden-loop.wav'
const HOME_ROUTES = new Set([
  'pages/index/index',
  'pages/recommend/recommend',
  'pages/review/review',
  'pages/collection/collection',
  'pages/parent/parent'
])

let audio = null
let wanted = false

const currentRoute = () => {
  try {
    const pages = getCurrentPages()
    return pages.length ? String(pages[pages.length - 1].route || '') : ''
  } catch (err) {
    return ''
  }
}

const getAudio = () => {
  if (audio || typeof uni.createInnerAudioContext !== 'function') return audio
  audio = uni.createInnerAudioContext()
  audio.autoplay = false
  audio.loop = true
  audio.volume = 0.22
  audio.src = HOME_BGM_PATH
  audio.onError((err) => console.log('BGM 播放失败：', err))
  return audio
}

const tryPlay = () => {
  if (!wanted) return
  const player = getAudio()
  if (!player) return
  try {
    player.play()
  } catch (err) {
    // H5/iOS may require the first user gesture before audio can start.
  }
}

export const syncBgmForCurrentPage = () => {
  wanted = HOME_ROUTES.has(currentRoute())
  if (wanted) tryPlay()
  else pauseBgm()
}

export const unlockBgm = () => {
  tryPlay()
}

export const pauseBgm = () => {
  if (!audio) return
  try { audio.pause() } catch (err) {}
}

export const setBgmVolume = (volume = 0.22) => {
  const player = getAudio()
  if (player) player.volume = Math.max(0, Math.min(1, Number(volume) || 0))
}
