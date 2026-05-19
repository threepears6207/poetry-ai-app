const BASE_URL = 'http://127.0.0.1:8000'

export const DEFAULT_USER_ID = 'test_user'

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

export const request = (options) => {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      timeout: 5000,
      success: (res) => {
        resolve(res.data)
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

export const API = {
  searchPoems(keyword, page = 1, pageSize = 10) {
    return request({
      url: `/poems/search?keyword=${encodeURIComponent(keyword)}&page=${page}&page_size=${pageSize}`
    })
  },

  getPoemDetail(poemId) {
    return request({
      url: `/poems/${poemId}`
    })
  },

  addRecord(poemId, durationSeconds = 0) {
    return request({
      url: '/record',
      method: 'POST',
      data: {
        poem_id: poemId,
        user_id: DEFAULT_USER_ID,
        duration_seconds: durationSeconds
      }
    })
  },

  chatWithPoet(message, poemId = 'poem_001') {
    return request({
      url: '/chat',
      method: 'POST',
      data: {
        message,
        poem_id: poemId,
        user_id: DEFAULT_USER_ID
      }
    })
  },

  getRecommend(limit = 5) {
    return request({
      url: `/recommend?user_id=${DEFAULT_USER_ID}&limit=${limit}`
    })
  }
}

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
