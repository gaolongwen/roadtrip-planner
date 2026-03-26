import { defineStore } from 'pinia'
import { ref } from 'vue'
import { poiApi } from '../api'

export const usePoiStore = defineStore('poi', () => {
  // 状态
  const pois = ref([])
  const selectedPoi = ref(null)
  const loading = ref(false)
  const filters = ref({
    province: '',
    city: '',
    type: '',
    isWild: false,
  })

  // 获取景点列表
  async function fetchPois(params = {}) {
    loading.value = true
    try {
      // 过滤掉空参数
      const filterParams = {}
      if (filters.value.province) filterParams.province = filters.value.province
      if (filters.value.city) filterParams.city = filters.value.city
      if (filters.value.type) filterParams.category = filters.value.type
      if (filters.value.isWild) filterParams.is_wild = true
      
      const data = await poiApi.getPois({ ...filterParams, ...params })
      pois.value = data.items || data || []
      return data
    } catch (error) {
      console.error('Failed to fetch pois:', error)
      pois.value = []
    } finally {
      loading.value = false
    }
  }

  // 获取地图范围内景点
  async function fetchPoisInBbox(minLng, maxLng, minLat, maxLat) {
    loading.value = true
    try {
      const data = await poiApi.getPoisInBbox(minLng, maxLng, minLat, maxLat)
      pois.value = data || []
      return data
    } catch (error) {
      console.error('Failed to fetch pois in bbox:', error)
      pois.value = []
    } finally {
      loading.value = false
    }
  }

  // 选择景点
  function selectPoi(poi) {
    selectedPoi.value = poi
  }

  // 取消选择
  function clearSelection() {
    selectedPoi.value = null
  }

  // 设置筛选条件
  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
  }

  // 重置筛选条件
  function resetFilters() {
    filters.value = {
      province: '',
      city: '',
      type: '',
      isWild: false,
    }
  }

  return {
    pois,
    selectedPoi,
    loading,
    filters,
    fetchPois,
    fetchPoisInBbox,
    selectPoi,
    clearSelection,
    setFilters,
    resetFilters,
  }
})
