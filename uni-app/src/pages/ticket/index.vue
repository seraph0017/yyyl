<template>
  <!-- 电子票页面 -->
  <view class="page-ticket">
    <view class="ticket-card card" v-for="item in tickets" :key="item.id">
      <view class="ticket-top">
        <view class="ticket-info">
          <text class="ticket-name">{{ item.product_name }}</text>
          <text class="ticket-date">📅 {{ item.date }}</text>
          <text class="ticket-no">票号：{{ item.ticket_no }}</text>
        </view>
        <view :class="['ticket-status', `ticket-status--${item.status}`]">
          <text>{{ item.status === 'unused' ? '未使用' : item.status === 'used' ? '已使用' : '已过期' }}</text>
        </view>
      </view>
      <view class="ticket-divider">
        <view class="ticket-divider__circle ticket-divider__circle--left"></view>
        <view class="ticket-divider__line"></view>
        <view class="ticket-divider__circle ticket-divider__circle--right"></view>
      </view>
      <view class="ticket-qr" @tap="onPreviewQr(item.qrcode_token)">
        <view class="ticket-qr__placeholder">
          <text class="ticket-qr__icon">📱</text>
          <text class="ticket-qr__text">出示此二维码验票</text>
          <text class="ticket-qr__refresh">每30秒自动刷新</text>
        </view>
      </view>
    </view>

    <view class="ticket-tip">
      <text>💡 请在验票时出示二维码给工作人员扫描</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import type { ITicket } from '@/types'

const tickets = ref<ITicket[]>([])
const loading = ref(true)
let refreshTimer: ReturnType<typeof setInterval> | null = null

onLoad((options) => {
  loadTickets(options?.order_id || '1')
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

async function loadTickets(orderId: string) {
  try {
    await ensureLogin()
    const list = await get<ITicket[]>(`/orders/${orderId}/tickets`)
    tickets.value = list || []
    loading.value = false
    startQrRefresh()
  } catch {
    tickets.value = []
    loading.value = false
    uni.showToast({ title: '加载票信息失败', icon: 'error' })
  }
}

function startQrRefresh() {
  // 每30秒刷新二维码token
  refreshTimer = setInterval(async () => {
    for (const ticket of tickets.value) {
      if (ticket.status === 'unused') {
        try {
          const data = await post<{ qrcode_token: string }>(`/tickets/${ticket.id}/refresh-qr`)
          ticket.qrcode_token = data.qrcode_token
        } catch {
          // 静默失败，下次重试
        }
      }
    }
  }, 30000)
}

function onPreviewQr(token: string) {
  uni.showToast({ title: `票码：${token.substring(0, 10)}...`, icon: 'none' })
}
</script>

<style lang="scss" scoped>
.page-ticket { min-height: 100vh; background-color: var(--color-bg); padding: 24rpx; }

.ticket-card { margin-bottom: 24rpx; padding: 0; overflow: visible; }

.ticket-top { padding: 28rpx; display: flex; justify-content: space-between; align-items: flex-start; }

.ticket-info {
  flex: 1;
}

.ticket-name { font-size: var(--font-size-lg); font-weight: 700; color: var(--color-text); display: block; }
.ticket-date { font-size: var(--font-size-base); color: var(--color-text-secondary); display: block; margin-top: 8rpx; }
.ticket-no { font-size: var(--font-size-sm); color: var(--color-text-placeholder); display: block; margin-top: 4rpx; }

.ticket-status {
  padding: 6rpx 16rpx; border-radius: var(--radius-sm); font-size: var(--font-size-xs); font-weight: 500;
  &--unused { background-color: var(--color-primary-bg); text { color: var(--color-primary); } }
  &--used { background-color: var(--color-bg-grey); text { color: var(--color-text-placeholder); } }
  &--expired { background-color: rgba(229,57,53,0.08); text { color: var(--color-red); } }
}

.ticket-divider {
  display: flex; align-items: center; position: relative; margin: 0 -1rpx;
  &__circle { width: 32rpx; height: 32rpx; border-radius: 50%; background-color: var(--color-bg); z-index: 1;
    &--left { margin-left: -16rpx; }
    &--right { margin-right: -16rpx; }
  }
  &__line { flex: 1; height: 1rpx; border-top: 2rpx dashed #E0E0E0; }
}

.ticket-qr {
  padding: 32rpx; display: flex; justify-content: center;
  &__placeholder { display: flex; flex-direction: column; align-items: center; padding: 40rpx; background-color: var(--color-bg-light); border-radius: var(--radius-lg); width: 350rpx; }
  &__icon { font-size: 80rpx; margin-bottom: 16rpx; }
  &__text { font-size: var(--font-size-base); color: var(--color-text); font-weight: 500; }
  &__refresh { font-size: var(--font-size-xs); color: var(--color-text-placeholder); margin-top: 8rpx; }
}

.ticket-tip {
  text-align: center; padding: 32rpx;
  text { font-size: var(--font-size-sm); color: var(--color-text-placeholder); }
}
</style>
