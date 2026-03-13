<template>
  <view class="page-staff">
    <!-- 今日数据 -->
    <view class="staff-stats">
      <view class="staff-stat"><text class="staff-stat__num">{{ todayStats.orders }}</text><text class="staff-stat__label">今日订单</text></view>
      <view class="staff-stat"><text class="staff-stat__num">¥{{ todayStats.revenue }}</text><text class="staff-stat__label">今日收入</text></view>
      <view class="staff-stat"><text class="staff-stat__num">{{ todayStats.visitors }}</text><text class="staff-stat__label">在营人数</text></view>
      <view class="staff-stat">
        <text :class="['staff-stat__num', todayStats.alerts > 0 ? 'staff-stat__num--alert' : '']">{{ todayStats.alerts }}</text>
        <text class="staff-stat__label">库存告警</text>
      </view>
    </view>
    <!-- 功能菜单 -->
    <view class="staff-menus">
      <view class="staff-menu card" v-for="item in menus" :key="item.key" @tap="onMenuTap(item.key)">
        <text class="staff-menu__icon">{{ item.icon }}</text>
        <view class="staff-menu__content">
          <text class="staff-menu__name">{{ item.name }}</text>
          <text class="staff-menu__desc">{{ item.desc }}</text>
        </view>
        <text class="staff-menu__arrow">›</text>
      </view>
    </view>
    <!-- 验票结果弹窗 -->
    <view class="verify-mask" v-if="showVerifyResult" @tap="onCloseResult">
      <view class="verify-popup card" @tap.stop>
        <view class="verify-success" v-if="verifyResult?.status === 'success'">
          <text class="verify-icon">✅</text>
          <text class="verify-title">验票成功</text>
          <view class="verify-info">
            <view class="verify-row"><text>姓名</text><text>{{ verifyResult.name }}</text></view>
            <view class="verify-row"><text>商品</text><text>{{ verifyResult.product }}</text></view>
            <view class="verify-row"><text>日期</text><text>{{ verifyResult.date }}</text></view>
          </view>
          <view class="verify-code-section" v-if="verifyResult.isMember === 'true'">
            <text class="verify-code-label">👑 年卡会员 — 验证码</text>
            <text class="verify-code-num">{{ verifyCode }}</text>
            <text class="verify-code-tip">请让用户在手机上输入此验证码</text>
          </view>
        </view>
        <view class="verify-close" @tap="onCloseResult"><text>关闭</text></view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { post, get } from '@/utils/request'

const todayStats = reactive({ orders: 0, revenue: 0, visitors: 0, alerts: 0 })
const menus = ref([
  { key: 'scan', name: '扫码验票', icon: '📷', desc: '扫描用户电子票二维码' },
  { key: 'orders', name: '查看订单', icon: '📋', desc: '查看今日订单列表' },
  { key: 'stock', name: '库存查看', icon: '📦', desc: '查看当前库存状态' },
])
const verifyCode = ref('')
const showVerifyResult = ref(false)
const verifyResult = ref<Record<string, string> | null>(null)

function onScanVerify() {
  uni.scanCode({
    onlyFromCamera: true,
    success: async (res) => {
      try {
        const data = await post<Record<string, string>>('/staff/tickets/scan', { qr_content: res.result })
        showVerifyResult.value = true
        verifyResult.value = data
        verifyCode.value = data.verify_code || ''
      } catch {
        uni.showToast({ title: '验票失败', icon: 'error' })
      }
    },
    fail: () => { uni.showToast({ title: '扫码取消', icon: 'none' }) },
  })
}

function onMenuTap(key: string) {
  if (key === 'scan') { onScanVerify() } else { uni.showToast({ title: '功能开发中', icon: 'none' }) }
}

function onCloseResult() { showVerifyResult.value = false; verifyResult.value = null; verifyCode.value = '' }
</script>

<style lang="scss" scoped>
.page-staff { min-height: 100vh; background-color: var(--color-bg); }
.staff-stats { display: flex; padding: 32rpx 24rpx; background: linear-gradient(135deg, #2E7D32, #4CAF50); }
.staff-stat {
  flex: 1; text-align: center;
  &__num { font-size: var(--font-size-xxl); font-weight: 700; color: #fff; display: block; &--alert { color: #FFC107; } }
  &__label { font-size: var(--font-size-xs); color: rgba(255,255,255,0.7); }
}
.staff-menus { padding: 24rpx; }
.staff-menu {
  display: flex; align-items: center; padding: 28rpx 24rpx; margin-bottom: 16rpx;
  &:active { opacity: 0.85; }
  &__icon { font-size: 48rpx; margin-right: 20rpx; }
  &__content { flex: 1; }
  &__name { font-size: var(--font-size-md); font-weight: 600; color: var(--color-text); display: block; }
  &__desc { font-size: var(--font-size-sm); color: var(--color-text-placeholder); display: block; margin-top: 4rpx; }
  &__arrow { font-size: var(--font-size-xl); color: var(--color-text-placeholder); }
}
.verify-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.verify-popup { width: 85%; padding: 40rpx 32rpx; text-align: center; }
.verify-icon { font-size: 100rpx; display: block; margin-bottom: 16rpx; }
.verify-title { font-size: var(--font-size-xl); font-weight: 700; display: block; margin-bottom: 24rpx; }
.verify-info { text-align: left; margin-bottom: 24rpx; }
.verify-row { display: flex; justify-content: space-between; padding: 12rpx 0; font-size: var(--font-size-base); border-bottom: 1rpx solid #F5F5F5;
  text:first-child { color: var(--color-text-secondary); } text:last-child { color: var(--color-text); font-weight: 500; }
}
.verify-code-section { padding: 24rpx; background: linear-gradient(135deg, #1A1A1A, #333); border-radius: var(--radius-lg); margin-top: 16rpx; }
.verify-code-label { font-size: var(--font-size-base); color: #FFD700; display: block; margin-bottom: 12rpx; }
.verify-code-num { font-size: 72rpx; font-weight: 700; color: #fff; letter-spacing: 16rpx; display: block; }
.verify-code-tip { font-size: var(--font-size-sm); color: rgba(255,255,255,0.5); display: block; margin-top: 8rpx; }
.verify-close { margin-top: 24rpx; text { font-size: var(--font-size-base); color: var(--color-primary); font-weight: 500; } &:active { opacity: 0.7; } }
</style>
