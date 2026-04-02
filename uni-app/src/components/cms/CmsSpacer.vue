<template>
  <view class="cms-spacer" :style="{ height: (data.height || 20) + 'rpx' }" />
</template>

<script setup lang="ts">
/**
 * CMS 间距组件
 * 渲染一个空白间距区域，高度由配置决定
 */
import type { CmsSpacerProps, CmsComponentStyle } from '@/types/cms'

interface Props {
  data: CmsSpacerProps
  componentStyle?: CmsComponentStyle
}

defineProps<Props>()
</script>

<style lang="scss" scoped>
.cms-spacer {
  width: 100%;
}
</style>
