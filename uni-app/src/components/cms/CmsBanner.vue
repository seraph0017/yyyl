<template>
  <view class="cms-banner" v-if="data.images?.length">
    <swiper
      class="cms-banner__swiper"
      :indicator-dots="false"
      autoplay
      circular
      :interval="(data.interval || 5) * 1000"
      :duration="600"
      @change="onSwiperChange"
    >
      <swiper-item v-for="(item, idx) in data.images" :key="idx">
        <view class="cms-banner__item" @tap="onImageTap(item.link)">
          <image
            v-if="!errorImages[idx]"
            class="cms-banner__image"
            :src="resolveImageUrl(item.url)"
            mode="aspectFill"
            :lazy-load="idx > 0"
            @error="onImageError(idx)"
          />
          <!-- 图片加载失败优雅占位 -->
          <view v-else class="cms-banner__placeholder">
            <text class="cms-banner__placeholder-icon">🏕️</text>
            <text class="cms-banner__placeholder-text">图片加载失败</text>
          </view>
        </view>
      </swiper-item>
    </swiper>

    <!-- 自定义指示器 -->
    <view
      v-if="indicatorStyle !== 'none'"
      class="cms-banner__indicator"
    >
      <!-- dot 圆点模式 -->
      <template v-if="indicatorStyle === 'dot'">
        <view
          v-for="(_, idx) in data.images"
          :key="idx"
          class="cms-banner__dot"
          :class="{ 'cms-banner__dot--active': currentIndex === idx }"
        />
      </template>
      <!-- number 数字模式 -->
      <template v-else-if="indicatorStyle === 'number'">
        <view class="cms-banner__number">
          <text>{{ currentIndex + 1 }}/{{ data.images.length }}</text>
        </view>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS Banner 轮播图组件
 * 支持自动轮播、自定义指示器样式、图片点击跳转
 */
import { ref, computed } from 'vue'
import { resolveImageUrl } from '@/utils/request'
import type { CmsBannerProps, CmsComponentStyle, CmsLink } from '@/types/cms'

interface Props {
  data: CmsBannerProps
  componentStyle?: CmsComponentStyle
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'link-tap', link: CmsLink): void
}>()

const currentIndex = ref(0)
const errorImages = ref<Record<number, boolean>>({})

/** 指示器样式，默认 dot */
const indicatorStyle = computed(() => props.data.indicator_style || 'dot')

/** 轮播变更 */
function onSwiperChange(e: { detail: { current: number } }) {
  currentIndex.value = e.detail.current
}

/** 图片点击 */
function onImageTap(link: CmsLink) {
  if (link && link.type !== 'none') {
    emit('link-tap', link)
  }
}

/** 图片加载失败 */
function onImageError(idx: number) {
  errorImages.value = { ...errorImages.value, [idx]: true }
}
</script>

<style lang="scss" scoped>
.cms-banner {
  width: 100%;
  overflow: hidden;

  &__swiper {
    height: 340rpx;
  }

  &__item {
    width: 100%;
    height: 100%;
    position: relative;
  }

  &__image {
    width: 100%;
    height: 100%;
    border-radius: var(--radius-xl);
  }

  &__placeholder {
    position: absolute;
    inset: 0;
    background: var(--color-bg-light);
    border-radius: var(--radius-xl);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 8rpx;
  }

  &__placeholder-icon {
    font-size: 48rpx;
    opacity: 0.5;
  }

  &__placeholder-text {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
  }

  // 指示器 — 暖铜金色活跃态
  &__indicator {
    display: flex;
    justify-content: center;
    gap: 10rpx;
    margin-top: 16rpx;
  }

  &__dot {
    width: 8rpx;
    height: 8rpx;
    border-radius: 50%;
    background-color: var(--color-text-placeholder);
    opacity: 0.3;
    transition: all 0.4s var(--ease-out-expo);

    &--active {
      width: 28rpx;
      border-radius: 4rpx;
      background: linear-gradient(90deg, var(--color-accent), var(--color-primary-light));
      opacity: 1;
    }
  }

  &__number {
    padding: 4rpx 16rpx;
    background: rgba(42, 37, 32, 0.4);
    border-radius: var(--radius-round);

    text {
      font-size: var(--font-size-xs);
      color: var(--color-text-white);
    }
  }
}
</style>
