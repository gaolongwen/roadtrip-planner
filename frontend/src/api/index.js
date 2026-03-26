import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

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
    return api.post(`/api/trips?name=${encodeURIComponent(name)}`)
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
  addPoi(tripId, poiId, dayNumber = 1, notes = '', nickname = '匿名') {
    const params = new URLSearchParams({ poi_id: poiId, day_number: dayNumber, notes, nickname })
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
  joinTrip(tripId, nickname) {
    const params = new URLSearchParams({ nickname })
    return api.post(`/api/trips/${tripId}/members?${params}`)
  },

  // 获取成员列表
  getMembers(tripId) {
    return api.get(`/api/trips/${tripId}/members`)
  },
}

export default api
