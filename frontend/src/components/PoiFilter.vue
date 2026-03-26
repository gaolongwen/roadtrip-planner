<template>
  <el-card class="filter-panel" shadow="never">
    <template #header>
      <div class="filter-header">
        <span>筛选条件</span>
        <el-button type="text" size="small" @click="resetFilters">
          重置
        </el-button>
      </div>
    </template>
    
    <el-form label-position="top" size="small">
      <!-- 景点性质 -->
      <el-form-item label="景点性质">
        <el-checkbox-group v-model="localFilters.nature">
          <el-checkbox label="正规">正规景点</el-checkbox>
          <el-checkbox label="野生">野生景点</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      
      <!-- 主要看点 -->
      <el-form-item label="主要看点">
        <el-checkbox-group v-model="localFilters.category">
          <el-checkbox label="人文">人文历史</el-checkbox>
          <el-checkbox label="自然">自然风光</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      
      <!-- 标签筛选 -->
      <el-form-item label="特色标签">
        <el-checkbox-group v-model="localFilters.tags">
          <el-checkbox label="古建">古建</el-checkbox>
          <el-checkbox label="石窟">石窟</el-checkbox>
          <el-checkbox label="佛教">佛教</el-checkbox>
          <el-checkbox label="道教">道教</el-checkbox>
          <el-checkbox label="长城">长城</el-checkbox>
          <el-checkbox label="古村">古村</el-checkbox>
          <el-checkbox label="自然">自然</el-checkbox>
          <el-checkbox label="世界遗产">世遗</el-checkbox>
          <el-checkbox label="博物馆">博物馆</el-checkbox>
          <el-checkbox label="教堂">教堂</el-checkbox>
          <el-checkbox label="工业遗产">工业</el-checkbox>
          <el-checkbox label="挂壁公路">挂壁</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
    </el-form>
    
    <el-button type="primary" size="small" @click="applyFilters" style="width: 100%;">
      应用筛选
    </el-button>
  </el-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { usePoiStore } from '../stores/poi'

const emit = defineEmits(['filter'])
const poiStore = usePoiStore()

const localFilters = ref({
  nature: ['正规', '野生'],  // 默认全选
  category: ['人文', '自然'], // 默认全选
  tags: [],
})

// 应用筛选
const applyFilters = () => {
  poiStore.setFilters(localFilters.value)
  emit('filter', localFilters.value)
}

// 重置筛选
const resetFilters = () => {
  localFilters.value = {
    nature: ['正规', '野生'],
    category: ['人文', '自然'],
    tags: [],
  }
  poiStore.resetFilters()
  emit('filter', localFilters.value)
}

// 同步 store 的筛选状态
watch(() => poiStore.filters, (newFilters) => {
  localFilters.value = { ...newFilters }
}, { immediate: true, deep: true })
</script>

<style scoped>
.filter-panel {
  margin: 10px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.el-checkbox {
  margin-right: 0;
}
</style>
