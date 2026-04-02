<template>
  <view class="cms-video" v-if="data.url">
    <!-- 视频播放器 -->
    <video
      v-if="!playError"
      class="cms-video__player"
      :src="data.url"
      :poster="data.poster ? resolveImageUrl(data.poster) : ''"
      :autoplay="data.autoplay || false"
      :loop="data.loop || false"
      :show-fullscreen-btn="true"
      :show-play-btn="true"
      :controls="true"
      object-fit="contain"
      @error="onVideoError"
    />

    <!-- 播放失败兜底 -->
    <view v-else class="cms-video__error">
      <text class="cms-video__error-icon">🎬</text>
      <text class="cms-video__error-text">视频加载失败</text>
      <view class="cms-video__retry" @tap="onRetry">
        <text>点击重试</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 视频区块组件
 * 使用 uni-app 原生 <video> 组件，支持封面图、自动播放、循环播放
 */
import { ref } from 'vue'
import { resolveImageUrl } from '@/utils/request'
import type { CmsVideoProps, CmsComponentStyle } from '@/types/cms'

interface Props {
  data: CmsVideoProps
  componentStyle?: CmsComponentStyle
}

defineProps<Props>()

const playError = ref(false)

/** 视频加载失败 */
function onVideoError() {
  playError.value = true
  console.warn('[CmsVideo] 视频加载失败')
}

/** 重试加载视频 */
function onRetry() {
  playError.value = false
}
</script>

<style lang="scss" scoped>
.cms-video {
  padding: 0 var(--spacing-lg);

  &__player {
    width: 100%;
    border-radius: var(--radius-xl);
    overflow: hidden;
  }

  // 播放失败兜底
  &__error {
    width: 100%;
    height: 400rpx;
    background: var(--color-bg-light);
    border-radius: var(--radius-xl);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 12rpx;
  }

  &__error-icon {
    font-size: 56rpx;
    opacity: 0.5;
  }

  &__error-text {
    color: var(--color-text-placeholder);
    font-size: var(--font-size-sm);
  }

  &__retry {
    margin-top: 8rpx;
    padding: 12rpx 36rpx;
    background: var(--color-primary);
    border-radius: var(--radius-round);
    color: var(--color-text-white);
    font-size: var(--font-size-sm);

    &:active {
      opacity: 0.85;
    }
  }
}
</style>
