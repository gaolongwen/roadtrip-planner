<template>
  <div class="trip-view">
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
        <el-form-item label="你的昵称">
          <el-input v-model="joinForm.nickname" placeholder="大家怎么称呼你" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showJoinDialog = false">取消</el-button>
        <el-button type="primary" @click="joinTrip" :loading="joining">加入</el-button>
      </template>
    </el-dialog>

    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建行程
      </el-button>
      <el-button @click="showJoinDialog = true">
        <el-icon><Link /></el-icon>
        加入行程
      </el-button>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：地图 -->
      <div class="map-section">
        <MapContainer
          ref="mapRef"
          @poi-click="handlePoiClick"
          @poi-add="handlePoiAdd"
        />
      </div>

      <!-- 右侧：行程面板 -->
      <div class="trip-panel">
        <el-card v-if="!currentTrip" class="empty-trip">
          <el-empty description="创建或加入行程开始规划">
            <el-button type="primary" @click="showCreateDialog = true">创建行程</el-button>
          </el-empty>
        </el-card>

        <el-card v-else class="trip-card">
          <template #header>
            <div class="trip-header">
              <div>
                <h3>{{ currentTrip.name }}</h3>
                <div class="share-info">
                  <span class="share-code">分享码: <strong>{{ currentTrip.share_code }}</strong></span>
                  <el-button text size="small" @click="copyShareLink">复制链接</el-button>
                </div>
              </div>
              <el-button text @click="showRenameDialog = true">
                <el-icon><Edit /></el-icon>
              </el-button>
            </div>
          </template>

          <!-- 成员列表 -->
          <div class="members-section">
            <el-tag v-for="member in currentTrip.members" :key="member.nickname" size="small">
              {{ member.nickname }}
            </el-tag>
            <el-button text size="small" @click="showNicknameDialog = true">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>

          <!-- 景点列表（按天分组） -->
          <div class="pois-section">
            <div v-for="day in days" :key="day.dayNumber" class="day-group">
              <div class="day-header">
                <h4>第{{ day.dayNumber }}天</h4>
                <el-tag size="small">{{ day.pois.length }}个景点</el-tag>
              </div>
              <draggable
                :list="day.pois"
                group="pois"
                item-key="id"
                @end="onPoiDragEnd"
                class="poi-list"
              >
                <template #item="{ element }">
                  <div class="poi-item">
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
        </el-card>
      </div>
    </div>

    <!-- 重命名对话框 -->
    <el-dialog v-model="showRenameDialog" title="修改行程名称" width="400px">
      <el-input v-model="newName" placeholder="输入新名称" />
      <template #footer>
        <el-button @click="showRenameDialog = false">取消</el-button>
        <el-button type="primary" @click="renameTrip">确定</el-button>
      </template>
    </el-dialog>

    <!-- 设置昵称对话框 -->
    <el-dialog v-model="showNicknameDialog" title="设置昵称" width="400px">
      <el-input v-model="nickname" placeholder="你的昵称" />
      <template #footer>
        <el-button @click="showNicknameDialog = false">取消</el-button>
        <el-button type="primary" @click="setNickname">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import draggable from 'vuedraggable'
import MapContainer from '@/components/MapContainer.vue'
import { tripApi } from '@/api'

const route = useRoute()
const router = useRouter()

// 状态
const showCreateDialog = ref(false)
const showJoinDialog = ref(false)
const showRenameDialog = ref(false)
const showNicknameDialog = ref(false)

const creating = ref(false)
const joining = ref(false)

const createForm = ref({ name: '' })
const joinForm = ref({ shareCode: '', nickname: '' })
const newName = ref('')
const nickname = ref(localStorage.getItem('trip_nickname') || '')

const currentTrip = ref(null)
const mapRef = ref(null)

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

// 方法
async function createTrip() {
  creating.value = true
  try {
    const trip = await tripApi.createTrip(createForm.value.name || '未命名行程')
    currentTrip.value = trip
    showCreateDialog.value = false
    createForm.value.name = ''
    
    // 加入行程
    if (nickname.value) {
      await tripApi.joinTrip(trip.trip_id, nickname.value)
    }
    
    // 更新 URL
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
    // 获取行程 ID
    const { trip_id } = await tripApi.getTripByCode(joinForm.value.shareCode)
    
    // 加入行程
    if (joinForm.value.nickname) {
      await tripApi.joinTrip(trip_id, joinForm.value.nickname)
      localStorage.setItem('trip_nickname', joinForm.value.nickname)
    }
    
    // 加载行程详情
    const trip = await tripApi.getTrip(trip_id)
    currentTrip.value = trip
    
    showJoinDialog.value = false
    joinForm.value = { shareCode: '', nickname: '' }
    
    // 更新 URL
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
    
    // 显示选中的景点
    if (mapRef.value && trip.pois.length > 0) {
      mapRef.value.highlightPois(trip.pois.map(p => p.id))
    }
  } catch (error) {
    ElMessage.error('加载行程失败')
    router.push('/')
  }
}

async function addPoiToTrip(poiId, dayNumber = 1) {
  if (!currentTrip.value) {
    ElMessage.warning('请先创建或加入行程')
    return
  }
  
  try {
    await tripApi.addPoi(
      currentTrip.value.trip_id,
      poiId,
      dayNumber,
      '',
      nickname.value || '匿名'
    )
    
    // 重新加载行程
    await loadTrip(currentTrip.value.trip_id)
    ElMessage.success('添加成功')
  } catch (error) {
    if (error.message.includes('已在行程中')) {
      ElMessage.warning('景点已在行程中')
    } else {
      ElMessage.error('添加失败')
    }
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

function setNickname() {
  if (nickname.value) {
    localStorage.setItem('trip_nickname', nickname.value)
    showNicknameDialog.value = false
    ElMessage.success('昵称已保存')
  }
}

function copyShareLink() {
  const link = `${window.location.origin}/trip/${currentTrip.value.trip_id}`
  navigator.clipboard.writeText(link)
  ElMessage.success('链接已复制: ' + currentTrip.value.share_code)
}

function exportTrip() {
  // TODO: 导出行程为文本/图片
  ElMessage.info('导出功能开发中...')
}

function handlePoiClick(poi) {
  // 点击景点显示详情
  console.log('Clicked POI:', poi)
}

function handlePoiAdd(poi) {
  // 从地图添加景点到行程
  addPoiToTrip(poi.id)
}

function onPoiDragEnd() {
  // 拖拽排序后更新顺序
  // TODO: 调用 API 更新顺序
}

// 生命周期
onMounted(() => {
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

.toolbar {
  padding: 10px 20px;
  background: white;
  border-bottom: 1px solid #eee;
  display: flex;
  gap: 10px;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.map-section {
  flex: 1;
  position: relative;
}

.trip-panel {
  width: 360px;
  background: #f5f7fa;
  padding: 10px;
  overflow-y: auto;
}

.trip-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.trip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trip-header h3 {
  margin: 0;
}

.share-info {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.share-code strong {
  color: #409eff;
  font-size: 14px;
}

.members-section {
  margin: 10px 0;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.members-section .el-tag {
  margin-right: 5px;
}

.pois-section {
  flex: 1;
  overflow-y: auto;
}

.day-group {
  margin-bottom: 15px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.day-header h4 {
  margin: 0;
}

.poi-list {
  min-height: 50px;
}

.poi-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: white;
  border-radius: 4px;
  margin-bottom: 5px;
  cursor: move;
}

.poi-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.poi-name {
  font-size: 14px;
}

.trip-actions {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.empty-trip {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
