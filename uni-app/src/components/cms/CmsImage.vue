<template>
  <view class="cms-image" v-if="data.images?.length">
    <view class="cms-image__grid" :style="gridStyle">
      <view
        v-for="(item, idx) in data.images"
        :key="idx"
        class="cms-image__item"
        @tap="onImageTap(item, idx)"
      >
        <image
          v-if="!errorImages[idx]"
          class="cms-image__img"
          :class="{ 'cms-image__img--multi': data.layout !== 'single' }"
          :src="resolveImageUrl(item.url)"
          :mode="data.layout === 'single' ? 'widthFix' : 'aspectFill'"
          :lazy-load="idx > 0"
          @error="onImageError(idx)"
        />
        <!-- 图片加载失败占位 -->
        <view v-else class="cms-image__fallback">
          <text class="cms-image__fallback-icon">🖼️</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 图片区块组件
 * 支持 single / two-column / three-column / four-grid 四种布局
 */
import { ref, computed } from 'vue'
import { resolveImageUrl } from '@/utils/request'
import type { CmsImageProps, CmsComponentStyle, CmsLink } from '@/types/cms'

interface Props {
  data: CmsImageProps
  componentStyle?: CmsComponentStyle
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'link-tap', link: CmsLink): void
}>()

const errorImages = ref<Record<number, boolean>>({})

/** 图片加载失败 */
function onImageError(idx: number) {
  errorImages.value = { ...errorImages.value, [idx]: true }
}

/** 根据 layout 计算 grid 样式 */
const gridStyle = computed(() => {
  const layout = props.data.layout || 'single'
  const columnMap: Record<string, string> = {
    single: '1fr',
    'two-column': 'repeat(2, 1fr)',
    'three-column': 'repeat(3, 1fr)',
    'four-grid': 'repeat(2, 1fr)',
  }
  return {
    gridTemplateColumns: columnMap[layout] || '1fr',
  }
})

/** 图片点击 — 有 link 则跳转，否则预览大图 */
function onImageTap(item: { url: string; link: CmsLink }, idx: number) {
  if (item.link && item.link.type !== 'none') {
    emit('link-tap', item.link)
  } else {
    // 长按/点击预览大图
    const urls = (props.data.images || []).map((img) => resolveImageUrl(img.url))
    uni.previewImage({
      urls,
      current: idx,
    })
  }
}
</script>

<style lang="scss" scoped>
.cms-image {
  padding: 0 var(--spacing-lg);

  &__grid {
    display: grid;
    gap: 12rpx;
  }

  &__item {
    border-radius: var(--radius-lg);
    overflow: hidden;
    position: relative;

    &:active {
      transform: scale(0.96);
      opacity: 0.85;
    }
  }

  &__img {
    width: 100%;
    border-radius: var(--radius-lg);

    // 多图模式 — 正方形
    &--multi {
      height: 0;
      padding-bottom: 100%;
      /* 利用 uni-app image 原生属性实现正方形 */
    }
  }

  /* 多图模式下 image 需要绝对定位填充 */
  &__item &__img--multi {
    height: 100%;
    padding-bottom: 0;
    aspect-ratio: 1;
  }

  &__fallback {
    width: 100%;
    aspect-ratio: 1;
    background: var(--color-bg-light);
    border-radius: var(--radius-lg);
    display: flex;
    justify-content: center;
    align-items: center;
  }

  &__fallback-icon {
    font-size: 48rpx;
    opacity: 0.4;
  }
}
</style>
