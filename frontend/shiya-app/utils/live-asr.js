import { DEFAULT_USER_ID, LIVE_ASR_STREAM_URL } from './api.js'

// #ifdef APP-PLUS
import {
  onLiveAudioError,
  onLiveAudioFrame,
  startLiveAudio,
  stopLiveAudio,
} from '@/uni_modules/shiya-live-audio'
// #endif

// H5 cannot resolve or execute the native UTS recorder. These stubs keep the
// shared module importable; chat.vue selects its browser recorder on H5.
// #ifndef APP-PLUS
const nativeAudioUnavailable = () => {
  throw new Error('Live audio recording is only available in the App build')
}
const onLiveAudioError = nativeAudioUnavailable
const onLiveAudioFrame = nativeAudioUnavailable
const startLiveAudio = nativeAudioUnavailable
const stopLiveAudio = () => ({ recording: false, sampleRate: 16000, frameBytes: 1280 })
// #endif

let activeSession = null

const parseServerEvent = (rawData) => {
  if (typeof rawData === 'string') return JSON.parse(rawData)
  return rawData || {}
}

const containsHumanVoice = (pcmBuffer) => {
  if (!pcmBuffer || typeof Int16Array === 'undefined') return false
  const samples = new Int16Array(pcmBuffer)
  if (!samples.length) return false

  let total = 0
  let peak = 0
  const stride = 8
  for (let index = 0; index < samples.length; index += stride) {
    const value = Math.abs(samples[index] || 0)
    total += value
    peak = Math.max(peak, value)
  }
  const average = total / Math.ceil(samples.length / stride)
  return peak >= 1200 || average >= 350
}

const closeSession = (session) => {
  if (!session || activeSession !== session) return
  try {
    session.socketTask.close({ code: 1000, reason: 'live-asr-finished' })
  } catch (error) {
    console.log('Failed to close live ASR socket:', error)
  }
  activeSession = null
}

const failSession = (session, error) => {
  if (!session || session.finished) return
  session.finished = true
  try {
    stopLiveAudio()
  } catch (stopError) {
    console.log('Failed to stop native recorder:', stopError)
  }
  session.onError?.(error instanceof Error ? error : new Error(String(error || 'Live ASR failed')))
  closeSession(session)
}

export const isLiveAsrActive = () => Boolean(activeSession && !activeSession.finished)

export const startLiveAsr = ({
  userId = DEFAULT_USER_ID,
  endVadTime = 1400,
  onReady,
  onVoiceStart,
  onPartial,
  onFinal,
  onError,
} = {}) => {
  if (isLiveAsrActive()) return Promise.reject(new Error('Live ASR is already active'))

  return new Promise((resolve, reject) => {
    let resolved = false
    const socketTask = uni.connectSocket({
      url: LIVE_ASR_STREAM_URL,
      fail: (error) => reject(new Error(error?.errMsg || 'Unable to connect to live ASR')),
    })
    const session = {
      socketTask,
      finished: false,
      ending: false,
      voiceDetected: false,
      onError,
    }
    activeSession = session

    const rejectBeforeReady = (error) => {
      const normalized = error instanceof Error ? error : new Error(String(error))
      if (!resolved) reject(normalized)
      failSession(session, normalized)
    }

    socketTask.onOpen(() => {
      socketTask.send({
        data: JSON.stringify({ type: 'start', user_id: userId, net_type: 1, end_vad_time: endVadTime }),
        fail: (error) => rejectBeforeReady(new Error(error?.errMsg || 'Unable to start live ASR')),
      })
    })

    socketTask.onMessage((message) => {
      let event
      try {
        event = parseServerEvent(message?.data)
      } catch (error) {
        rejectBeforeReady(new Error('Live ASR returned invalid data'))
        return
      }

      if (event?.event === 'ready') {
        try {
          // UTS keeps on... functions with one callback alive for continuous events.
          onLiveAudioFrame((pcmBase64) => {
              if (activeSession !== session || session.finished || session.ending) return
              const pcmBuffer = uni.base64ToArrayBuffer(pcmBase64)
              if (!session.voiceDetected && containsHumanVoice(pcmBuffer)) {
                session.voiceDetected = true
                onVoiceStart?.()
              }
              socketTask.send({
                data: pcmBuffer,
                fail: (error) => failSession(session, new Error(error?.errMsg || 'Failed to send live PCM')),
              })
          })
          onLiveAudioError((message) => failSession(session, new Error(message || 'Native live recording failed')))
          startLiveAudio()
          resolved = true
          onReady?.(event)
          resolve(event)
        } catch (error) {
          rejectBeforeReady(error)
        }
        return
      }

      if (event?.event === 'partial') {
        onPartial?.(String(event.text || ''), event)
        return
      }

      if (event?.event === 'final') {
        session.finished = true
        try {
          stopLiveAudio()
        } catch (error) {
          console.log('Failed to stop recorder after final ASR:', error)
        }
        onFinal?.(String(event.text || ''), event)
        closeSession(session)
        return
      }

      if (event?.event === 'error') {
        rejectBeforeReady(new Error(event.error || 'Live ASR failed'))
      }
    })

    socketTask.onError((error) => rejectBeforeReady(new Error(error?.errMsg || 'Live ASR socket error')))
    socketTask.onClose(() => {
      if (!session.finished && !session.ending) {
        rejectBeforeReady(new Error('Live ASR socket closed'))
      }
    })
  })
}

export const stopLiveAsr = () => {
  const session = activeSession
  if (!session || session.finished || session.ending) return false

  session.ending = true
  try {
    stopLiveAudio()
  } catch (error) {
    console.log('Failed to stop native recorder:', error)
  }
  session.socketTask.send({
    data: JSON.stringify({ type: 'end' }),
    fail: (error) => failSession(session, new Error(error?.errMsg || 'Failed to finish live ASR')),
  })
  return true
}
