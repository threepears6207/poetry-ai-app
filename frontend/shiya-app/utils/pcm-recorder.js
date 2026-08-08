// Android 端跟读和实时聊天共用同一套 16kHz / 16bit / 单声道 PCM 采集能力。
// 这里仅负责采集和拼接，评分/聊天逻辑仍由各页面控制。
// #ifdef APP-PLUS
import {
  onLiveAudioError,
  onLiveAudioFrame,
  startLiveAudio,
  stopLiveAudio,
} from '@/uni_modules/shiya-live-audio'
// #endif

// #ifndef APP-PLUS
const nativeAudioUnavailable = () => {
  throw new Error('PCM 跟读录音仅支持 Android App 真机')
}
const onLiveAudioError = nativeAudioUnavailable
const onLiveAudioFrame = nativeAudioUnavailable
const startLiveAudio = nativeAudioUnavailable
const stopLiveAudio = () => ({ recording: false, sampleRate: 16000, frameBytes: 1280 })
// #endif

let activeCapture = null

const concatFramesToBase64 = (frames = []) => {
  if (!frames.length) return ''

  const buffers = frames
    .map((frame) => uni.base64ToArrayBuffer(frame))
    .filter((buffer) => buffer && buffer.byteLength)

  const totalLength = buffers.reduce((sum, buffer) => sum + buffer.byteLength, 0)
  if (!totalLength) return ''

  const merged = new Uint8Array(totalLength)
  let offset = 0
  buffers.forEach((buffer) => {
    merged.set(new Uint8Array(buffer), offset)
    offset += buffer.byteLength
  })

  return uni.arrayBufferToBase64(merged.buffer)
}

export const isPcmCaptureActive = () => Boolean(activeCapture && !activeCapture.finished)

export const startPcmCapture = ({ onError } = {}) => {
  if (isPcmCaptureActive()) {
    return Promise.reject(new Error('已有 PCM 录音正在进行'))
  }

  return new Promise((resolve, reject) => {
    const capture = {
      frames: [],
      finished: false,
      onError,
    }
    activeCapture = capture

    const failCapture = (error) => {
      if (capture.finished) return
      capture.finished = true
      if (activeCapture === capture) activeCapture = null
      try {
        stopLiveAudio()
      } catch (stopError) {
        console.log('停止 PCM 跟读录音失败：', stopError)
      }
      const normalized = error instanceof Error ? error : new Error(String(error || 'PCM 录音失败'))
      capture.onError?.(normalized)
      reject(normalized)
    }

    try {
      onLiveAudioFrame((pcmBase64) => {
        if (activeCapture !== capture || capture.finished || !pcmBase64) return
        capture.frames.push(String(pcmBase64))
      })
      onLiveAudioError((message) => failCapture(new Error(message || 'PCM 录音失败')))
      const status = startLiveAudio()
      resolve(status)
    } catch (error) {
      failCapture(error)
    }
  })
}

export const stopPcmCapture = () => {
  const capture = activeCapture
  if (!capture || capture.finished) return ''

  capture.finished = true
  activeCapture = null
  try {
    stopLiveAudio()
  } catch (error) {
    console.log('停止 PCM 跟读录音失败：', error)
  }

  return concatFramesToBase64(capture.frames)
}
