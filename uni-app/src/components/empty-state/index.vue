<template>
  <view class="empty-state">
    <text class="empty-state__icon">{{ icon }}</text>
    <text class="empty-state__title">{{ title }}</text>
    <text class="empty-state__desc" v-if="description">{{ description }}</text>
    <view class="empty-state__btn btn-primary" v-if="buttonText" @tap="$emit('action')">
      <text>{{ buttonText }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string
  title?: string
  description?: string
  buttonText?: string
}>(), {
  icon: '📭',
  title: '暂无数据',
  description: '',
  buttonText: '',
})

defineEmits<{
  (e: 'action'): void
}>()
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 60rpx 80rpx;

  &__icon {
    font-size: 120rpx;
    margin-bottom: 32rpx;
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--color-text);
    margin-bottom: 12rpx;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    text-align: center;
    line-height: 1.6;
    margin-bottom: 40rpx;
  }

  &__btn {
    width: 280rpx;
    height: 76rpx;
    font-size: var(--font-size-base);
  }
}
</style>
