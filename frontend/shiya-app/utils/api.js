// utils/api.js

// =====================================================
// 1. 后端基础地址
// =====================================================
// 电脑浏览器本机联调：使用 127.0.0.1
const BASE_URL = 'http://127.0.0.1:8000'

// 手机真机联调时，不要用 127.0.0.1。
// 要改成你电脑的局域网 IP，例如：
// const BASE_URL = 'http://192.168.1.23:8000'

export const DEFAULT_USER_ID = 'test_user'


// =====================================================
// 1.1 AI 生成类接口的前端缓存
// 说明：详情页预请求、播放页再次请求时，可复用同一个 Promise，避免重复触发生成。
// =====================================================
const imageGeneratePromiseCache = new Map()
const poetAvatarPromiseCache = new Map()


// =====================================================
// 2. 本地兜底古诗数据
// 后端没连上时，页面不会空白
// =====================================================
export const LOCAL_POEMS = [
  {
    id: 'poem_001',
    title: '春晓',
    author: '孟浩然',
    dynasty: '唐',
    content: ['春眠不觉晓', '处处闻啼鸟', '夜来风雨声', '花落知多少'],
    translation: '春天睡醒时天已经亮了，到处都能听见小鸟的叫声。夜里风雨交加，不知道花儿落了多少。',
    tags: ['春天', '自然', '儿童启蒙'],
    content_preview: '春眠不觉晓，处处闻啼鸟。'
  },
  {
    id: 'poem_002',
    title: '静夜思',
    author: '李白',
    dynasty: '唐',
    content: ['床前明月光', '疑是地上霜', '举头望明月', '低头思故乡'],
    translation: '明亮的月光洒在床前，好像地上的白霜。抬头看着天上的明月，低下头想念自己的家乡。',
    tags: ['月亮', '思乡', '李白'],
    content_preview: '床前明月光，疑是地上霜。'
  },
  {
    id: 'poem_003',
    title: '咏鹅',
    author: '骆宾王',
    dynasty: '唐',
    content: ['鹅鹅鹅', '曲项向天歌', '白毛浮绿水', '红掌拨清波'],
    translation: '白鹅弯着脖子向天唱歌，洁白的羽毛漂浮在绿水上，红色的脚掌拨动着清清的水波。',
    tags: ['动物', '儿童启蒙', '自然'],
    content_preview: '鹅鹅鹅，曲项向天歌。'
  },
  {
    id: 'poem_004',
    title: '悯农',
    author: '李绅',
    dynasty: '唐',
    content: ['锄禾日当午', '汗滴禾下土', '谁知盘中餐', '粒粒皆辛苦'],
    translation: '农民在正午太阳下锄地，汗水滴落在庄稼下面的土地里。谁知道碗里的饭，每一粒都来得很辛苦。',
    tags: ['劳动', '珍惜粮食', '儿童启蒙'],
    content_preview: '锄禾日当午，汗滴禾下土。'
  },
  {
    id: 'poem_005',
    title: '登鹳雀楼',
    author: '王之涣',
    dynasty: '唐',
    content: ['白日依山尽', '黄河入海流', '欲穷千里目', '更上一层楼'],
    translation: '太阳靠着群山慢慢落下，黄河奔流入海。想要看得更远，就要再登上一层楼。',
    tags: ['登高', '黄河', '励志'],
    content_preview: '白日依山尽，黄河入海流。'
  }
]


// =====================================================
// 3. 静态资源地址处理
// =====================================================
export const normalizeAssetUrl = (url) => {
  if (!url) return ''

  const value = String(url).trim()

  if (
    value.startsWith('data:image') ||
    value.startsWith('blob:')
  ) {
    return value
  }

  if (
    value.startsWith('http://') ||
    value.startsWith('https://')
  ) {
    return encodeURI(value)
  }

  if (value.startsWith('/')) {
    return encodeURI(`${BASE_URL}${value}`)
  }

  return encodeURI(`${BASE_URL}/${value}`)
}

export const getPoetAvatarStaticUrl = (poetName = '') => {
  const name = String(poetName || '').trim()

  if (!name) return ''

  return normalizeAssetUrl(`/static/images/poets/${name}.jpg`)
}


// =====================================================
// 4. 统一请求封装
// =====================================================
export const request = (options) => {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...(options.header || {})
      },
      timeout: options.timeout || 30000,

      success: (res) => {
        console.log('[接口成功]', options.method || 'GET', options.url, res)

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }

        reject({
          message: '接口状态码异常',
          statusCode: res.statusCode,
          data: res.data
        })
      },

      fail: (err) => {
        console.log('[接口失败]', options.method || 'GET', options.url, err)
        reject(err)
      }
    })
  })
}



