<template>
  <div class="landing-image-text" :class="`layout-${layout || 'left-right'}`">
    <div class="image-section">
      <img v-if="image_url" :src="image_url" class="card-image" />
      <div v-else class="image-placeholder">图片</div>
    </div>
    <div class="text-section">
      <h3 class="card-title" :style="{ color: title_color || '#333333' }">{{ title || '标题' }}</h3>
      <p class="card-desc" :style="{ color: desc_color || '#999999' }">{{ description || '描述文字' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LinkConfig } from '@/types/cms'

defineProps<{
  layout?: 'left-right' | 'right-left' | 'top-bottom'
  image_url?: string
  title?: string
  description?: string
  link?: LinkConfig
  title_color?: string
  desc_color?: string
}>()
</script>

<style lang="scss" scoped>
.landing-image-text {
  display: flex;
  padding: 12px;
  gap: 12px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;

  &.layout-left-right {
    flex-direction: row;
  }

  &.layout-right-left {
    flex-direction: row-reverse;
  }

  &.layout-top-bottom {
    flex-direction: column;
  }
}

.image-section {
  flex-shrink: 0;

  .layout-left-right &,
  .layout-right-left & {
    width: 120px;
    height: 90px;
  }

  .layout-top-bottom & {
    width: 100%;
    height: 200px;
  }
}

.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 6px;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  border-radius: 6px;
  color: #c0c4cc;
  font-size: 13px;
}

.text-section {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 6px;
  line-height: 1.4;
}

.card-desc {
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}
</style>
