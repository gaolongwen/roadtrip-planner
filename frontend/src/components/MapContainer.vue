<template>
  <div id="map-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { usePoiStore } from '../stores/poi'

// 配置高德地图安全密钥
window._AMapSecurityConfig = {
  securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE || '',
}

const emit = defineEmits(['mapReady', 'markerClick'])

const poiStore = usePoiStore()
const map = ref(null)
const markers = ref([])
const AMap = ref(null)
let debounceTimer = null

// 初始化地图
const initMap = async () => {
  try {
    const amapInstance = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_KEY || 'your_amap_key_here',
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.ToolBar'],
    })
    
    AMap.value = amapInstance
    
    map.value = new amapInstance.Map('map-container', {
      zoom: 8,
      center: [113.5, 35.5],
      mapStyle: 'amap://styles/normal',
    })
    
    map.value.addControl(new amapInstance.Scale())
    map.value.addControl(new amapInstance.ToolBar())
    
    // 防抖刷新
    map.value.on('moveend', debounceRefresh)
    map.value.on('zoomend', debounceRefresh)
    
    emit('mapReady', map.value)
  } catch (error) {
    console.error('地图初始化失败:', error)
  }
}

// 防抖刷新（300ms）
const debounceRefresh = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    refreshPoisInBounds()
  }, 300)
}

// 刷新可见范围内的景点
const refreshPoisInBounds = async () => {
  if (!map.value) return
  
  const bounds = map.value.getBounds()
  const southWest = bounds.getSouthWest()
  const northEast = bounds.getNorthEast()
  
  await poiStore.fetchPoisInBbox(
    southWest.lng,
    northEast.lng,
    southWest.lat,
    northEast.lat
  )
}

// 批量添加标记（性能优化）
const addMarkers = (pois) => {
  if (!AMap.value || !map.value) return
  
  // 清除旧标记
  markers.value.forEach(marker => marker.setMap(null))
  markers.value = []
  
  if (!pois.length) return
  
  // 过滤有效坐标
  const validPois = pois.filter(poi => poi.longitude && poi.latitude)
  if (!validPois.length) return
  
  // 批量创建标记
  const newMarkers = validPois.map(poi => {
    const marker = new AMap.value.Marker({
      position: [poi.longitude, poi.latitude],
      title: poi.name,
      content: `<div class="custom-marker"><span>${poi.name}</span></div>`,
      offset: new AMap.value.Pixel(-30, -12),
    })
    
    marker.on('click', () => {
      poiStore.selectPoi(poi)
      emit('markerClick', poi)
    })
    
    return marker
  })
  
  // 批量添加到地图
  map.value.add(newMarkers)
  markers.value = newMarkers
}

// 监听景点数据变化
watch(() => poiStore.pois, (newPois) => {
  addMarkers(newPois)
}, { deep: true })

// 定位到指定景点
const panTo = (lng, lat) => {
  if (map.value) {
    map.value.panTo([lng, lat])
  }
}

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (map.value) {
    map.value.destroy()
  }
})

defineExpose({
  panTo,
  refreshPoisInBounds,
})
</script>

<style>
#map-container {
  width: 100%;
  height: 100%;
}

.custom-marker {
  background: rgba(64, 158, 255, 0.4);
  color: white;
  padding: 3px 6px;
  border-radius: 3px;
  font-size: 11px;
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.custom-marker::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: rgba(64, 158, 255, 0.4);
}
</style>
