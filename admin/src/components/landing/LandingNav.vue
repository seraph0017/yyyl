<template>
  <div class="landing-nav">
    <div
      class="nav-grid"
      :style="{ gridTemplateColumns: `repeat(${columns || 4}, 1fr)` }"
    >
      <div v-for="(item, idx) in items" :key="idx" class="nav-item">
        <div class="nav-icon">
          <img v-if="item.icon" :src="item.icon" />
          <el-icon v-else :size="24"><Grid /></el-icon>
        </div>
        <span v-if="show_label !== false" class="nav-label">{{ item.label || '导航' }}</span>
      </div>
    </div>
    <div v-if="!items || items.length === 0" class="nav-placeholder">
      快捷导航（请添加导航项）
    </div>
  </div>
</template>

<script setup lang="ts">
import { Grid } from '@element-plus/icons-vue'
import type { LinkConfig } from '@/types/cms'

defineProps<{
  items?: Array<{ icon: string; label: string; link: LinkConfig }>
  columns?: 4 | 5
  show_label?: boolean
}>()
</script>

<style lang="scss" scoped>
.landing-nav {
  padding: 12px 16px;
}

.nav-grid {
  display: grid;
  gap: 12px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.nav-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #f5f7fa;

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .el-icon {
    color: #909399;
  }
}

.nav-label {
  font-size: 12px;
  color: #333;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60px;
}

.nav-placeholder {
  text-align: center;
  padding: 20px;
  color: #c0c4cc;
  font-size: 13px;
}
</style>
