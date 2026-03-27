<template>
  <div class="main-container">
    <!-- 顶部导航栏 -->
    <div class="top-nav">
      <h1>🚗 自驾行程规划</h1>
      <div class="nav-links">
        <router-link to="/" class="nav-link">地图</router-link>
        <router-link to="/trip" class="nav-link">我的行程</router-link>
        <template v-if="userStore.isLoggedIn">
          <el-dropdown @command="handleUserCommand">
            <span class="user-dropdown">
              {{ userStore.nickname || '用户' }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <router-link v-else to="/login" class="nav-link">登录</router-link>
      </div>
    </div>
    
    <div class="content-area">
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
                <el-tag v-if="poi.is_wild" type="warning" size="small">野生</el-tag>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePoiStore } from '../stores/poi'
import { useUserStore } from '../stores/user'
import { Refresh, Loading, ArrowDown } from '@element-plus/icons-vue'
import MapContainer from '../components/MapContainer.vue'
import PoiCard from '../components/PoiCard.vue'
import PoiFilter from '../components/PoiFilter.vue'

const router = useRouter()
const poiStore = usePoiStore()
const userStore = useUserStore()
const mapRef = ref(null)
const mapReady = ref(false)

// 处理地图就绪
const handleMapReady = (map) => {
  mapReady.value = true
  console.log('Map is ready')
}

// 处理筛选
const handleFilter = async () => {
  // 如果地图已就绪，刷新地图范围内的景点（带筛选）
  if (mapRef.value && mapReady.value) {
    mapRef.value.refreshPoisInBounds()
  } else {
    // 否则直接获取景点列表
    await poiStore.fetchPois()
  }
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

// 用户命令处理
const handleUserCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

onMounted(() => {
  // 初始加载景点
  poiStore.fetchPois()
})
</script>

<style scoped>
.main-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: white;
  border-bottom: 1px solid #eee;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.top-nav h1 {
  margin: 0;
  font-size: 18px;
}

.nav-links {
  display: flex;
  gap: 15px;
}

.nav-link {
  color: #606266;
  text-decoration: none;
  padding: 5px 10px;
  border-radius: 4px;
}

.nav-link:hover {
  background: #f5f7fa;
}

.nav-link.router-link-active {
  color: #409eff;
  background: #ecf5ff;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  color: #606266;
}

.user-dropdown:hover {
  background: #f5f7fa;
}

.content-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  width: 320px;
  background: white;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
}

.poi-list {
  flex: 1;
  overflow-y: auto;
}

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

.poi-list-item {
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.poi-list-item:hover {
  background: #f5f7fa;
}

.poi-list-item.active {
  background: #ecf5ff;
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

.right-panel {
  flex: 1;
  position: relative;
}

.poi-card-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 100;
}
</style>
