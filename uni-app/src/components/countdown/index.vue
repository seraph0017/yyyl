<template>
  <view class="countdown" :class="[`countdown--${size}`]" v-if="showCountdown">
    <view class="countdown__label" v-if="label">
      <text>{{ label }}</text>
    </view>
    <view class="countdown__timer">
      <view class="countdown__block" v-if="showDays && days > 0">
        <text class="countdown__number">{{ padZero(days) }}</text>
        <text class="countdown__unit">天</text>
      </view>
      <view class="countdown__block">
        <text class="countdown__number">{{ padZero(hours) }}</text>
        <text class="countdown__separator">:</text>
      </view>
      <view class="countdown__block">
        <text class="countdown__number">{{ padZero(minutes) }}</text>
        <text class="countdown__separator">:</text>
      </view>
      <view class="countdown__block">
        <text class="countdown__number">{{ padZero(seconds) }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  /** 目标时间（时间戳ms 或 ISO字符串） */
  targetTime: number | string
  /** 显示标签 */
  label?: string
  /** 尺寸 */
  size?: 'small' | 'medium' | 'large'
  /** 是否显示天数 */
  showDays?: boolean
}>(), {
  label: '',
  size: 'medium',
  showDays: true,
})

const emit = defineEmits<{
  (e: 'finish'): void
}>()

const days = ref(0)
const hours = ref(0)
const minutes = ref(0)
const seconds = ref(0)
const showCountdown = ref(true)

let timer: ReturnType<typeof setInterval> | null = null

function padZero(num: number): string {
  return num < 10 ? `0${num}` : String(num)
}

function getTargetTimestamp(): number {
  if (typeof props.targetTime === 'number') return props.targetTime
  return new Date(props.targetTime).getTime()
}

function updateCountdown() {
  const now = Date.now()
  const target = getTargetTimestamp()
  let diff = Math.max(0, Math.floor((target - now) / 1000))

  if (diff <= 0) {
    showCountdown.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    emit('finish')
    return
  }

  days.value = Math.floor(diff / 86400)
  diff %= 86400
  hours.value = Math.floor(diff / 3600)
  diff %= 3600
  minutes.value = Math.floor(diff / 60)
  seconds.value = diff % 60
}

onMounted(() => {
  updateCountdown()
  timer = setInterval(updateCountdown, 1000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})

watch(() => props.targetTime, () => {
  showCountdown.value = true
  updateCountdown()
})
</script>

<style lang="scss" scoped>
.countdown {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;

  &__label {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-right: 8rpx;
  }

  &__timer {
    display: flex;
    align-items: center;
  }

  &__block {
    display: flex;
    align-items: center;
  }

  &__number {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    min-width: 40rpx;
    height: 40rpx;
    background-color: var(--color-text);
    color: #fff;
    font-size: 22rpx;
    font-weight: 700;
    border-radius: 6rpx;
    font-variant-numeric: tabular-nums;
    padding: 0 4rpx;
  }

  &__separator {
    font-size: 22rpx;
    font-weight: 700;
    color: var(--color-text);
    margin: 0 4rpx;
  }

  &__unit {
    font-size: 20rpx;
    color: var(--color-text-secondary);
    margin: 0 4rpx;
  }

  /* 尺寸变体 */
  &--small {
    .countdown__number {
      min-width: 32rpx;
      height: 32rpx;
      font-size: 18rpx;
    }
    .countdown__separator {
      font-size: 18rpx;
    }
  }

  &--large {
    .countdown__number {
      min-width: 52rpx;
      height: 52rpx;
      font-size: 28rpx;
      border-radius: 8rpx;
    }
    .countdown__separator {
      font-size: 28rpx;
      margin: 0 8rpx;
    }
  }
}
</style>
