<template>
  <div class="system-info-panel">
    <div v-if="systemInfo && Object.keys(systemInfo).length > 0" class="info-grid">
      <div
        v-for="(value, key) in systemInfo"
        :key="key"
        class="info-item"
        :class="{ 'full-width': isLongContent(value) }"
      >
        <label>{{ formatLabel(key) }}:</label>
        <span v-if="!isLongContent(value)">{{ value || '未知' }}</span>
        <pre v-else class="long-content">{{ value || '未获取到内容' }}</pre>
      </div>
    </div>
    <div v-else-if="systemInfo === null" class="loading-info">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在获取系统信息...</span>
    </div>
    <div v-else class="empty-info">
      <el-icon><InfoFilled /></el-icon>
      <span>未获取到系统信息</span>
    </div>
  </div>
</template>

<script setup>
import { Loading, InfoFilled } from '@element-plus/icons-vue'

// 定义props
defineProps({
  systemInfo: {
    type: [Object, null],
    default: null,
  },
})

// 格式化标签名称
const formatLabel = (key) => {
  // 将下划线转换为空格，并将每个单词的首字母大写
  return key.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

// 判断是否为长内容（需要全宽显示）
const isLongContent = (value) => {
  if (typeof value !== 'string') return false

  // 如果内容包含换行符或长度超过100个字符，则认为是长内容
  return value.includes('\n') || value.length > 100
}
</script>

<style scoped>
.system-info-panel {
  padding: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 4px;
  background-color: #fafafa;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-item label {
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.info-item span {
  color: #666;
  word-break: break-all;
}

.long-content {
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.loading-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
}

.loading-info .el-icon {
  font-size: 24px;
  margin-bottom: 10px;
}

.empty-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.empty-info .el-icon {
  font-size: 24px;
  margin-bottom: 10px;
}
</style>
