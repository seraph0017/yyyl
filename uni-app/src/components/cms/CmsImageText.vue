<template>
  <view
    class="cms-image-text"
    :class="{ 'cms-image-text--horizontal': layoutMode === 'horizontal' }"
    @tap="onCardTap"
  >
    <view class="cms-image-text__image-wrapper" :class="{ 'cms-image-text__image-wrapper--horizontal': layoutMode === 'horizontal' }">
      <image
        v-if="!imageError"
        class="cms-image-text__image"
        :class="{ 'cms-image-text__image--horizontal': layoutMode === 'horizontal' }"
        :src="resolveImageUrl(data.image || '')"
        mode="aspectFill"
        lazy-load
        @error="imageError = true"
      />
      <view v-else class="cms-image-text__image-fallback">
        <text class="cms-image-text__fallback-icon">🏕️</text>
      </view>
    </view>
    <view class="cms-image-text__content">
      <text class="cms-image-text__title">{{ data.title || '' }}</text>
      <text v-if="data.subtitle" class="cms-image-text__subtitle">{{ data.subtitle }}</text>
      <text v-if="data.description" class="cms-image-text__description">{{ data.description }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 图文卡片组件
 * 支持 horizontal（左图右文）和 vertical（上图下文）两种布局
 */
import { ref, computed } from 'vue'
import { resolveImageUrl } from '@/utils/request'
import type { CmsImageTextProps, CmsComponentStyle, CmsLink } from '@/types/cms'

interface Props {
  data: CmsImageTextProps
  componentStyle?: CmsComponentStyle
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'link-tap', link: CmsLink): void
}>()

const imageError = ref(false)

/** 布局模式，默认 horizontal */
const layoutMode = computed(() => props.data.layout || 'horizontal')

/** 卡片点击 */
function onCardTap() {
  if (props.data.link && props.data.link.type !== 'none') {
    emit('link-tap', props.data.link)
  }
}
</script>

<style lang="scss" scoped>
.cms-image-text {
  margin: 0 var(--spacing-lg);
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  border: 1rpx solid rgba(42, 37, 32, 0.04);

  &:active {
    transform: scale(0.96);
    opacity: 0.85;
  }

  // 水平布局
  &--horizontal {
    display: flex;
    align-items: stretch;
  }

  &__image-wrapper {
    overflow: hidden;

    &--horizontal {
      width: 280rpx;
      flex-shrink: 0;
    }
  }

  &__image {
    width: 100%;
    height: 320rpx;

    // 水平布局下图片尺寸
    &--horizontal {
      width: 280rpx;
      height: 100%;
      flex-shrink: 0;
    }
  }

  &__image-fallback {
    width: 100%;
    height: 320rpx;
    background: var(--color-bg-light);
    display: flex;
    justify-content: center;
    align-items: center;
  }

  &__fallback-icon {
    font-size: 48rpx;
    opacity: 0.4;
  }

  &__content {
    padding: var(--spacing-lg);
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: 1rpx;
    line-height: 1.4;
  }

  &__subtitle {
    font-size: var(--font-size-sm);
    color: var(--color-accent);
    margin-top: 8rpx;
    letter-spacing: 1rpx;
  }

  &__description {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    margin-top: 12rpx;
    line-height: 1.6;
    // 最多3行省略
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}
</style>
