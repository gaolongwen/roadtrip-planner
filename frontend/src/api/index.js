import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 自动带上 Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    
    // 401 错误时清除 token 并跳转登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 如果不在登录页，跳转到登录页
      if (window.location.hash !== '#/login') {
        window.location.hash = '/login'
      }
    }
    
    return Promise.reject(error)
  }
)

// 认证相关 API
export const authApi = {
  // 登录
  login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 注册
  register(username, password, nickname = '') {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    if (nickname) {
      formData.append('nickname', nickname)
    }
    return api.post('/api/auth/register', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取当前用户信息
  getMe() {
    return api.get('/api/auth/me')
  },
}

// 景点相关 API
export const poiApi = {
  // 获取景点列表
  getPois(params = {}) {
    return api.get('/api/pois', { params })
  },

  // 获取单个景点
  getPoi(id) {
    return api.get(`/api/pois/${id}`)
  },

  // 获取地图范围内的景点
  getPoisByBbox(minLat, maxLat, minLng, maxLng, params = {}) {
    return api.get('/api/pois/bbox', {
      params: {
        min_lat: minLat,
        max_lat: maxLat,
        min_lng: minLng,
        max_lng: maxLng,
        ...params,
      },
    })
  },
}

// 行程相关 API
export const tripApi = {
  // 创建行程
  createTrip(name = '未命名行程') {
    const formData = new FormData()
    formData.append('name', name)
    return api.post('/api/trips', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取行程详情
  getTrip(tripId) {
    return api.get(`/api/trips/${tripId}`)
  },

  // 通过分享码获取行程
  getTripByCode(shareCode) {
    return api.get(`/api/trips/code/${shareCode}`)
  },

  // 更新行程名称
  updateTrip(tripId, name) {
    return api.patch(`/api/trips/${tripId}?name=${encodeURIComponent(name)}`)
  },

  // 添加景点到行程
  addPoi(tripId, poiId, dayNumber = 1, notes = '') {
    const params = new URLSearchParams({ poi_id: poiId, day_number: dayNumber, notes })
    return api.post(`/api/trips/${tripId}/pois?${params}`)
  },

  // 移除景点
  removePoi(tripId, poiId) {
    return api.delete(`/api/trips/${tripId}/pois/${poiId}`)
  },

  // 更新景点信息
  updateTripPoi(tripId, poiId, data) {
    const params = new URLSearchParams()
    if (data.day_number !== undefined) params.append('day_number', data.day_number)
    if (data.order_index !== undefined) params.append('order_index', data.order_index)
    if (data.notes !== undefined) params.append('notes', data.notes)
    return api.patch(`/api/trips/${tripId}/pois/${poiId}?${params}`)
  },

  // 加入行程
  joinTrip(tripId) {
    const params = new URLSearchParams()
    return api.post(`/api/trips/${tripId}/members?${params}`)
  },

  // 获取成员列表
  getMembers(tripId) {
    return api.get(`/api/trips/${tripId}/members`)
  },

    // 规划行程路线（异步轮询）
  planTrip(tripId, startCity, endCity, days) {
    const formData = new FormData()
    formData.append('start_city', startCity)
    formData.append('end_city', endCity)
    formData.append('days', days)
    return api.post(`/api/trips/${tripId}/plan`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // 获取规划任务状态
  getPlanStatus(tripId, taskId) {
    return api.get(`/api/trips/${tripId}/plan/status/${taskId}`)
  },

  // 获取行程路线
  getRoute(tripId) {
    return api.get(`/api/trips/${tripId}/route`)
  },

  // 导出行程
  exportTrip(tripId) {
    return api.post(`/api/trips/${tripId}/export`)
  },
}

export default api
