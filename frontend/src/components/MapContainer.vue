<template>
  <div id="map-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { usePoiStore } from '../stores/poi'

// 配置高德地图安全密钥
window._AMapSecurityConfig = {
  securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE || '',
}

const props = defineProps({
  showOnlyAdded: {
    type: Boolean,
    default: false
  },
  addedPoiIds: {
    type: Set,
    default: () => new Set()
  }
})

const emit = defineEmits(['mapReady', 'markerClick', 'poi-click', 'poi-add'])

const poiStore = usePoiStore()
const map = ref(null)
const markers = ref([])
const AMap = ref(null)
let debounceTimer = null
const routePolylines = ref([]) // 路线
const routeMarkers = ref([]) // 路线上的标注

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
  let validPois = pois.filter(poi => poi.longitude && poi.latitude)
  
  // 如果开启只显示已添加景点，则过滤
  if (props.showOnlyAdded && props.addedPoiIds.size > 0) {
    validPois = validPois.filter(poi => props.addedPoiIds.has(poi.id))
  }
  
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

// 监听过滤条件变化
watch([() => props.showOnlyAdded, () => props.addedPoiIds], () => {
  addMarkers(poiStore.pois)
}, { deep: true })

// 定位到指定景点
const panTo = (lng, lat) => {
  if (map.value) {
    map.value.panTo([lng, lat])
  }
}

// 高亮选中的景点
const highlightPois = (poiIds) => {
  // TODO: 实现高亮逻辑
  console.log('Highlight POIs:', poiIds)
}

// 绘制路线（带箭头）
const drawRoute = (routeData) => {
  if (!AMap.value || !map.value || !routeData) return

  // 清除旧路线
  clearRoute()

  const days = routeData.days || []
  const poiCoords = routeData.poi_coords || {}
  const startCoord = routeData.start_coord
  const endCoord = routeData.end_coord

  // 为每天绘制路线
  days.forEach((day, dayIndex) => {
    const points = []
    const poiNames = day.pois || []

    // 添加起点（只有第一天）
    if (dayIndex === 0 && startCoord) {
      points.push([startCoord.lng, startCoord.lat])
    }

    // 添加当天景点
    poiNames.forEach(name => {
      const coord = poiCoords[name]
      if (coord) {
        points.push([coord.lng, coord.lat])
      }
    })

    // 添加终点（最后一天）
    if (dayIndex === days.length - 1 && endCoord) {
      points.push([endCoord.lng, endCoord.lat])
    }

    if (points.length < 2) return

    // 绘制带箭头的线
    const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
    const color = colors[dayIndex % colors.length]

    const polyline = new AMap.value.Polyline({
      path: points,
      strokeColor: color,
      strokeWeight: 5,
      strokeStyle: 'solid',
      showDir: true, // 显示箭头
      lineJoin: 'round',
      lineCap: 'round',
    })

    map.value.add(polyline)
    routePolylines.value.push(polyline)

    // 在每段线中点添加标注
    for (let i = 0; i < points.length - 1; i++) {
      const midPoint = [
        (points[i][0] + points[i + 1][0]) / 2,
        (points[i][1] + points[i + 1][1]) / 2
      ]

      // 添加日期标签
      if (i === 0) {
        const startMarker = new AMap.value.Text({
          text: `D${day.day}`,
          position: points[0],
          style: {
            'background-color': color,
            'color': '#fff',
            'border': 'none',
            'padding': '4px 8px',
            'font-size': '12px',
            'font-weight': 'bold',
            'border-radius': '4px',
          },
          offset: new AMap.value.Pixel(0, -20),
        })
        map.value.add(startMarker)
        routeMarkers.value.push(startMarker)
      }

      // 添加景点名称
      if (i < poiNames.length) {
        const poiMarker = new AMap.value.Text({
          text: poiNames[i],
          position: points[i + 1],
          style: {
            'background-color': '#fff',
            'color': color,
            'border': `2px solid ${color}`,
            'padding': '2px 6px',
            'font-size': '11px',
            'border-radius': '4px',
          },
          offset: new AMap.value.Pixel(0, -15),
        })
        map.value.add(poiMarker)
        routeMarkers.value.push(poiMarker)
      }
    }
  })

  // 调整视野包含所有路线
  if (routePolylines.value.length > 0) {
    map.value.setFitView(routePolylines.value, false, [50, 50, 50, 50])
  }
}

// 清除路线
const clearRoute = () => {
  routePolylines.value.forEach(polyline => polyline.setMap(null))
  routeMarkers.value.forEach(marker => marker.setMap(null))
  routePolylines.value = []
  routeMarkers.value = []
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
  highlightPois,
  drawRoute,
  clearRoute,
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