const buildPoemContent = (poem = {}) => {
  if (Array.isArray(poem.content)) {
    return poem.content
  }

  if (Array.isArray(poem.poem_content)) {
    return poem.poem_content
  }

  return String(poem.content || poem.poem_content || '')
    .split(/[，,。；;！!？?\n]/)
    .map((line) => line.trim())
    .filter(Boolean)
}

const getPoemImageCacheKey = (poem = {}, content = []) => {
  return String(
    poem.id ||
    poem.poem_id ||
    `${poem.title || poem.poem_title || ''}-${poem.author || poem.poet_name || ''}-${content.join('|')}`
  )
}

const getPoetAvatarCacheKey = (poetName = '', dynasty = '') => {
  return `${dynasty || '未知朝代'}-${poetName || '古代诗人'}`
}

// =====================================================
// 5. 后端接口 API
// =====================================================
export const API = {
  // -----------------------------------------------------
  // 健康检查
  // GET /ping
  // -----------------------------------------------------
  ping() {
    return request({
      url: '/ping',
      method: 'GET'
    })
  },


  // -----------------------------------------------------
  // 搜索古诗
  // 支持两种写法：
  // API.searchPoems('静夜思')
  // API.searchPoems({ keyword: '静夜思', author: '李白', dynasty: '唐', tag: '月亮' })
  // -----------------------------------------------------
  searchPoems(params = '', page = 1, pageSize = 10) {
    let queryParams = {}

    if (typeof params === 'string') {
      queryParams = {
        keyword: params,
        page,
        page_size: pageSize
      }
    } else {
      queryParams = {
        keyword: params.keyword || '',
        author: params.author || '',
        dynasty: params.dynasty || '',
        tag: params.tag || '',
        page: params.page || 1,
        page_size: params.pageSize || params.page_size || 10
      }
    }

    const query = Object.keys(queryParams)
      .filter((key) => queryParams[key] !== undefined && queryParams[key] !== null && queryParams[key] !== '')
      .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(queryParams[key])}`)
      .join('&')

    return request({
      url: `/poems/search?${query}`,
      method: 'GET'
    })
  },


  // -----------------------------------------------------
  // 获取古诗详情
  // GET /poems/{poem_id}
  // -----------------------------------------------------
  getPoemDetail(poemId) {
    return request({
      url: `/poems/${poemId}`,
      method: 'GET'
    })
  },


  // -----------------------------------------------------
  // 添加学习记录
  // POST /record
  // -----------------------------------------------------
  addRecord(poemId, durationSeconds = 0) {
    return request({
      url: '/record',
      method: 'POST',
      data: {
        poem_id: poemId,
        user_id: DEFAULT_USER_ID,
        duration_seconds: Math.max(0, Math.round(Number(durationSeconds || 0)))
      }
    })
  },


  // -----------------------------------------------------
  // 查询学习记录
  // GET /record?user_id=test_user
  // -----------------------------------------------------
  getRecords() {
    return request({
      url: `/record?user_id=${DEFAULT_USER_ID}`,
      method: 'GET'
    })
  },


  // -----------------------------------------------------
  // 家长端学习统计
  // GET /record/summary?user_id=test_user
  // -----------------------------------------------------
  getRecordSummary() {
    return request({
      url: `/record/summary?user_id=${DEFAULT_USER_ID}`,
      method: 'GET'
    })
  },


  // -----------------------------------------------------
  // 推荐古诗
  // GET /recommend?user_id=test_user&limit=5
  // -----------------------------------------------------
  getRecommend(limit = 5) {
    return request({
      url: `/recommend?user_id=${DEFAULT_USER_ID}&limit=${limit}`,
      method: 'GET'
    })
  },


  // -----------------------------------------------------
  // AI 诗人对话
  // POST /chat
  // -----------------------------------------------------
  chatWithPoet(data) {
    return request({
      url: '/chat',
      method: 'POST',
      data: {
        message: data.message || '',
        poet_name: data.poet_name || '古代诗人',
        dynasty: data.dynasty || '唐',
        poem_title: data.poem_title || '',
        poem_content: data.poem_content || '',
        history: Array.isArray(data.history) ? data.history : []
      },
      timeout: 60000
    })
  },


  // -----------------------------------------------------
  // 拍照识诗 / 文字演示版
  // POST /ocr
  // -----------------------------------------------------
  recognizePoem(text, mode = 'text') {
    return request({
      url: '/ocr',
      method: 'POST',
      data: {
        image: text,
        mode
      },
      timeout: 60000
    })
  },


  // -----------------------------------------------------
  // 拍照识诗 / 真实图片 base64 版
  // POST /ocr
  //
  // 为兼容后端不同版本，同时传 image 和 image_base64：
  // - image：带 data:image/jpeg;base64, 前缀
  // - image_base64：纯 base64
  // -----------------------------------------------------
  recognizePoemImage(imageBase64) {
    const pureBase64 = String(imageBase64 || '').replace(/^data:image\/\w+;base64,/, '')
    const imageDataUrl = pureBase64.startsWith('data:image')
      ? pureBase64
      : `data:image/jpeg;base64,${pureBase64}`

    return request({
      url: '/ocr',
      method: 'POST',
      data: {
        image: imageDataUrl,
        image_base64: pureBase64,
        mode: 'image_base64'
      },
      timeout: 90000
    })
  },


  // -----------------------------------------------------
  // AI 配图生成
  // POST /generate/image
  // 首次生成可能需要 30 秒到 2 分钟，必须使用 120 秒以上超时。
  // 这里设置为 300 秒，并加入前端 Promise 缓存，方便详情页提前预热、播放页复用。
  // -----------------------------------------------------
  generateImage(poem = {}, options = {}) {
    const content = buildPoemContent(poem)
    const cacheKey = getPoemImageCacheKey(poem, content)
    const forceRegenerate = Boolean(poem.force_regenerate || options.forceRegenerate)

    if (!forceRegenerate && imageGeneratePromiseCache.has(cacheKey)) {
      return imageGeneratePromiseCache.get(cacheKey)
    }

    const requestPromise = request({
      url: '/generate/image',
      method: 'POST',
      data: {
        poem_id: poem.id || poem.poem_id || '',
        poem_title: poem.title || poem.poem_title || '',
        poem_content: content,
        poet_name: poem.author || poem.poet_name || '',
        dynasty: poem.dynasty || '',
        tags: Array.isArray(poem.tags) ? poem.tags : [],
        ...(forceRegenerate ? { force_regenerate: true } : {})
      },
      timeout: 300000
    }).catch((err) => {
      imageGeneratePromiseCache.delete(cacheKey)
      throw err
    })

    if (!forceRegenerate) {
      imageGeneratePromiseCache.set(cacheKey, requestPromise)
    }

    return requestPromise
  },


  // -----------------------------------------------------
  // 预热 AI 配图生成
  // 给诗词详情页使用：进入详情页时直接 API.preloadGenerateImage(poem) 即可。
  // -----------------------------------------------------
  preloadGenerateImage(poem = {}) {
    return API.generateImage(poem).catch((err) => {
      console.log('AI 配图预热失败：', err)
      return null
    })
  },


  // -----------------------------------------------------
  // AI 诗人形象生成
  // POST /generate/peot_avatar
  // 注意：后端当前路径为 peot_avatar，前端按后端实际路径调用。
  // -----------------------------------------------------
  generatePoetAvatar(poet = {}) {
    const poetName = poet.poet_name || poet.poetName || poet.author || poet.name || '古代诗人'
    const dynasty = poet.dynasty || '唐'
    const cacheKey = getPoetAvatarCacheKey(poetName, dynasty)

    if (poetAvatarPromiseCache.has(cacheKey)) {
      return poetAvatarPromiseCache.get(cacheKey)
    }

    const requestPromise = request({
      url: '/generate/peot_avatar',
      method: 'POST',
      data: {
        poet_name: poetName,
        dynasty
      },
      timeout: 180000
    }).catch((err) => {
      poetAvatarPromiseCache.delete(cacheKey)
      throw err
    })

    poetAvatarPromiseCache.set(cacheKey, requestPromise)
    return requestPromise
  },


  // -----------------------------------------------------
  // 语音朗读
  // POST /tts
  // 当前学习页不使用该接口，保留封装方便以后扩展
  // -----------------------------------------------------
  textToSpeech(text, voice = 'zh-CN-XiaoxiaoNeural') {
    return request({
      url: '/tts',
      method: 'POST',
      data: {
        text,
        voice
      },
      timeout: 60000
    })
  }
}


// =====================================================
// 6. 本地数据辅助方法
// =====================================================
export const getLocalPoemById = (poemId) => {
  return LOCAL_POEMS.find(item => item.id === poemId) || LOCAL_POEMS[0]
}


export const searchLocalPoems = (keyword) => {
  const kw = (keyword || '').trim()

  if (!kw) return LOCAL_POEMS

  return LOCAL_POEMS.filter(item => {
    return (
      item.title.includes(kw) ||
      item.author.includes(kw) ||
      item.dynasty.includes(kw) ||
      item.tags.join('').includes(kw) ||
      item.content.join('').includes(kw)
    )
  })
}


export { BASE_URL }
