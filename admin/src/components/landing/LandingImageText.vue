<template>
  <div class="landing-image-text" :class="`layout-${layout || 'left-right'}`">
    <div class="image-section">
      <img v-if="image_url" :src="image_url" class="card-image" />
      <div v-else class="image-placeholder">图片</div>
    </div>
    <div class="text-section">
      <h3 class="card-title" :style="{ color: title_color || '#333333', fontSize: previewFontSize(title_font_size, 32), fontFamily: previewFontFamily(title_font_family), fontWeight: title_font_weight || '600' }">{{ title || '标题' }}</h3>
      <p class="card-desc" :style="{ color: desc_color || '#999999', fontSize: previewFontSize(desc_font_size, 26), fontFamily: previewFontFamily(desc_font_family), fontWeight: desc_font_weight || '400' }">{{ description || '描述文字' }}</p>
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
  title_font_size?: number | string
  desc_font_size?: number | string
  title_font_family?: string
  desc_font_family?: string
  title_font_weight?: string
  desc_font_weight?: string
}>()

function previewFontSize(value: number | string | undefined, fallbackRpx: number) {
  if (typeof value === 'string' && value.trim()) {
    return value.endsWith('rpx') ? `${Number.parseFloat(value) / 2}px` : value
  }
  const rpx = typeof value === 'number' && Number.isFinite(value) ? value : fallbackRpx
  return `${rpx / 2}px`
}

function previewFontFamily(value: string | undefined) {
  const map: Record<string, string> = {
    system: 'inherit',
    sans: 'Arial, "PingFang SC", "Microsoft YaHei", sans-serif',
    serif: '"Songti SC", SimSun, serif',
    rounded: '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
  }
  return map[value || 'system'] || value || 'inherit'
}
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
