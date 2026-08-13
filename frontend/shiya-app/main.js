import App from './App'
import { syncBgmForCurrentPage, unlockBgm } from './utils/bgm.js'

const bgmPageMixin = {
  onShow() {
    setTimeout(syncBgmForCurrentPage, 0)
  },
  onReady() {
    // Browsers and iOS only allow the first playback after a user gesture.
    // A one-time listener unlocks BGM without adding a visible button.
    if (typeof document !== 'undefined') {
      document.addEventListener('pointerdown', unlockBgm, { once: true, passive: true })
      document.addEventListener('touchstart', unlockBgm, { once: true, passive: true })
    }
  }
}

// #ifndef VUE3
import Vue from 'vue'
import './uni.promisify.adaptor'
Vue.config.productionTip = false
Vue.mixin(bgmPageMixin)
App.mpType = 'app'
const app = new Vue({
  ...App
})
app.$mount()
// #endif

// #ifdef VUE3
import { createSSRApp } from 'vue'
export function createApp() {
  const app = createSSRApp(App)
  app.mixin(bgmPageMixin)
  return {
    app
  }
}
// #endif
