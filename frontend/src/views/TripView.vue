<template>
  <div class="trip-view">
    <!-- 顶部导航栏 -->
    <div class="top-nav">
      <h1>🚗 自驾行程规划</h1>
      <div class="nav-links">
        <router-link to="/" class="nav-link">地图</router-link>
        <router-link to="/trip" class="nav-link active">我的行程</router-link>
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

    <!-- 行程信息栏 -->
    <div class="trip-info-bar" v-if="currentTrip">
      <div class="trip-info">
        <h3>{{ currentTrip.name }}</h3>
        <div class="share-info">
          <span class="share-code">分享码: <strong>{{ currentTrip.share_code }}</strong></span>
          <el-button text size="small" @click="copyShareCode">复制</el-button>
        </div>
      </div>
      <div class="trip-members">
        <el-tag v-for="member in currentTrip.members" :key="member.nickname" size="small">
          {{ member.nickname }}
        </el-tag>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-area">
      <!-- 左侧面板：景点筛选 + 已添加景点 -->
      <div class="left-panel">
        <!-- 景点筛选 -->
        <PoiFilter @filter="handleFilter" />
        
        <!-- 显示过滤复选框 -->
        <div class="filter-checkbox">
          <el-checkbox v-model="showOnlyAdded">只显示已添加景点</el-checkbox>
        </div>

        <!-- 已添加景点区域 -->
        <div class="added-pois-panel" v-if="currentTrip && currentTrip.pois.length > 0">
          <div class="panel-header" @click="addedPoisExpanded = !addedPoisExpanded">
            <span class="panel-title">
              <el-icon><LocationFilled /></el-icon>
              已添加景点 ({{ currentTrip.pois.length }})
            </span>
            <el-icon class="expand-icon" :class="{ expanded: addedPoisExpanded }">
              <ArrowDown v-if="!addedPoisExpanded" />
              <ArrowUp v-else />
            </el-icon>
          </div>
          <Transition name="collapse">
            <div class="panel-content" v-show="addedPoisExpanded">
              <div
                v-for="poi in currentTrip.pois"
                :key="poi.id"
                class="added-poi-item"
              >
                <div class="poi-item-info">
                  <span class="poi-item-name">{{ poi.name }}</span>
                </div>
                <el-button
                  text
                  size="small"
                  type="danger"
                  @click.stop="removePoi(poi.id)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </Transition>
        </div>

        <!-- 景点详情卡片 -->
        <div class="poi-card-overlay" v-if="poiStore.selectedPoi">
          <PoiCard
            :poi="poiStore.selectedPoi"
            :showAddToTrip="!!currentTrip"
            :isAdded="addedPoiIds.has(poiStore.selectedPoi.id)"
            @close="handleCloseCard"
            @add-to-trip="handleAddToTrip"
            @edit="handleEdit"
          />
        </div>
      </div>

      <!-- 地图 -->
      <div class="map-container-wrapper">
        <MapContainer
          ref="mapRef"
          :showOnlyAdded="showOnlyAdded"
          :addedPoiIds="addedPoiIds"
          @mapReady="handleMapReady"
          @markerClick="handlePoiClick"
        />
      </div>

      <!-- 右侧面板：行程规划 -->
      <div class="right-panel">
        <div class="planning-panel">
          <div class="panel-title-bar">
            <h4>行程规划面板</h4>
          </div>
          
          <div class="planning-form">
            <div class="form-item">
              <label>起点</label>
              <el-input 
                v-model="planForm.startCity" 
                placeholder="如：大同"
                clearable
              />
            </div>
            
            <div class="form-item">
              <label>终点</label>
              <el-input 
                v-model="planForm.endCity" 
                placeholder="如：郑州"
                clearable
              />
            </div>
            
            <div class="form-item">
              <label>预计天数</label>
              <el-input-number 
                v-model="planForm.days" 
                :min="1" 
                :max="30"
                controls-position="right"
              />
            </div>
            
            <div class="form-actions">
              <el-button
                type="primary"
                @click="handlePlanTrip"
                :disabled="!canPlan"
                :loading="planning"
                style="width: 100%"
              >
                规划行程
              </el-button>
              <el-button
                type="success"
                @click="handleExportTrip"
                :disabled="!hasRoute"
                :loading="exporting"
                style="width: 100%; margin-top: 10px; margin-left: 0"
              >
                导出行程
              </el-button>
            </div>
            
            <!-- 规划结果展示 -->
            <div class="plan-result" v-if="routeData && routeData.days">
              <div class="result-title">📅 行程安排</div>
              <div class="day-card" v-for="day in routeData.days" :key="day.day">
                <div class="day-header">
                  <span class="day-number">第{{ day.day }}天</span>
                </div>
                <div class="day-route">{{ day.route || '待规划' }}</div>
                <div class="day-pois" v-if="day.pois && day.pois.length">
                  <el-tag v-for="poi in day.pois" :key="poi" size="small" style="margin: 2px">{{ poi }}</el-tag>
                </div>
                <div class="day-desc" v-if="day.description">{{ day.description }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建行程对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建新行程" width="400px">
      <el-form :model="createForm">
        <el-form-item label="行程名称">
          <el-input v-model="createForm.name" placeholder="例如：五一南太行之旅" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createTrip" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 加入行程对话框 -->
    <el-dialog v-model="showJoinDialog" title="加入行程" width="400px">
      <el-form :model="joinForm">
        <el-form-item label="分享码">
          <el-input v-model="joinForm.shareCode" placeholder="输入6位分享码" maxlength="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showJoinDialog = false">取消</el-button>
        <el-button type="primary" @click="joinTrip" :loading="joining">加入</el-button>
      </template>
    </el-dialog>

    <!-- 行程详情抽屉 -->
    <el-drawer
      v-model="showTripDrawer"
      title="行程详情"
      direction="rtl"
      size="400px"
    >
      <template v-if="currentTrip">
        <div class="drawer-header">
          <div class="trip-name-row">
            <h3>{{ currentTrip.name }}</h3>
            <el-button text @click="showRenameDialog = true">
              <el-icon><Edit /></el-icon>
            </el-button>
          </div>
          <div class="share-info">
            <span class="share-code">分享码: <strong>{{ currentTrip.share_code }}</strong></span>
            <el-button text size="small" @click="copyShareCode">复制</el-button>
            <el-button text size="small" @click="copyShareLink">复制链接</el-button>
          </div>
        </div>

        <!-- 成员列表 -->
        <div class="members-section">
          <h4>成员</h4>
          <div class="member-list">
            <el-tag v-for="member in currentTrip.members" :key="member.nickname" size="small">
              {{ member.nickname }}
            </el-tag>
          </div>
        </div>

        <!-- 景点列表（按天分组） -->
        <div class="pois-section">
          <h4>已添加景点</h4>
          <div v-for="day in days" :key="day.dayNumber" class="day-group">
            <div class="day-header">
              <span>第{{ day.dayNumber }}天</span>
              <el-tag size="small">{{ day.pois.length }}个景点</el-tag>
            </div>
            <draggable
              :list="day.pois"
              group="pois"
              item-key="id"
              @end="onPoiDragEnd"
              class="poi-drag-list"
            >
              <template #item="{ element }">
                <div class="poi-drag-item">
                  <div class="poi-info">
                    <span class="poi-name">{{ element.name }}</span>
                    <el-tag v-if="element.added_by" size="small" type="info">{{ element.added_by }}</el-tag>
                  </div>
                  <el-button text size="small" @click="removePoi(element.id)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </template>
            </draggable>
          </div>

          <el-empty v-if="currentTrip.pois.length === 0" description="点击地图上的景点添加" />
        </div>

        <!-- 操作按钮 -->
        <div class="trip-actions">
          <el-button type="primary" @click="exportTrip">
            <el-icon><Download /></el-icon>
            导出行程
          </el-button>
        </div>
      </template>

      <template v-else>
        <el-empty description="创建或加入行程开始规划">
          <el-button type="primary" @click="showCreateDialog = true">创建行程</el-button>
          <el-button @click="showJoinDialog = true">加入行程</el-button>
        </el-empty>
      </template>
    </el-drawer>

    <!-- 底部浮动按钮 -->
    <div class="floating-actions">
      <el-button type="primary" circle @click="showTripDrawer = true" v-if="currentTrip">
        <el-icon><List /></el-icon>
      </el-button>
      <el-button type="primary" @click="showCreateDialog = true" v-else>
        <el-icon><Plus /></el-icon>
        创建行程
      </el-button>
    </div>

    <!-- 重命名对话框 -->
    <el-dialog v-model="showRenameDialog" title="修改行程名称" width="400px">
      <el-input v-model="newName" placeholder="输入新名称" />
      <template #footer>
        <el-button @click="showRenameDialog = false">取消</el-button>
        <el-button type="primary" @click="renameTrip">确定</el-button>
      </template>
    </el-dialog>

    <!-- 规划进度对话框 -->
    <el-dialog 
      v-model="showPlanDialog" 
      title="行程规划中..." 
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="plan-progress">
        <el-progress :percentage="planProgress" :format="() => planProgressText" />
        <div class="progress-steps">
          <div class="step" :class="{ active: planStep >= 1, done: planStep > 1 }">
            <el-icon v-if="planStep > 1"><Check /></el-icon>
            <span v-else>1</span>
            获取景点坐标
          </div>
          <div class="step" :class="{ active: planStep >= 2, done: planStep > 2 }">
            <el-icon v-if="planStep > 2"><Check /></el-icon>
            <span v-else>2</span>
            计算路线距离
          </div>
          <div class="step" :class="{ active: planStep >= 3, done: planStep > 3 }">
            <el-icon v-if="planStep > 3"><Check /></el-icon>
            <span v-else>3</span>
            AI 规划行程
          </div>
          <div class="step" :class="{ active: planStep >= 4 }">
            <el-icon v-if="planStep >= 4"><Check /></el-icon>
            <span v-else>4</span>
            生成结果
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Link, Edit, Delete, Download, Refresh, Loading, List, ArrowDown, ArrowUp, LocationFilled, Check } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import MapContainer from '@/components/MapContainer.vue'
import PoiFilter from '@/components/PoiFilter.vue'
import PoiCard from '@/components/PoiCard.vue'
import { usePoiStore } from '../stores/poi'
import { useUserStore } from '../stores/user'
import { tripApi } from '@/api'

