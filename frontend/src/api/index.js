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

  // 创建景点
  createPoi(data) {
    return api.post('/api/pois', data)
  },

  // 更新景点
  updatePoi(id, data) {
    return api.put(`/api/pois/${id}`, data)
  },

  // 删除景点
  deletePoi(id) {
    return api.delete(`/api/pois/${id}`)
  },

  // 获取地图范围内景点
  getPoisInBbox(minLng, maxLng, minLat, maxLat, filters = {}) {
    return api.get('/api/pois/bbox', {
      params: {
        min_lng: minLng,
        max_lng: maxLng,
        min_lat: minLat,
        max_lat: maxLat,
        ...filters,
      },
    })
  },
}

export default api
