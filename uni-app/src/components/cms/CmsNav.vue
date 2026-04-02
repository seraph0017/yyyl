<template>
  <view class="cms-nav" v-if="data.items?.length">
    <view
      class="cms-nav__grid"
      :style="{ gridTemplateColumns: `repeat(${data.columns || 4}, 1fr)` }"
    >
      <view
        v-for="(item, idx) in data.items"
        :key="idx"
        class="cms-nav__item"
        @tap="onItemTap(item.link)"
      >
        <view class="cms-nav__icon">
          <!-- 图片 URL 则用 image，emoji/text 则用 text -->
          <image
            v-if="isImageUrl(item.icon) && !errorIcons[idx]"
            :src="resolveImageUrl(item.icon)"
            mode="aspectFit"
            class="cms-nav__icon-img"
            lazy-load
            @error="onIconError(idx)"
          />
          <text v-else class="cms-nav__icon-emoji">{{ (!isImageUrl(item.icon) && item.icon) || '📌' }}</text>
        </view>
        <text class="cms-nav__name">{{ item.name }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 快捷导航组件
 * 支持 3/4/5 列网格布局，图标支持 URL 图片和 emoji
 */
import { ref } from 'vue'
import { resolveImageUrl } from '@/utils/request'
import type { CmsNavProps, CmsComponentStyle, CmsLink } from '@/types/cms'

interface Props {
  data: CmsNavProps
  componentStyle?: CmsComponentStyle
}

defineProps<Props>()
const emit = defineEmits<{
  (e: 'link-tap', link: CmsLink): void
}>()

const errorIcons = ref<Record<number, boolean>>({})

/** 图标图片加载失败 */
function onIconError(idx: number) {
  errorIcons.value = { ...errorIcons.value, [idx]: true }
}

/** 判断是否为图片 URL */
function isImageUrl(icon: string): boolean {
  if (!icon) return false
  return icon.startsWith('http://') || icon.startsWith('https://') || icon.startsWith('/')
}

/** 导航项点击 */
function onItemTap(link: CmsLink) {
  if (link && link.type !== 'none') {
    emit('link-tap', link)
  }
}
</script>

<style lang="scss" scoped>
.cms-nav {
  padding: var(--spacing-lg) var(--spacing-lg) var(--spacing-md);

  &__grid {
    display: grid;
    gap: 24rpx 16rpx;
  }

  &__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 4rpx 0;
    transition: var(--transition-base);

    &:active {
      transform: scale(0.92);
    }
  }

  &__icon {
    width: 88rpx;
    height: 88rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: var(--radius-xl);
    background: var(--color-bg-card);
    box-shadow: var(--shadow-sm);
    margin-bottom: 12rpx;
  }

  &__icon-img {
    width: 48rpx;
    height: 48rpx;
  }

  &__icon-emoji {
    font-size: 44rpx;
  }

  &__name {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    font-weight: 500;
    letter-spacing: 1rpx;
  }
}
</style>