const route = useRoute()
const router = useRouter()
const poiStore = usePoiStore()
const userStore = useUserStore()

// 状态
const showCreateDialog = ref(false)
const showJoinDialog = ref(false)
const showRenameDialog = ref(false)
const showTripDrawer = ref(false)
const addedPoisExpanded = ref(true) // 已添加景点面板默认展开

const creating = ref(false)
const joining = ref(false)

const createForm = ref({ name: '' })
const joinForm = ref({ shareCode: '' })
const newName = ref('')

// 行程规划表单
const planForm = ref({
  startCity: '',
  endCity: '',
  days: 3
})

// 规划状态
const planning = ref(false)
const exporting = ref(false)
const routeData = ref(null)

// 规划进度
const showPlanDialog = ref(false)
const planProgress = ref(0)
const planProgressText = ref('准备中...')
const planStep = ref(0)

// localStorage 存储相关
const getPlanStorageKey = (tripId) => `trip_plan_info_${tripId}`

const savePlanToLocalStorage = () => {
  if (!currentTrip.value) return
  const key = getPlanStorageKey(currentTrip.value.trip_id)
  localStorage.setItem(key, JSON.stringify({
    startCity: planForm.value.startCity,
    endCity: planForm.value.endCity,
    days: planForm.value.days
  }))
}

