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
      <el-form-item label="省份">
        <el-select 
          v-model="localFilters.province" 
          placeholder="选择省份" 
          clearable
          @change="onProvinceChange"
        >
          <el-option 
            v-for="province in provinces" 
            :key="province" 
            :label="province" 
            :value="province"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="城市">
        <el-select 
          v-model="localFilters.city" 
          placeholder="选择城市" 
          clearable
          :disabled="!localFilters.province"
        >
          <el-option 
            v-for="city in filteredCities" 
            :key="city" 
            :label="city" 
            :value="city"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="景点类型">
        <el-select 
          v-model="localFilters.type" 
          placeholder="选择类型" 
          clearable
        >
          <el-option 
            v-for="type in poiTypes" 
            :key="type" 
            :label="type" 
            :value="type"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="野生景点">
        <el-switch 
          v-model="localFilters.isWild"
          active-text="只看野生"
          inactive-text="全部"
        />
      </el-form-item>
    </el-form>
    
    <el-button type="primary" size="small" @click="applyFilters" style="width: 100%;">
      应用筛选
    </el-button>
  </el-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePoiStore } from '../stores/poi'

const emit = defineEmits(['filter'])
const poiStore = usePoiStore()

// 省份数据（河南周边）
const provinces = ['河南', '陕西', '山西', '河北', '山东', '安徽', '湖北']

// 城市数据
const cityMap = {
  '河南': ['郑州', '洛阳', '开封', '安阳', '新乡', '焦作', '南阳', '信阳', '周口', '驻马店'],
  '陕西': ['西安', '咸阳', '宝鸡', '渭南', '延安', '汉中', '榆林'],
  '山西': ['太原', '大同', '晋中', '临汾', '运城', '长治'],
  '河北': ['石家庄', '保定', '邯郸', '邢台', '张家口', '承德'],
  '山东': ['济南', '青岛', '烟台', '威海', '泰安', '济宁'],
  '安徽': ['合肥', '芜湖', '蚌埠', '黄山', '安庆'],
  '湖北': ['武汉', '宜昌', '襄阳', '十堰', '恩施'],
}

// 景点类型
const poiTypes = ['自然风光', '历史文化', '主题乐园', '网红打卡', '美食街', '其他']

const localFilters = ref({
  province: '',
  city: '',
  type: '',
  isWild: false,
})

// 过滤后的城市列表
const filteredCities = computed(() => {
  return cityMap[localFilters.value.province] || []
})

// 省份变化时清空城市选择
const onProvinceChange = () => {
  localFilters.value.city = ''
}

// 应用筛选
const applyFilters = () => {
  poiStore.setFilters(localFilters.value)
  emit('filter', localFilters.value)
}

// 重置筛选
const resetFilters = () => {
  localFilters.value = {
    province: '',
    city: '',
    type: '',
    isWild: false,
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

.el-select {
  width: 100%;
}
</style>
