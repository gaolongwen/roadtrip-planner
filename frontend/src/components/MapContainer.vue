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
      center: [113.5, 35.5], // 河南省中心点
      mapStyle: 'amap://styles/normal',
    })
    
    // 添加控件
    map.value.addControl(new amapInstance.Scale())
    map.value.addControl(new amapInstance.ToolBar())
    
    // 地图移动结束后刷新景点
    map.value.on('moveend', () => {
      refreshPoisInBounds()
    })
    
    map.value.on('zoomend', () => {
      refreshPoisInBounds()
    })
    
    emit('mapReady', map.value)
  } catch (error) {
    console.error('地图初始化失败:', error)
  }
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

// 添加标记点
const addMarkers = (pois) => {
  // 清除旧标记
  markers.value.forEach(marker => marker.setMap(null))
  markers.value = []
  
  if (!AMap.value || !map.value) return
  
  pois.forEach(poi => {
    if (!poi.longitude || !poi.latitude) return
    
    const marker = new AMap.value.Marker({
      position: [poi.longitude, poi.latitude],
      title: poi.name,
      content: `<div class="custom-marker"><span>${poi.name}</span></div>`,
    })
    
    marker.on('click', () => {
      poiStore.selectPoi(poi)
      emit('markerClick', poi)
    })
    
    marker.setMap(map.value)
    markers.value.push(marker)
  })
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
  if (map.value) {
    map.value.destroy()
  }
})

// 暴露方法给父组件
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
  background: rgba(64, 158, 255, 0.65);
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
  border-top-color: rgba(64, 158, 255, 0.65);
}
</style>
