import { defineStore } from 'pinia'
import { ref } from 'vue'
import { poiApi } from '../api'

export const usePoiStore = defineStore('poi', () => {
  // 状态
  const pois = ref([])
  const selectedPoi = ref(null)
  const loading = ref(false)
  const filters = ref({
    nature: ['正规', '野生'],
    category: ['人文', '自然'],
    tags: [],
  })

  // 获取景点列表
  async function fetchPois(params = {}) {
    loading.value = true
    try {
      const filterParams = {}
      
      // 景点性质筛选
      if (filters.value.nature && filters.value.nature.length > 0 && filters.value.nature.length < 2) {
        filterParams.wild_filter = filters.value.nature.join(',')
      }
      
      // 类别筛选
      if (filters.value.category && filters.value.category.length > 0 && filters.value.category.length < 2) {
        filterParams.categories = filters.value.category.join(',')
      }
      
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
      nature: ['正规', '野生'],
      category: ['人文', '自然'],
      tags: [],
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
