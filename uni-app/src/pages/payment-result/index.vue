<template>
  <!-- 支付结果页 -->
  <view class="page-result">
    <!-- 成功 -->
    <view class="result-content" v-if="status === 'success'">
      <text class="result-icon result-icon--success">✅</text>
      <text class="result-title">支付成功</text>
      <text class="result-desc">订单已支付，祝您露营愉快！</text>
      <view class="result-actions">
        <view class="result-btn result-btn--primary" @tap="onViewTicket">
          <text>查看电子票</text>
        </view>
        <view class="result-btn result-btn--outline" @tap="onViewOrder">
          <text>查看订单</text>
        </view>
        <view class="result-btn result-btn--text" @tap="onGoHome">
          <text>返回首页</text>
        </view>
      </view>
      <!-- 订阅消息引导 -->
      <view class="subscribe-guide card">
        <text class="subscribe-guide__icon">🔔</text>
        <view class="subscribe-guide__content">
          <text class="subscribe-guide__title">订阅消息通知</text>
          <text class="subscribe-guide__desc">及时接收订单动态和行程提醒</text>
        </view>
        <view class="subscribe-guide__btn">
          <text>订阅</text>
        </view>
      </view>
    </view>

    <!-- 失败 -->
    <view class="result-content" v-if="status === 'fail'">
      <text class="result-icon result-icon--fail">❌</text>
      <text class="result-title">支付失败</text>
      <text class="result-desc">支付未完成，请重新尝试</text>
      <view class="result-actions">
        <view class="result-btn result-btn--primary" @tap="onRetryPay">
          <text>重新支付</text>
        </view>
        <view class="result-btn result-btn--text" @tap="onGoHome">
          <text>返回首页</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

const status = ref<'success' | 'fail'>('success')
const orderId = ref('')

onLoad((options) => {
  status.value = (options?.status as 'success' | 'fail') || 'success'
  orderId.value = options?.order_id || ''
})

function onViewOrder() {
  uni.redirectTo({ url: `/pages/order-detail/index?id=${orderId.value}` })
}

function onViewTicket() {
  uni.redirectTo({ url: `/pages/ticket/index?order_id=${orderId.value}` })
}

function onRetryPay() {
  uni.navigateBack()
}

function onGoHome() {
  uni.switchTab({ url: '/pages/index/index' })
}
</script>

<style lang="scss" scoped>
.page-result {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding: 80rpx 32rpx;
}

.result-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-icon {
  font-size: 120rpx;
  margin-bottom: 24rpx;
}

.result-title {
  font-size: var(--font-size-xxl);
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 12rpx;
}

.result-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: 48rpx;
}

.result-actions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  padding: 0 32rpx;
}

.result-btn {
  height: 88rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: var(--radius-xl);
  font-size: var(--font-size-lg);
  font-weight: 600;

  &--primary {
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
    text { color: #fff; }
  }

  &--outline {
    border: 2rpx solid var(--color-primary);
    text { color: var(--color-primary); }
  }

  &--text {
    text { color: var(--color-text-secondary); font-size: var(--font-size-base); }
  }

  &:active { opacity: 0.85; }
}

.subscribe-guide {
  display: flex;
  align-items: center;
  width: 100%;
  margin-top: 48rpx;
  padding: 24rpx;

  &__icon { font-size: 40rpx; margin-right: 16rpx; }

  &__content { flex: 1; }
  &__title { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text); display: block; }
  &__desc { font-size: var(--font-size-sm); color: var(--color-text-secondary); display: block; margin-top: 4rpx; }

  &__btn {
    padding: 12rpx 28rpx;
    background-color: var(--color-primary);
    border-radius: var(--radius-round);
    text { font-size: var(--font-size-sm); color: #fff; font-weight: 500; }
    &:active { opacity: 0.85; }
  }
}
</style>
