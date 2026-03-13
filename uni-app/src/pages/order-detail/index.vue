<template>
  <!-- 订单详情页 -->
  <view class="page-order-detail" v-if="order">
    <!-- 状态卡片 -->
    <view class="status-card">
      <text class="status-card__text">{{ statusText }}</text>
      <view class="status-steps">
        <view
          :class="['status-step', item.active ? 'status-step--active' : '']"
          v-for="item in statusSteps"
          :key="item.label"
        >
          <view class="status-step__dot"></view>
          <text class="status-step__label">{{ item.label }}</text>
          <text class="status-step__time" v-if="item.time">{{ item.time }}</text>
        </view>
      </view>
    </view>

    <!-- 商品列表 -->
    <view class="detail-section card">
      <view class="detail-section__title">商品信息</view>
      <view class="order-product" v-for="item in order.items" :key="item.id">
        <view class="order-product__image"><text>🏕️</text></view>
        <view class="order-product__info">
          <text class="order-product__name">{{ item.product_name }}</text>
          <text class="order-product__date" v-if="item.date">📅 {{ item.date }}</text>
        </view>
        <view class="order-product__right">
          <text class="order-product__price">¥{{ item.actual_price }}</text>
          <text class="order-product__qty">x{{ item.quantity }}</text>
        </view>
      </view>
    </view>

    <!-- 费用明细 -->
    <view class="detail-section card">
      <view class="detail-section__title">费用明细</view>
      <view class="fee-line">
        <text>商品金额</text>
        <text>¥{{ order.total_amount + order.discount_amount }}</text>
      </view>
      <view class="fee-line fee-line--green" v-if="order.discount_amount > 0">
        <text>优惠</text>
        <text>-¥{{ order.discount_amount }}</text>
      </view>
      <view class="divider"></view>
      <view class="fee-line fee-line--bold">
        <text>实付金额</text>
        <text class="fee-total">¥{{ order.actual_amount }}</text>
      </view>
    </view>

    <!-- 订单信息 -->
    <view class="detail-section card">
      <view class="detail-section__title">订单信息</view>
      <view class="info-line">
        <text>订单编号</text>
        <view class="info-line__right">
          <text>{{ order.order_no }}</text>
          <text class="info-copy" @tap="onCopyOrderNo">复制</text>
        </view>
      </view>
      <view class="info-line">
        <text>下单时间</text>
        <text>{{ order.created_at }}</text>
      </view>
      <view class="info-line" v-if="order.paid_at">
        <text>支付时间</text>
        <text>{{ order.paid_at }}</text>
      </view>
    </view>

    <!-- 底部操作 -->
    <view class="detail-footer safe-bottom">
      <view class="detail-footer__btn detail-footer__btn--text" @tap="onContactService">
        <text>联系客服</text>
      </view>
      <view class="detail-footer__btn detail-footer__btn--outline" @tap="onRefund" v-if="order.status === 'paid'">
        <text>申请退款</text>
      </view>
      <view class="detail-footer__btn detail-footer__btn--primary" @tap="onViewTicket" v-if="order.status === 'paid'">
        <text>查看电子票</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import { getOrderStatusText, formatDate } from '@/utils/util'
import type { IOrder } from '@/types'

interface StatusStep {
  label: string
  time: string
  active: boolean
}

const order = ref<IOrder | null>(null)
const loading = ref(true)
const statusText = ref('')
const statusSteps = ref<StatusStep[]>([])

onLoad((options) => {
  loadOrder(options?.id || '1')
})

async function loadOrder(id: string) {
  try {
    await ensureLogin()
    const o = await get<IOrder>(`/orders/${id}`)
    order.value = o
    statusText.value = getOrderStatusText(o.status)
    loading.value = false

    // Build status steps dynamically
    const steps: StatusStep[] = [
      { label: '提交订单', time: o.created_at ? formatDate(o.created_at, 'MM-DD HH:mm') : '', active: true },
    ]
    if (o.paid_at) {
      steps.push({ label: '支付成功', time: formatDate(o.paid_at, 'MM-DD HH:mm'), active: true })
    } else {
      steps.push({ label: '支付成功', time: '', active: false })
    }
    steps.push({ label: '验票入营', time: '', active: o.status === 'verified' || o.status === 'completed' })
    steps.push({ label: '已完成', time: '', active: o.status === 'completed' })
    statusSteps.value = steps
  } catch {
    uni.showToast({ title: '加载订单详情失败', icon: 'error' })
  }
}

function onViewTicket() {
  uni.navigateTo({ url: `/pages/ticket/index?order_id=${order.value?.id}` })
}

