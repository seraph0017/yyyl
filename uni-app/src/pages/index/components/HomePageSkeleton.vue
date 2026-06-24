<template>
  <view class="skeleton">
    <!-- Banner 骨架 -->
    <view class="skeleton__banner" />

    <!-- 导航栏骨架 -->
    <view class="skeleton__nav">
      <view class="skeleton__nav-item" v-for="i in 4" :key="i">
        <view class="skeleton__nav-icon" />
        <view class="skeleton__nav-text" />
      </view>
    </view>

    <!-- 商品列表骨架 -->
    <view class="skeleton__products">
      <view class="skeleton__col">
        <view class="skeleton__card" v-for="i in 3" :key="i">
          <view class="skeleton__image" />
          <view class="skeleton__text" />
          <view class="skeleton__text skeleton__text--short" />
        </view>
      </view>
      <view class="skeleton__col">
        <view class="skeleton__card" v-for="i in 3" :key="i">
          <view class="skeleton__image" />
          <view class="skeleton__text" />
          <view class="skeleton__text skeleton__text--short" />
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 首页加载骨架屏
 * CMS 配置加载期间展示
 */
</script>

<style lang="scss" scoped>
.skeleton {
  padding: 0 var(--spacing-lg);

  &__banner {
    height: 340rpx;
    border-radius: var(--radius-xl);
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    animation: shimmer 2s infinite;
    margin-bottom: var(--spacing-lg);
  }

  &__nav {
    display: flex;
    justify-content: space-around;
    padding: var(--spacing-lg) 0;
  }

  &__nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12rpx;
  }

  &__nav-icon {
    width: 88rpx;
    height: 88rpx;
    border-radius: var(--radius-xl);
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    animation: shimmer 2s infinite;
  }

  &__nav-text {
    width: 64rpx;
    height: 24rpx;
    border-radius: 6rpx;
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    animation: shimmer 2s infinite;
  }

  &__products {
    display: flex;
    gap: 16rpx;
    margin-top: var(--spacing-md);
  }

  &__col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }

  &__card {
    background-color: var(--color-bg-card);
    border-radius: var(--radius-xl);
    overflow: hidden;
    border: 1rpx solid rgba(42, 37, 32, 0.04);
  }

  &__image {
    width: 100%;
    height: 280rpx;
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    animation: shimmer 2s infinite;
  }

  &__text {
    height: 28rpx;
    margin: 16rpx 20rpx 0;
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    border-radius: 6rpx;
    animation: shimmer 2s infinite;

    &--short {
      width: 55%;
      margin-bottom: 20rpx;
    }
  }
}

@keyframes shimmer {
  0% { background-position: 300% 0; }
  100% { background-position: -300% 0; }
}
</style>
