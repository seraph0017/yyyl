<template>
  <div class="landing-image">
    <img
      v-if="url"
      :src="url"
      :style="imageStyle"
      class="landing-image__img"
    />
    <div v-else class="landing-image__placeholder">
      <span>图片（请选择图片）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LinkConfig } from '@/types/cms'

const props = defineProps<{
  url?: string
  link?: LinkConfig
  mode?: 'aspectFill' | 'aspectFit' | 'widthFix'
  width?: string
  height?: string
}>()

const imageStyle = computed(() => {
  const style: Record<string, string> = {
    width: props.width || '100%',
  }
  if (props.height) {
    style.height = props.height
  }
  // 映射裁剪模式到 CSS object-fit
  if (props.mode === 'aspectFill') {
    style.objectFit = 'cover'
  } else if (props.mode === 'aspectFit') {
    style.objectFit = 'contain'
  } else {
    // widthFix: 宽度100%，高度自适应
    style.objectFit = 'contain'
    style.height = 'auto'
  }
  return style
})
</script>

<style lang="scss" scoped>
.landing-image {
  width: 100%;
  display: flex;
  justify-content: center;

  &__img {
    display: block;
    max-width: 100%;
  }

  &__placeholder {
    width: 100%;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f0f2f5;
    color: #909399;
    font-size: 14px;
  }
}
</style>
