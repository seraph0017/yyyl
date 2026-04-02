<template>
  <div class="landing-banner">
    <div v-if="images && images.length > 0" class="banner-carousel">
      <el-carousel
        :interval="(interval || 5) * 1000"
        :autoplay="autoplay !== false"
        :indicator-position="indicatorPosition"
        :style="{ borderRadius: (border_radius || 0) + 'px' }"
        height="400px"
      >
        <el-carousel-item v-for="(img, idx) in images" :key="idx">
          <img :src="img.url" class="banner-image" />
        </el-carousel-item>
      </el-carousel>
    </div>
    <div v-else class="banner-placeholder">
      <span>轮播图（请添加图片）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LinkConfig } from '@/types/cms'

const props = defineProps<{
  images?: Array<{ url: string; link: LinkConfig }>
  interval?: number
  indicator_style?: 'dot' | 'number' | 'none'
  autoplay?: boolean
  border_radius?: number
}>()

const indicatorPosition = computed(() => {
  if (props.indicator_style === 'none') return 'none'
  return 'outside'
})
</script>

<style lang="scss" scoped>
.landing-banner {
  width: 100%;
}

.banner-carousel {
  width: 100%;
  overflow: hidden;
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.banner-placeholder {
  width: 100%;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  color: #909399;
  font-size: 14px;
}

:deep(.el-carousel__container) {
  height: 100% !important;
}
</style>
