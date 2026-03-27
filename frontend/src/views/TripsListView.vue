<template>
  <div class="trips-container">
    <!-- 顶部导航栏 -->
    <div class="header">
      <h1 class="title">🚗 我的行程</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showJoinDialog = true">
          加入行程
        </el-button>
        <el-button type="success" @click="createTrip">
          创建新行程
        </el-button>
        <el-button @click="logout">退出</el-button>
      </div>
    </div>

    <!-- 行程列表 -->
    <div class="trips-list" v-loading="loading">
      <div v-if="trips.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无行程，创建一个新行程吧！">
          <el-button type="primary" @click="createTrip">创建新行程</el-button>
        </el-empty>
      </div>

      <div v-else class="trip-cards">
        <div
          v-for="trip in trips"
          :key="trip.trip_id"
          class="trip-card"
          @click="goToTrip(trip.trip_id)"
        >
          <div class="trip-name">{{ trip.name }}</div>
          <div class="trip-stats">
            <span>👥 {{ trip.member_count }} 人</span>
            <span>📍 {{ trip.poi_count }} 景点</span>
          </div>
          <div class="trip-time">
            更新于 {{ formatTime(trip.updated_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 加入行程对话框 -->
    <el-dialog v-model="showJoinDialog" title="加入行程" width="400px">
      <el-form @submit.prevent="joinTrip">
        <el-form-item label="分享码">
          <el-input
            v-model="shareCode"
            placeholder="请输入6位分享码"
            maxlength="6"
            style="text-transform: uppercase"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showJoinDialog = false">取消</el-button>
        <el-button type="primary" @click="joinTrip" :loading="joining">加入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import api from '@/api/index'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const trips = ref([])
const showJoinDialog = ref(false)
const shareCode = ref('')
const joining = ref(false)

// 加载行程列表
const loadTrips = async () => {
  loading.value = true
  try {
    const response = await fetch(`${api.defaults.baseURL}/api/trips`, {
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    if (!response.ok) {
      throw new Error('获取行程失败')
    }
    
    trips.value = await response.json()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

// 创建新行程
const createTrip = async () => {
  try {
    const response = await fetch(`${api.defaults.baseURL}/api/trips`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    if (!response.ok) {
      throw new Error('创建行程失败')
    }
    
    const data = await response.json()
    ElMessage.success('创建成功')
    router.push(`/trip/${data.trip_id}`)
  } catch (error) {
    ElMessage.error(error.message)
  }
}

// 加入行程
const joinTrip = async () => {
  if (!shareCode.value.trim()) {
    ElMessage.warning('请输入分享码')
    return
  }
  
  joining.value = true
  try {
    // 先获取行程ID
    const codeResponse = await fetch(`${api.defaults.baseURL}/api/trips/code/${shareCode.value.toUpperCase()}`, {
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    if (!codeResponse.ok) {
      throw new Error('分享码无效')
    }
    
    const tripData = await codeResponse.json()
    
    // 加入行程
    const joinResponse = await fetch(`${api.defaults.baseURL}/api/trips/${tripData.trip_id}/members`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    if (!joinResponse.ok) {
      throw new Error('加入失败')
    }
    
    ElMessage.success('加入成功')
    showJoinDialog.value = false
    shareCode.value = ''
    router.push(`/trip/${tripData.trip_id}`)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    joining.value = false
  }
}

// 进入行程详情
const goToTrip = (tripId) => {
  router.push(`/trip/${tripId}`)
}

// 退出登录
const logout = () => {
  userStore.logout()
  router.push('/')
}

// 格式化时间
const formatTime = (time) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  
  // 小于1小时
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return minutes <= 1 ? '刚刚' : `${minutes}分钟前`
  }
  
  // 小于24小时
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  
  // 小于7天
  if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}天前`
  }
  
  // 其他
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

onMounted(() => {
  loadTrips()
})
</script>

<style scoped>
.trips-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: 40px;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 30px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.title {
  color: white;
  font-size: 24px;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.trips-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.empty-state {
  padding: 60px 20px;
}

.trip-cards {
  display: grid;
  gap: 15px;
}

.trip-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.trip-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.trip-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.trip-stats {
  display: flex;
  gap: 20px;
  color: #666;
  font-size: 14px;
  margin-bottom: 8px;
}

.trip-time {
  color: #999;
  font-size: 12px;
}
</style>