const loadPlanFromLocalStorage = (tripId) => {
  const key = getPlanStorageKey(tripId)
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      const data = JSON.parse(saved)
      planForm.value.startCity = data.startCity || ''
      planForm.value.endCity = data.endCity || ''
      planForm.value.days = data.days || 3
    } catch (e) {
      console.error('Failed to load plan from localStorage:', e)
    }
  }
}

// 监听表单变化，自动保存到 localStorage
watch(
  () => planForm.value,
  () => {
    if (currentTrip.value) {
      savePlanToLocalStorage()
    }
  },
  { deep: true }
)

const currentTrip = ref(null)
const mapRef = ref(null)
const mapReady = ref(false)
const showOnlyAdded = ref(false) // 只显示已添加景点

// 计算属性
const days = computed(() => {
  if (!currentTrip.value) return []

  const dayMap = {}
  currentTrip.value.pois.forEach(poi => {
    const day = poi.day_number || 1
    if (!dayMap[day]) {
      dayMap[day] = { dayNumber: day, pois: [] }
    }
    dayMap[day].pois.push(poi)
  })

  return Object.values(dayMap).sort((a, b) => a.dayNumber - b.dayNumber)
})

// 已添加景点的 ID 集合
const addedPoiIds = computed(() => {
  if (!currentTrip.value) return new Set()
  return new Set(currentTrip.value.pois.map(p => p.id))
})

