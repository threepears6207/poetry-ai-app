import { API, normalizeAssetUrl } from '@/utils/api.js'
import { setBgmVolume } from '@/utils/bgm.js'

const audioCache = new Map()
let speechAudio = null
let requestToken = 0

const stopCurrentSpeech = () => {
  if (!speechAudio) return
  const current = speechAudio
  speechAudio = null
  try { current.stop() } catch (err) {}
  try { current.destroy() } catch (err) {}
  restoreBgm()
}

const restoreBgm = () => setBgmVolume(0.22)

const loadSpeechUrl = async (text) => {
  const key = String(text || '').trim()
  if (!key) return ''
  if (audioCache.has(key)) return audioCache.get(key)

  // “xiaoyi + ui” is used for short interface prompts instead of poem recitation.
  const result = await API.textToSpeech(key, 'xiaoyi', 'ui')
  const rawUrl = result?.audio_url || result?.url || result?.data?.audio_url || ''
  const url = normalizeAssetUrl(rawUrl)
  if (url) audioCache.set(key, url)
  return url
}

export const speakText = async (text) => {
  const content = String(text || '').trim()
  if (!content) return false

  const token = ++requestToken
  stopCurrentSpeech()

  try {
    const url = await loadSpeechUrl(content)
    if (!url || token !== requestToken) return false

    const player = uni.createInnerAudioContext()
    speechAudio = player
    player.autoplay = false
    player.src = url
    setBgmVolume(0.07)

    const cleanup = () => {
      if (speechAudio !== player) return
      speechAudio = null
      try { player.destroy() } catch (err) {}
      restoreBgm()
    }
    player.onEnded(cleanup)
    player.onStop(cleanup)
    player.onError((err) => {
      console.log('界面点读播放失败：', err)
      cleanup()
    })
    player.play()
    return true
  } catch (err) {
    console.log('界面点读请求失败：', err)
    restoreBgm()
    return false
  }
}
