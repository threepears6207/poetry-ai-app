export const FIXED_PROMPTS = Object.freeze({
  camera: { text: '拍一拍找古诗', src: '/static/audio/prompts/camera-find-poem.mp3' },
  today: { text: '学一首新诗', src: '/static/audio/prompts/today-new-poem.mp3' },
  search: { text: '找你喜欢的诗', src: '/static/audio/prompts/find-favorite-poem.mp3' },
  practice: { text: '读一读，练一练', src: '/static/audio/prompts/read-and-practice.mp3' },
  stamps: { text: '看看小红花', src: '/static/audio/prompts/see-red-flowers.mp3' }
})

const audioCache = new Map()
let activeAudio = null

const supportsAudio = () => typeof uni !== 'undefined' && typeof uni.createInnerAudioContext === 'function'

const destroyAudio = (audio) => {
  if (!audio) return
  try { audio.stop() } catch (err) {}
  try { audio.destroy() } catch (err) {}
}

const createAudio = (key) => {
  const prompt = FIXED_PROMPTS[key]
  if (!prompt?.src || !supportsAudio()) return null
  const audio = uni.createInnerAudioContext()
  audio.autoplay = false
  audio.src = prompt.src
  audioCache.set(key, audio)
  return audio
}

const getAudio = (key, recreate = false) => {
  if (recreate) {
    destroyAudio(audioCache.get(key))
    audioCache.delete(key)
  }
  return audioCache.get(key) || createAudio(key)
}

export const preloadFixedPrompts = () => {
  if (!supportsAudio()) return
  Object.keys(FIXED_PROMPTS).forEach(key => getAudio(key))
}

const playOnce = (key, recreate = false) => new Promise((resolve) => {
  const audio = getAudio(key, recreate)
  if (!audio) return resolve(false)
  if (activeAudio && activeAudio !== audio) {
    try { activeAudio.stop() } catch (err) {}
  }
  activeAudio = audio
  let settled = false
  let timeoutId = null
  const finish = (played) => {
    if (settled) return
    settled = true
    clearTimeout(timeoutId)
    if (activeAudio === audio) activeAudio = null
    resolve(played)
  }
  timeoutId = setTimeout(() => finish(false), 6500)
  audio.onEnded(() => finish(true))
  audio.onError(() => finish(false))
  try {
    audio.stop()
    audio.seek(0)
    audio.play()
  } catch (err) {
    finish(false)
  }
})

export const playFixedPrompt = async (key) => {
  if (await playOnce(key)) return true
  return playOnce(key, true)
}

export const destroyFixedPrompts = () => {
  if (activeAudio) {
    try { activeAudio.stop() } catch (err) {}
    activeAudio = null
  }
  audioCache.forEach(audio => destroyAudio(audio))
  audioCache.clear()
}