// 是否可以规划行程
const canPlan = computed(() => {
  return planForm.value.startCity && planForm.value.endCity && planForm.value.days > 0 && currentTrip.value && currentTrip.value.pois.length > 0
})

// 是否已有路线
const hasRoute = computed(() => {
  return routeData.value !== null
})

// 地图相关方法
const handleMapReady = (map) => {
  mapReady.value = true
  console.log('Map is ready')
}

const handleFilter = async () => {
  if (mapRef.value && mapReady.value) {
    mapRef.value.refreshPoisInBounds()
  } else {
    await poiStore.fetchPois()
  }
}

const refreshPois = () => {
  if (mapRef.value && mapReady.value) {
    mapRef.value.refreshPoisInBounds()
  } else {
    poiStore.fetchPois()
  }
}

const handlePoiClick = (poi) => {
  poiStore.selectPoi(poi)
  if (mapRef.value && poi.longitude && poi.latitude) {
    mapRef.value.panTo(poi.longitude, poi.latitude)
  }
}

const handleCloseCard = () => {
  poiStore.clearSelection()
}

const handleEdit = (poi) => {
  console.log('Edit poi:', poi)
}

// 行程规划
async function handlePlanTrip() {
  if (!canPlan.value) {
    ElMessage.warning('请填写起点、终点并添加景点')
    return
  }

  planning.value = true
  showPlanDialog.value = true
  planProgress.value = 0
  planStep.value = 0
  planProgressText.value = '准备中...'

  try {
    // 步骤1：获取坐标
    planStep.value = 1
    planProgress.value = 20
    planProgressText.value = '获取景点坐标...'
    await new Promise(r => setTimeout(r, 500))

    // 步骤2：计算距离
    planStep.value = 2
    planProgress.value = 40
    planProgressText.value = '计算路线距离...'
    await new Promise(r => setTimeout(r, 500))

    // 步骤3：AI规划
    planStep.value = 3
    planProgress.value = 60
    planProgressText.value = 'AI 正在规划最佳路线...'
    
    const result = await tripApi.planTrip(
      currentTrip.value.trip_id,
      planForm.value.startCity,
      planForm.value.endCity,
      planForm.value.days
    )

    // 步骤4：生成结果
    planStep.value = 4
    planProgress.value = 100
    planProgressText.value = '规划完成！'

    // 保存规划结果
    routeData.value = result.route

    // 在地图上绘制路线
    if (mapRef.value && result.route) {
      mapRef.value.drawRoute(result.route)
    }

    await new Promise(r => setTimeout(r, 500))
    showPlanDialog.value = false
    ElMessage.success('行程规划完成！')
  } catch (error) {
    showPlanDialog.value = false
    ElMessage.error('规划失败: ' + (error.message || '未知错误'))
  } finally {
    planning.value = false
  }
}

// 加入行程
async function handleAddToTrip(poi) {
  if (!currentTrip.value) {
    ElMessage.warning('请先创建或加入行程')
    showCreateDialog.value = true
    return
  }
  
  try {
    await tripApi.addPoi(
      currentTrip.value.trip_id,
      poi.id,
      1 // 默认第一天
    )
    
    // 重新加载行程
    await loadTrip(currentTrip.value.trip_id)
    ElMessage.success('已添加到行程')
  } catch (error) {
    if (error.message && error.message.includes('已在行程中')) {
      ElMessage.warning('景点已在行程中')
    } else {
      ElMessage.error('添加失败: ' + (error.message || '未知错误'))
    }
  }
}

// 行程相关方法
async function createTrip() {
  creating.value = true
  try {
    const trip = await tripApi.createTrip(
      createForm.value.name || '未命名行程'
    )
    currentTrip.value = trip
    showCreateDialog.value = false
    createForm.value.name = ''

    router.push(`/trip/${trip.trip_id}`)

    ElMessage.success('创建成功！分享码: ' + trip.share_code)
  } catch (error) {
    ElMessage.error('创建失败: ' + error.message)
  } finally {
    creating.value = false
  }
}

