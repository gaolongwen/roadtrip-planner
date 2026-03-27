<template>
  <el-card v-if="poi" class="poi-card" shadow="always">
    <template #header>
      <div class="card-header">
        <span class="poi-name">{{ poi.name }}</span>
        <el-button type="text" @click="$emit('close')">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </template>
    
    <div class="poi-content">
      <!-- 景点图片 -->
      <div class="poi-image" v-if="poi.images && poi.images.length > 0">
        <img :src="poi.images[0]" :alt="poi.name" referrerpolicy="no-referrer" @error="handleImageError" />
      </div>
      
      <div class="poi-info">
        <el-icon><Location /></el-icon>
        <span>{{ poi.address || '暂无地址' }}</span>
      </div>
      
      <div class="poi-info" v-if="poi.rating">
        <el-icon><Star /></el-icon>
        <el-rate 
          v-model="poi.rating" 
          disabled 
          show-score 
          text-color="#ff9900"
          score-template="{value} 分"
        />
      </div>
      
      <div class="poi-info" v-if="poi.duration">
        <el-icon><Clock /></el-icon>
        <span>建议游玩 <strong>{{ poi.duration }}</strong> 小时</span>
      </div>
      
      <div class="poi-info">
        <el-icon><CollectionTag /></el-icon>
        <el-tag size="small">{{ poi.category || '未分类' }}</el-tag>
        <el-tag v-if="poi.is_wild" type="warning" size="small">野生</el-tag>
      </div>
      
      <div class="poi-description" v-if="poi.description">
        <p>{{ poi.description }}</p>
      </div>
      
      <!-- 参考链接 -->
      <div class="poi-reference" v-if="poi.reference_url">
        <el-icon><Link /></el-icon>
        <a :href="poi.reference_url" target="_blank" rel="noopener noreferrer">
          查看详情
          <el-icon><TopRight /></el-icon>
        </a>
      </div>
      
      <div class="poi-coords">
        <el-icon><MapLocation /></el-icon>
        <span>{{ poi.longitude?.toFixed(4) }}°E, {{ poi.latitude?.toFixed(4) }}°N</span>
      </div>
    </div>
    
    <div class="poi-actions">
      <!-- 加入行程按钮 -->
      <el-button
        v-if="showAddToTrip"
        :type="isAdded ? 'info' : 'primary'"
        size="small"
        :disabled="isAdded"
        @click="!isAdded && $emit('add-to-trip', poi)"
      >
        <el-icon v-if="isAdded"><Check /></el-icon>
        <el-icon v-else><Plus /></el-icon>
        {{ isAdded ? '已添加' : '加入行程' }}
      </el-button>
      <!-- 编辑按钮 -->
      <el-button size="small" @click="$emit('edit', poi)">
        <el-icon><Edit /></el-icon>
        编辑
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { Close, Location, Star, CollectionTag, Link, TopRight, MapLocation, Edit, Plus, Check, Clock } from '@element-plus/icons-vue'

defineProps({
  poi: {
    type: Object,
    default: null,
  },
  showAddToTrip: {
    type: Boolean,
    default: false,
  },
  isAdded: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['close', 'add-to-trip', 'edit'])

const handleImageError = (e) => {
  e.target.style.display = 'none'
}
</script>

<style scoped>
.poi-card {
  border-radius: 8px;
  max-width: 320px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.poi-name {
  font-size: 16px;
  font-weight: 600;
}

.poi-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.poi-image {
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

.poi-image img {
  width: 100%;
  height: 160px;
  object-fit: cover;
  display: block;
}

.poi-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
  flex-wrap: wrap;
}

.poi-description {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.poi-reference {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.poi-reference a {
  color: #409eff;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.poi-reference a:hover {
  text-decoration: underline;
}

.poi-coords {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}

.poi-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}
</style>
