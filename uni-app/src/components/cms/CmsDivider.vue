<template>
  <view
    class="cms-divider"
    :style="{
      borderTopStyle: data.line_style || 'solid',
      borderTopColor: data.color || 'rgba(42, 37, 32, 0.08)',
      marginLeft: (data.margin_horizontal || 28) + 'rpx',
      marginRight: (data.margin_horizontal || 28) + 'rpx',
    }"
  />
</template>

<script setup lang="ts">
/**
 * CMS 分割线组件
 * 渲染一条水平分割线，支持 solid/dashed 样式
 */
import type { CmsDividerProps, CmsComponentStyle } from '@/types/cms'

interface Props {
  data: CmsDividerProps
  componentStyle?: CmsComponentStyle
}

defineProps<Props>()
</script>

<style lang="scss" scoped>
.cms-divider {
  border-top-width: 1rpx;
}
</style>