async function joinTrip() {
  if (!joinForm.value.shareCode) {
    ElMessage.warning('请输入分享码')
    return
  }
  
  joining.value = true
  try {
    const { trip_id } = await tripApi.getTripByCode(joinForm.value.shareCode)
    
    await tripApi.joinTrip(trip_id)
    
    const trip = await tripApi.getTrip(trip_id)
    currentTrip.value = trip
    
    showJoinDialog.value = false
    joinForm.value = { shareCode: '' }
    
    router.push(`/trip/${trip_id}`)
    
    ElMessage.success('加入成功！')
  } catch (error) {
    ElMessage.error('加入失败: ' + error.message)
  } finally {
    joining.value = false
  }
}

async function loadTrip(tripId) {
  try {
    const trip = await tripApi.getTrip(tripId)
    currentTrip.value = trip
    
    if (mapRef.value && trip.pois.length > 0) {
      mapRef.value.highlightPois(trip.pois.map(p => p.id))
    }
    
    // 从 localStorage 恢复规划信息
    loadPlanFromLocalStorage(tripId)
    
    // 获取已规划的路线
    try {
      const routeResult = await tripApi.getRoute(tripId)
      if (routeResult.route && routeResult.route.data) {
        routeData.value = routeResult.route.data
        
        // 恢复规划表单
        planForm.value.startCity = routeResult.route.start_city || ''
        planForm.value.endCity = routeResult.route.end_city || ''
        planForm.value.days = routeResult.route.total_days || 3
        
        // 地图上绘制路线
        if (mapRef.value && routeResult.route.data) {
          // 等地图加载完成
          setTimeout(() => {
            mapRef.value.drawRoute(routeResult.route.data)
          }, 500)
        }
      }
    } catch (e) {
      // 没有路线数据，忽略
    }
  } catch (error) {
    ElMessage.error('加载行程失败')
    router.push('/trip')
  }
}

async function removePoi(poiId) {
  try {
    await tripApi.removePoi(currentTrip.value.trip_id, poiId)
    await loadTrip(currentTrip.value.trip_id)
    ElMessage.success('移除成功')
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

async function renameTrip() {
  if (!newName.value) return
  
  try {
    await tripApi.updateTrip(currentTrip.value.trip_id, newName.value)
    currentTrip.value.name = newName.value
    showRenameDialog.value = false
    ElMessage.success('修改成功')
  } catch (error) {
    ElMessage.error('修改失败')
  }
}

function copyShareLink() {
  const link = `${window.location.origin}/trip/${currentTrip.value.trip_id}`
  const text = `分享码: ${currentTrip.value.share_code}\n链接: ${link}`
  navigator.clipboard.writeText(text)
  ElMessage.success(`分享码 ${currentTrip.value.share_code} 已复制！`)
}

function copyShareCode() {
  navigator.clipboard.writeText(currentTrip.value.share_code)
  ElMessage.success(`分享码 ${currentTrip.value.share_code} 已复制！`)
}

async function exportTrip() {
  if (!currentTrip.value || !routeData.value) {
    ElMessage.warning('请先规划行程')
    return
  }

  exporting.value = true
  try {
    const result = await tripApi.exportTrip(currentTrip.value.trip_id)

    if (result.url) {
      window.open(result.url, '_blank')
      ElMessage.success('导出成功！')
    } else if (result.preview) {
      // 如果没有生成文档链接，显示预览
      ElMessage.info(result.message || '导出预览')
      console.log('导出预览:', result.preview)
    }
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.message || '未知错误'))
  } finally {
    exporting.value = false
  }
}

function onPoiDragEnd() {
  // TODO: 调用 API 更新顺序
}

// 用户命令处理
function handleUserCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

// 生命周期
onMounted(async () => {
  // 加载景点数据
  await poiStore.fetchPois()
  
  // 从 URL 加载行程
  if (route.params.tripId) {
    loadTrip(route.params.tripId)
  }
  
  // 从 URL 参数读取分享码
  if (route.query.code) {
    joinForm.value.shareCode = route.query.code
    showJoinDialog.value = true
  }
})
</script>

