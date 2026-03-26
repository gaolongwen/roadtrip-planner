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
      
      <div class="poi-info" v-if="poi.type">
        <el-icon><CollectionTag /></el-icon>
        <el-tag size="small">{{ poi.type }}</el-tag>
      </div>
      
      <div class="poi-info" v-if="poi.isWild">
        <el-icon><Compass /></el-icon>
        <el-tag type="warning" size="small">野生景点</el-tag>
      </div>
      
      <div class="poi-description" v-if="poi.description">
        <p>{{ poi.description }}</p>
      </div>
      
      <div class="poi-coords">
        <el-icon><MapLocation /></el-icon>
        <span>经度: {{ poi.longitude?.toFixed(6) }}, 纬度: {{ poi.latitude?.toFixed(6) }}</span>
      </div>
    </div>
    
    <div class="poi-actions">
      <el-button type="primary" size="small" @click="$emit('navigate', poi)">
        <el-icon><Position /></el-icon>
        导航
      </el-button>
      <el-button size="small" @click="$emit('edit', poi)">
        <el-icon><Edit /></el-icon>
        编辑
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  poi: {
    type: Object,
    default: null,
  },
})

defineEmits(['close', 'navigate', 'edit'])
</script>

<style scoped>
.poi-card {
  border-radius: 8px;
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

.poi-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.poi-description {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
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
