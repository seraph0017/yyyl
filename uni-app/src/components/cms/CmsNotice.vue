<template>
  <view
    class="cms-notice"
    :style="noticeStyle"
    v-if="data.notices?.length"
    @tap="onNoticeTap"
  >
    <view class="cms-notice__icon">
      <text>{{ data.icon || '📢' }}</text>
    </view>
    <view class="cms-notice__text">
      <text
        class="cms-notice__scroll"
        :class="{ 'cms-notice__scroll--fade': fading }"
      >{{ currentNotice?.text || '' }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 公告栏组件
 * 多条公告轮流展示，支持点击跳转
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { CmsNoticeProps, CmsComponentStyle, CmsLink } from '@/types/cms'

interface Props {
  data: CmsNoticeProps
  componentStyle?: CmsComponentStyle
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'link-tap', link: CmsLink): void
}>()

const currentIndex = ref(0)
const fading = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

/** 当前公告 */
const currentNotice = computed(() => {
  const notices = props.data.notices || []
  if (notices.length === 0) return null
  return notices[currentIndex.value % notices.length]
})

/** 公告栏背景样式 */
const noticeStyle = computed(() => {
  if (props.data.background_color) {
    return { background: props.data.background_color }
  }
  return {}
})

/** 点击公告 */
function onNoticeTap() {
  const notice = currentNotice.value
  if (notice?.link && notice.link.type !== 'none') {
    emit('link-tap', notice.link)
  }
}

onMounted(() => {
  // 多条公告时轮流展示
  const notices = props.data.notices || []
  if (notices.length > 1) {
    timer = setInterval(() => {
      fading.value = true
      setTimeout(() => {
        currentIndex.value = (currentIndex.value + 1) % notices.length
        fading.value = false
      }, 300)
    }, 4000)
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style lang="scss" scoped>
.cms-notice {
  margin: 0 var(--spacing-lg);
  padding: 16rpx 24rpx;
  background: var(--color-accent-bg);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  gap: 12rpx;
  overflow: hidden;

  &:active {
    opacity: 0.85;
  }

  &__icon {
    flex-shrink: 0;
    font-size: 28rpx;
  }

  &__text {
    flex: 1;
    font-size: var(--font-size-sm);
    color: var(--color-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__scroll {
    display: inline;
    transition: opacity 0.3s ease;

    &--fade {
      opacity: 0;
    }
  }
}
</style>