<style scoped>
.trip-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
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

.nav-link.active {
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

/* 行程信息栏 */
.trip-info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: white;
  border-bottom: 1px solid #eee;
}

.trip-info-bar .trip-info h3 {
  margin: 0;
  font-size: 16px;
}

.trip-info-bar .trip-info .share-info {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.trip-info-bar .trip-info .share-code strong {
  color: #409eff;
}

.trip-info-bar .trip-members {
  display: flex;
  align-items: center;
  gap: 5px;
}

/* 主内容区 */
.content-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧面板：景点筛选 + 已添加景点 */
.left-panel {
  width: 15%;
  min-width: 200px;
  max-width: 280px;
  background: white;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

/* 显示过滤复选框 */
.filter-checkbox {
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
}

/* 已添加景点面板 */
.added-pois-panel {
  background: white;
  border-bottom: 1px solid #eee;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  cursor: pointer;
  user-select: none;
}

.panel-header:hover {
  background: #f5f7fa;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  font-size: 14px;
}

.expand-icon {
  transition: transform 0.3s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.panel-content {
  padding: 0 15px 10px;
  max-height: 200px;
  overflow-y: auto;
}

.added-poi-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 6px;
}

.added-poi-item:last-child {
  margin-bottom: 0;
}

.added-poi-item .poi-item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.added-poi-item .poi-item-name {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 折叠动画 */
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  opacity: 0;
}

/* 地图容器 */
.map-container-wrapper {
  flex: 1;
  position: relative;
}

/* 右侧面板：行程规划 */
.right-panel {
  width: 12%;
  min-width: 180px;
  max-width: 240px;
  background: white;
  border-left: 1px solid #eee;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

/* 行程规划面板 */
.planning-panel {
  padding: 15px;
}

.panel-title-bar {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.panel-title-bar h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.planning-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.form-item :deep(.el-input-number) {
  width: 100%;
}

.form-actions {
  margin-top: 10px;
}

.form-actions .el-button {
  width: 100%;
}

/* 规划结果展示 */
.plan-result {
  margin-top: 20px;
  border-top: 1px solid #eee;
  padding-top: 15px;
}

.result-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.day-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
}

.day-card .day-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.day-card .day-number {
  font-weight: 600;
  color: #409eff;
  font-size: 13px;
}

.day-card .day-route {
  font-size: 12px;
  color: #606266;
  margin-bottom: 6px;
}

.day-card .day-pois {
  margin-bottom: 6px;
}

.day-card .day-desc {
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}

/* 规划进度对话框 */
.plan-progress {
  text-align: center;
}

.plan-progress .el-progress {
  margin-bottom: 30px;
}

.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 15px;
  text-align: left;
}

.progress-steps .step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #c0c4cc;
  transition: all 0.3s;
}

.progress-steps .step.active {
  color: #409eff;
}

.progress-steps .step.done {
  color: #67c23a;
}

.progress-steps .step .el-icon {
  font-size: 18px;
}

.progress-steps .step span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e4e7ed;
  color: #fff;
  font-size: 12px;
}

.progress-steps .step.active span {
  background: #409eff;
}

.progress-steps .step.done span {
  background: #67c23a;
}

/* 景点详情卡片 */
.poi-card-overlay {
  padding: 10px;
}

/* 浮动按钮 */
.floating-actions {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 200;
}

/* 抽屉样式 */
.drawer-header {
  margin-bottom: 20px;
}

.trip-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trip-name-row h3 {
  margin: 0;
}

.members-section {
  margin-bottom: 20px;
}

.members-section h4 {
  margin-bottom: 10px;
  font-size: 14px;
  color: #606266;
}

.member-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pois-section {
  flex: 1;
}

.pois-section h4 {
  margin-bottom: 15px;
  font-size: 14px;
  color: #606266;
}

.day-group {
  margin-bottom: 15px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 500;
}

.poi-drag-list {
  min-height: 50px;
}

.poi-drag-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: white;
  border-radius: 4px;
  margin-bottom: 5px;
  cursor: move;
  border: 1px solid #eee;
}

.poi-drag-item .poi-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.poi-drag-item .poi-name {
  font-size: 14px;
}

.trip-actions {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}
</style>
