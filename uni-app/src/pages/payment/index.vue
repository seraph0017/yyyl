<template>
  <!-- 支付页 -->
  <view class="page-payment">
    <view class="payment-card card">
      <!-- 金额 -->
      <view class="payment-amount">
        <text class="payment-amount__label">支付金额</text>
        <view class="payment-amount__value">
          <text class="payment-amount__symbol">¥</text>
          <text class="payment-amount__num">{{ amount }}</text>
        </view>
      </view>

      <!-- 订单信息 -->
      <view class="payment-info">
        <view class="payment-info__row">
          <text class="payment-info__label">订单编号</text>
          <text class="payment-info__value">{{ orderNo }}</text>
        </view>
        <view class="payment-info__row">
          <text class="payment-info__label">支付方式</text>
          <text class="payment-info__value">微信支付</text>
        </view>
        <view class="payment-info__row">
          <text class="payment-info__label">支付倒计时</text>
          <Countdown :targetTime="expiredAt" mode="inline" @finish="onCountdownFinish" />
        </view>
      </view>

      <!-- 支付提示 -->
      <view class="payment-mock-tip">
        <text class="payment-mock-tip__icon">🔒</text>
        <text class="payment-mock-tip__text">将打开微信支付收银台，支付结果以微信通知为准</text>
      </view>
    </view>

    <!-- 操作按钮 -->
    <view class="payment-actions">
      <view :class="['payment-btn', 'payment-btn--success', paying ? 'btn-disabled' : '']" @tap="onWechatPay">
        <text class="payment-btn__icon">💳</text>
        <text>{{ paying ? '正在拉起支付' : '微信支付' }}</text>
      </view>
      <view class="payment-btn payment-btn--cancel" @tap="onCancel">
        <text>取消支付</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { post } from '@/utils/request'
import Countdown from '@/components/countdown/index.vue'

const orderId = ref('')
const amount = ref(0)
const orderNo = ref('')
const expiredAt = ref('')
const paying = ref(false)

onLoad((options) => {
  orderId.value = options?.order_id || ''
  amount.value = Number(options?.amount || 0)
  orderNo.value = options?.order_no || ''
  expiredAt.value = new Date(Date.now() + 30 * 60 * 1000).toISOString()
})

interface WechatPayParams {
  appId?: string
  timeStamp: string
  nonceStr: string
  package: string
  signType: string
  paySign: string
}

/** 微信支付 */
async function onWechatPay() {
  if (paying.value) return
  paying.value = true

  uni.showLoading({ title: '拉起支付...' })

  try {
    if (!orderId.value) {
      throw new Error('缺少订单信息')
    }

    const payParams = await post<WechatPayParams>(
      `/orders/${orderId.value}/pay`,
      { payment_method: 'wechat_pay' },
      { showError: false },
    )
    uni.hideLoading()

    await requestWechatPayment(payParams)

    uni.redirectTo({
      url: `/pages/payment-result/index?status=success&order_id=${orderId.value}`,
    })
  } catch (err) {
    uni.hideLoading()
    const errMsg = err instanceof Error ? err.message : ''
    const message = isPaymentCancel(errMsg)
      ? '已取消支付'
      : errMsg || '支付请求失败，请稍后重试'
    uni.showToast({ title: message, icon: 'none' })
  } finally {
    paying.value = false
  }
}

function requestWechatPayment(params: WechatPayParams): Promise<void> {
  return new Promise((resolve, reject) => {
    uni.requestPayment({
      provider: 'wxpay',
      timeStamp: params.timeStamp,
      nonceStr: params.nonceStr,
      package: params.package,
      signType: params.signType,
      paySign: params.paySign,
      success: () => resolve(),
      fail: (err) => reject(new Error(err.errMsg || 'requestPayment failed')),
    })
  })
}

function isPaymentCancel(message: string): boolean {
  return message.includes('cancel') || message.includes('取消')
}

/** 取消支付 */
function onCancel() {
  uni.showModal({
    title: '提示',
    content: '确定放弃支付吗？订单将在30分钟后自动取消',
    success: (res) => {
      if (res.confirm) {
        uni.navigateBack()
      }
    },
  })
}

/** 倒计时结束 */
function onCountdownFinish() {
  uni.showModal({
    title: '提示',
    content: '支付超时，订单已取消',
    showCancel: false,
    success() {
      uni.navigateBack({ delta: 2 })
    },
  })
}
</script>

<style lang="scss" scoped>
.page-payment {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding: 32rpx;
}

.payment-card {
  padding: 48rpx 32rpx;
}

.payment-amount {
  text-align: center;
  padding-bottom: 40rpx;
  border-bottom: 1rpx solid #F0F0F0;

  &__label {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    display: block;
    margin-bottom: 16rpx;
  }

  &__value {
    display: flex;
    justify-content: center;
    align-items: baseline;
  }

  &__symbol {
    font-size: var(--font-size-xl);
    color: var(--color-text);
    font-weight: 700;
  }

  &__num {
    font-size: 72rpx;
    color: var(--color-text);
    font-weight: 700;
    margin-left: 4rpx;
  }
}

.payment-info {
  padding: 24rpx 0;

  &__row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12rpx 0;
  }

  &__label {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
  }

  &__value {
    font-size: var(--font-size-base);
    color: var(--color-text);
  }
}

.payment-mock-tip {
  display: flex;
  align-items: flex-start;
  gap: 8rpx;
  padding: 20rpx;
  background-color: rgba(33, 150, 243, 0.08);
  border-radius: var(--radius-md);
  margin-top: 16rpx;

  &__icon {
    font-size: 28rpx;
    flex-shrink: 0;
  }

  &__text {
    font-size: var(--font-size-sm);
    color: var(--color-blue);
    line-height: 1.5;
  }
}

.payment-actions {
  margin-top: 48rpx;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.payment-btn {
  height: 96rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: var(--radius-xl);
  font-size: var(--font-size-lg);
  font-weight: 600;
  gap: 12rpx;

  &:active { opacity: 0.85; transform: scale(0.98); }

  &__icon {
    font-size: 32rpx;
  }

  &--success {
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
    color: #fff;
  }

  &--fail {
    background: linear-gradient(135deg, #FF8A50, var(--color-orange));
    color: #fff;
  }

  &--cancel {
    background-color: var(--color-bg-grey);
    color: var(--color-text-secondary);
  }
}
</style>
