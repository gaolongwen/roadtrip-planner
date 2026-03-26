<template>
  <div class="main-container">
    <!-- 左侧面板 -->
    <div class="left-panel">
      <PoiFilter @filter="handleFilter" />
      
      <div class="poi-list">
        <div class="list-header">
          <span>景点列表 ({{ poiStore.pois.length }})</span>
          <el-button type="primary" size="small" @click="refreshPois">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
        
        <div v-if="poiStore.loading" class="loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        
        <div v-else-if="poiStore.pois.length === 0" class="empty">
          <el-empty description="暂无景点数据" :image-size="80" />
        </div>
        
        <div v-else>
          <div 
            v-for="poi in poiStore.pois" 
            :key="poi.id"
            :class="['poi-list-item', { active: poiStore.selectedPoi?.id === poi.id }]"
            @click="handlePoiClick(poi)"
          >
            <div class="poi-item-header">
              <span class="poi-item-name">{{ poi.name }}</span>
              <el-tag v-if="poi.isWild" type="warning" size="small">野生</el-tag>
            </div>
            <div class="poi-item-address">{{ poi.address || '暂无地址' }}</div>
            <div class="poi-item-meta">
              <el-tag size="small" type="info">{{ poi.category || '未分类' }}</el-tag>
              <span v-if="poi.rating" class="poi-item-rating">
                ⭐ {{ poi.rating }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 右侧地图 -->
    <div class="right-panel">
      <MapContainer 
        ref="mapRef"
        @mapReady="handleMapReady"
        @markerClick="handlePoiClick"
      />
      
      <!-- 景点详情卡片 -->
      <div class="poi-card-overlay" v-if="poiStore.selectedPoi">
        <PoiCard 
          :poi="poiStore.selectedPoi"
          @close="handleCloseCard"
          @navigate="handleNavigate"
          @edit="handleEdit"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePoiStore } from '../stores/poi'
import MapContainer from '../components/MapContainer.vue'
import PoiCard from '../components/PoiCard.vue'
import PoiFilter from '../components/PoiFilter.vue'

const poiStore = usePoiStore()
const mapRef = ref(null)
const mapReady = ref(false)

// 处理地图就绪
const handleMapReady = (map) => {
  mapReady.value = true
  console.log('Map is ready')
}

// 处理筛选
const handleFilter = async () => {
  await poiStore.fetchPois()
}

// 刷新景点列表
const refreshPois = () => {
  if (mapRef.value && mapReady.value) {
    mapRef.value.refreshPoisInBounds()
  } else {
    poiStore.fetchPois()
  }
}

// 点击景点
const handlePoiClick = (poi) => {
  poiStore.selectPoi(poi)
  if (mapRef.value && poi.longitude && poi.latitude) {
    mapRef.value.panTo(poi.longitude, poi.latitude)
  }
}

// 关闭详情卡片
const handleCloseCard = () => {
  poiStore.clearSelection()
}

// 导航
const handleNavigate = (poi) => {
  if (poi.longitude && poi.latitude) {
    // 打开高德地图导航
    const url = `https://uri.amap.com/navigation?to=${poi.longitude},${poi.latitude},${poi.name}&mode=car&policy=1&src=roadtrip-planner`
    window.open(url, '_blank')
  }
}

// 编辑景点
const handleEdit = (poi) => {
  console.log('Edit poi:', poi)
  // TODO: 实现编辑功能
}

onMounted(() => {
  // 初始加载景点
  poiStore.fetchPois()
})
</script>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #eee;
  font-weight: 500;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
  gap: 10px;
}

.empty {
  padding: 20px;
}

.poi-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.poi-item-name {
  font-weight: 500;
  font-size: 14px;
}

.poi-item-address {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.poi-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.poi-item-rating {
  font-size: 12px;
  color: #ff9900;
}
</style>