function onRefund() {
  uni.showModal({
    title: '申请退款',
    content: '确定要申请退款吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await post(`/orders/${order.value?.id}/refund`)
          uni.showToast({ title: '退款申请已提交', icon: 'success' })
          loadOrder(String(order.value?.id))
        } catch {
          uni.showToast({ title: '退款申请失败', icon: 'error' })
        }
      }
    },
  })
}

function onContactService() {
  uni.navigateTo({ url: '/pages/customer-service/index' })
}

function onCopyOrderNo() {
  uni.setClipboardData({ data: order.value?.order_no || '' })
}
</script>

<style lang="scss" scoped>
.page-order-detail { min-height: 100vh; background-color: var(--color-bg); padding-bottom: 140rpx; }

.status-card {
  background: linear-gradient(135deg, #2E7D32, #4CAF50);
  padding: 40rpx 32rpx;
  &__text { font-size: var(--font-size-xxl); font-weight: 700; color: #fff; display: block; margin-bottom: 24rpx; }
}

.status-steps {
  display: flex; justify-content: space-between;
}

.status-step {
  display: flex; flex-direction: column; align-items: center; flex: 1;
  &__dot { width: 20rpx; height: 20rpx; border-radius: 50%; background-color: rgba(255,255,255,0.3); margin-bottom: 8rpx; }
  &__label { font-size: var(--font-size-xs); color: rgba(255,255,255,0.6); }
  &__time { font-size: 18rpx; color: rgba(255,255,255,0.5); margin-top: 4rpx; }
  &--active {
    .status-step__dot { background-color: #fff; }
    .status-step__label { color: #fff; font-weight: 500; }
    .status-step__time { color: rgba(255,255,255,0.8); }
  }
}

.detail-section {
  margin: 16rpx 24rpx; padding: 24rpx;
  &__title { font-size: var(--font-size-md); font-weight: 600; color: var(--color-text); margin-bottom: 20rpx; }
}

.order-product {
  display: flex; align-items: center; padding: 12rpx 0;
  &__image { width: 100rpx; height: 100rpx; background-color: var(--color-bg-light); border-radius: var(--radius-md); display: flex; justify-content: center; align-items: center; flex-shrink: 0; margin-right: 16rpx; text { font-size: 36rpx; } }
  &__info { flex: 1; min-width: 0; }
  &__name { font-size: var(--font-size-base); color: var(--color-text); font-weight: 500; display: block; }
  &__date { font-size: var(--font-size-sm); color: var(--color-text-secondary); display: block; margin-top: 4rpx; }
  &__right { text-align: right; flex-shrink: 0; margin-left: 16rpx; }
  &__price { font-size: var(--font-size-base); color: var(--color-text); font-weight: 500; display: block; }
  &__qty { font-size: var(--font-size-sm); color: var(--color-text-placeholder); }
}

.fee-line {
  display: flex; justify-content: space-between; padding: 10rpx 0;
  font-size: var(--font-size-base); color: var(--color-text-secondary);
  &--green text:last-child { color: var(--color-primary); }
  &--bold { font-weight: 600; text { color: var(--color-text); } }
}

.fee-total { color: var(--color-orange) !important; font-size: var(--font-size-xl); }

.info-line {
  display: flex; justify-content: space-between; align-items: center; padding: 10rpx 0;
  font-size: var(--font-size-base); color: var(--color-text-secondary);
  &__right { display: flex; align-items: center; gap: 12rpx; }
}

.info-copy {
  font-size: var(--font-size-sm); color: var(--color-primary); padding: 4rpx 12rpx;
  border: 1rpx solid var(--color-primary); border-radius: var(--radius-sm);
}

.detail-footer {
  position: fixed; bottom: 0; left: 0; right: 0;
  display: flex; justify-content: flex-end; align-items: center; gap: 16rpx;
  padding: 16rpx 32rpx; background-color: var(--color-bg-white);
  box-shadow: 0 -4rpx 16rpx rgba(0,0,0,0.06); z-index: 100;

  &__btn {
    height: 72rpx; padding: 0 32rpx; display: flex; justify-content: center; align-items: center;
    border-radius: var(--radius-round); font-size: var(--font-size-base); font-weight: 500;
    &--primary { background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary)); text { color: #fff; } }
    &--outline { border: 2rpx solid var(--color-text-placeholder); text { color: var(--color-text-secondary); } }
    &--text { text { color: var(--color-text-secondary); } }
    &:active { opacity: 0.7; }
  }
}
</style>
