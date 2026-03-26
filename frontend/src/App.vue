<template>
  <el-container>
    <el-header>
      <h1>🚗 自驾行程规划</h1>
    </el-header>
    <MapView />
  </el-container>
</template>

<script setup>
import MapView from './views/MapView.vue'
</script>

<style scoped>
.el-container {
  height: 100vh;
}
</style>
