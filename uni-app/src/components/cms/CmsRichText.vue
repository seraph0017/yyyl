<template>
  <view class="cms-rich-text" v-if="data.content">
    <view class="cms-rich-text__content">
      <rich-text :nodes="data.content" />
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 富文本组件
 * 使用 uni-app 原生 <rich-text> 组件渲染 HTML 内容
 * 原生组件自动过滤危险标签（<script>、<iframe> 等），这是小程序端的 XSS 防护措施
 */
import type { CmsRichTextProps, CmsComponentStyle } from '@/types/cms'

interface Props {
  data: CmsRichTextProps
  componentStyle?: CmsComponentStyle
}

defineProps<Props>()
</script>

<style lang="scss" scoped>
.cms-rich-text {
  padding: 0 var(--spacing-lg);

  &__content {
    font-size: var(--font-size-base);
    color: var(--color-text);
    line-height: 1.8;
    letter-spacing: 0.5rpx;

    // 全局图片样式（通过外层 class 控制）
    image {
      max-width: 100% !important;
      border-radius: var(--radius-md);
    }
  }
}
</style>
