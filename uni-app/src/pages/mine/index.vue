<template>
  <view class="page-mine">
    <!-- 用户头部区域 -->
    <view class="user-header">
      <!-- 已登录状态 -->
      <view class="user-info" v-if="userStore.isLoggedIn && userStore.userInfo">
        <view class="user-avatar">
          <image
            :src="userStore.userInfo.avatar_url"
            mode="aspectFill"
            v-if="userStore.userInfo.avatar_url"
          />
          <text class="user-avatar__placeholder" v-else>😊</text>
        </view>
        <view class="user-detail">
          <text class="user-name">{{ userStore.userInfo.nickname || '露营者' }}</text>
          <view class="user-tags">
            <view class="user-tag user-tag--member" v-if="userStore.userInfo.is_annual_member">
              <text>年卡会员</text>
            </view>
            <view class="user-tag" v-if="userStore.userInfo.is_staff">
              <text>员工</text>
            </view>
          </view>
        </view>
        <view class="user-settings" @tap="onEditProfile">
          <text>编辑资料 ›</text>
        </view>
      </view>

      <!-- 未登录状态 -->
      <view class="user-login" v-else>
        <view class="user-avatar">
          <text class="user-avatar__placeholder">🏕️</text>
        </view>
        <view class="user-login__content">
          <text class="user-login__title">欢迎来到{{ brandConfig.name }}</text>
          <button class="user-login__btn" @tap="onLogin">微信快捷登录</button>
        </view>
      </view>
    </view>

    <!-- 数据统计 -->
    <view class="order-section card" v-if="userStore.isLoggedIn && userStore.userInfo">
      <view class="section-header">
        <text class="section-header__title">我的订单</text>
        <view class="section-header__more" @tap="onGoOrders">
          <text>全部订单</text>
          <text class="section-header__arrow">›</text>
        </view>
      </view>
      <view class="order-menu">
        <view
          class="order-menu__item"
          v-for="item in orderMenuItems"
          :key="item.key"
          @tap="onOrderMenuTap(item.key)"
        >
          <view class="order-menu__icon-wrap">
            <text class="order-menu__icon">{{ item.icon }}</text>
            <view class="order-menu__badge" v-if="item.badge">
              <text>{{ item.badge }}</text>
            </view>
          </view>
          <text class="order-menu__name">{{ item.name }}</text>
        </view>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="func-section card">
      <view
        class="func-item"
        v-for="item in menuItems"
        :key="item.key"
        @tap="onMenuTap(item.url)"
      >
        <view class="func-item__left">
          <text class="func-item__icon">{{ item.icon }}</text>
          <text class="func-item__label">{{ item.label }}</text>
        </view>
        <view class="func-item__right">
          <text class="func-item__badge" v-if="item.badge">{{ item.badge }}</text>
          <text class="func-item__arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 员工入口 -->
    <view
      class="staff-entry card"
      v-if="userStore.isLoggedIn && userStore.isStaff"
      @tap="onStaffEntry"
    >
      <view class="staff-entry__left">
        <text class="staff-entry__icon">📱</text>
        <text class="staff-entry__text">员工核销</text>
      </view>
      <text class="staff-entry__arrow">›</text>
    </view>

    <!-- 退出登录 -->
    <view class="logout-section" v-if="userStore.isLoggedIn">
      <view class="logout-btn" @tap="onLogout">
        <text>退出登录</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onShareAppMessage } from '@dcloudio/uni-app'
import { useUserStore } from '@/store/user'
import { wxLogin, phoneLogin, logout, checkLoginStatus } from '@/utils/auth'
import { get } from '@/utils/request'
import { brandConfig } from '@/config/sites'
import type { IUserInfo } from '@/types'

interface IMenuItem {
  key: string
  icon: string
  label: string
  badge?: number
  url: string
}

interface IOrderMenuItem {
  key: string
  icon: string
  name: string
  badge?: number
}

// ---- Store ----
const userStore = useUserStore()

// ---- 订单快捷菜单 ----
const orderMenuItems = ref<IOrderMenuItem[]>([
  { key: 'pending_payment', icon: '💰', name: '待支付' },
  { key: 'paid', icon: '📋', name: '待使用' },
  { key: 'completed', icon: '✅', name: '已完成' },
  { key: 'refunding', icon: '🔄', name: '售后' },
])

// ---- 功能菜单 ----
const menuItems = ref<IMenuItem[]>([
  { key: 'member', icon: '👑', label: '会员中心', url: '/pages/member/index' },
  { key: 'ticket', icon: '🎫', label: '我的票', url: '/pages/ticket/index' },
  { key: 'address', icon: '📍', label: '收货地址', url: '/pages/address/index' },
  { key: 'identity', icon: '👤', label: '出行人信息', url: '/pages/identity/index' },
  { key: 'service', icon: '💬', label: '帮助与客服', url: '/pages/customer-service/index' },
])

// ---- 生命周期 ----
onShow(() => {
  refreshLoginState()
})

onShareAppMessage(() => {
  return {
    title: brandConfig.shareTitle,
    path: '/pages/index/index',
  }
})

// ---- 登录状态 ----
async function refreshLoginState() {
  userStore.restoreFromStorage()
  // 如果已登录，从后端刷新用户信息
  if (checkLoginStatus()) {
    try {
      const userInfo = await get<IUserInfo>('/users/me')
      if (userInfo) {
        userStore.setUser(userInfo)
        uni.setStorageSync('user_info', JSON.stringify(userInfo))
      }
    } catch {
      // 静默失败，使用本地缓存
    }
  }
}

// ---- 登录 ----
async function onLogin() {
  try {
    await wxLogin()
    refreshLoginState()
    uni.showToast({ title: '登录成功', icon: 'success' })
  } catch (err) {
    console.error('登录失败:', err)
    uni.showToast({ title: '登录失败，请重试', icon: 'none' })
  }
}

// ---- 手机号登录 ----
async function onPhoneLogin(e: { detail: { code?: string; errMsg: string } }) {
  try {
    const result = await phoneLogin(e)
    if (result) {
      refreshLoginState()
      uni.showToast({ title: '登录成功', icon: 'success' })
    }
  } catch (err) {
    console.error('手机号登录失败:', err)
  }
}

// ---- 退出登录 ----
function onLogout() {
  uni.showModal({
    title: '提示',
    content: '确定要退出登录吗？',
    success: (res) => {
      if (res.confirm) {
        logout()
        refreshLoginState()
        uni.showToast({ title: '已退出', icon: 'success' })
      }
    },
  })
}

// ---- 菜单点击 ----
function onMenuTap(url: string) {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  uni.navigateTo({ url })
}

// ---- 订单快捷入口 ----
function onOrderMenuTap(tabKey: string) {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  const tabIndexMap: Record<string, number> = {
    pending_payment: 1,
    paid: 2,
    completed: 3,
    refunding: 4,
  }
  const tabIndex = tabIndexMap[tabKey] ?? 0
  uni.switchTab({ url: '/pages/order/index' })
}

// ---- 全部订单 ----
function onGoOrders() {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  uni.switchTab({ url: '/pages/order/index' })
}

// ---- 编辑资料 ----
function onEditProfile() {
  uni.navigateTo({ url: '/pages/profile/index' })
}

// ---- 员工入口 ----
function onStaffEntry() {
  uni.navigateTo({ url: '/pages/staff/index' })
}
</script>

<style lang="scss" scoped>
.page-mine {
  min-height: 100vh;
  background-color: var(--color-bg);
}

/* 用户信息头部 */
.user-header {
  background: linear-gradient(180deg, var(--color-primary) 0%, var(--color-primary-light) 60%, var(--color-bg) 100%);
  padding: 32rpx 32rpx 48rpx;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  background-color: rgba(255, 255, 255, 0.2);
  display: flex;
  justify-content: center;
  align-items: center;
  border: 4rpx solid rgba(255, 255, 255, 0.3);

  image {
    width: 100%;
    height: 100%;
  }

  &__placeholder {
    font-size: 56rpx;
  }
}

.user-detail {
  flex: 1;
  margin-left: 24rpx;
  min-width: 0;
}

.user-name {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: #fff;
  display: block;
}

.user-tags {
  display: flex;
  gap: 12rpx;
  margin-top: 8rpx;
}

.user-tag {
  display: inline-flex;
  align-items: center;
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
  background-color: rgba(255, 255, 255, 0.2);

  text {
    font-size: var(--font-size-xs);
    color: #fff;
  }

  &--member {
    background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(255, 165, 0, 0.3));
  }
}

.user-settings {
  padding: 12rpx;

  text {
    font-size: var(--font-size-sm);
    color: rgba(255, 255, 255, 0.8);
  }
}

/* 未登录状态 */
.user-login {
  display: flex;
  align-items: center;
  padding: 20rpx 0;

  &__content {
    margin-left: 24rpx;
    flex: 1;
  }

  &__title {
    font-size: var(--font-size-lg);
    color: #fff;
    font-weight: 500;
    display: block;
    margin-bottom: 12rpx;
  }

  &__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 60rpx;
    padding: 0 32rpx;
    background-color: rgba(255, 255, 255, 0.25);
    color: #fff;
    font-size: var(--font-size-sm);
    border-radius: var(--radius-round);
    border: none;
    font-weight: 500;
    line-height: 60rpx;

    &::after {
      border: none;
    }
  }
}

/* 订单入口 */
.order-section {
  margin: -16rpx 32rpx 20rpx;
  padding: 24rpx;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;

  &__title {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  &__more {
    display: flex;
    align-items: center;

    text {
      font-size: var(--font-size-sm);
      color: var(--color-text-placeholder);
    }
  }

  &__arrow {
    font-size: var(--font-size-lg);
    margin-left: 4rpx;
  }
}

.order-menu {
  display: flex;
  justify-content: space-around;

  &__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8rpx;

    &:active {
      opacity: 0.7;
    }
  }

  &__icon-wrap {
    position: relative;
    margin-bottom: 8rpx;
  }

  &__icon {
    font-size: 44rpx;
  }

  &__badge {
    position: absolute;
    top: -8rpx;
    right: -16rpx;
    min-width: 32rpx;
    height: 32rpx;
    padding: 0 8rpx;
    background-color: var(--color-red);
    border-radius: 16rpx;
    display: flex;
    justify-content: center;
    align-items: center;

    text {
      font-size: 18rpx;
      color: #fff;
      font-weight: 600;
    }
  }

  &__name {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
  }
}

/* 功能菜单 */
.func-section {
  margin: 0 32rpx 20rpx;
  padding: 8rpx 24rpx;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.func-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 0;
  border-bottom: 1rpx solid #f5f5f5;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    opacity: 0.7;
  }

  &__left {
    display: flex;
    align-items: center;
    gap: 16rpx;
  }

  &__icon {
    font-size: 36rpx;
  }

  &__label {
    font-size: var(--font-size-base);
    color: var(--color-text);
  }

  &__right {
    display: flex;
    align-items: center;
    gap: 8rpx;
  }

  &__badge {
    min-width: 32rpx;
    height: 32rpx;
    padding: 0 8rpx;
    background-color: var(--color-red);
    border-radius: 16rpx;
    font-size: 18rpx;
    color: #fff;
    text-align: center;
    line-height: 32rpx;
  }

  &__arrow {
    font-size: var(--font-size-xl);
    color: var(--color-text-placeholder);
  }
}

/* 员工入口 */
.staff-entry {
  margin: 0 32rpx 20rpx;
  padding: 28rpx 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);

  &:active {
    opacity: 0.85;
  }

  &__left {
    display: flex;
    align-items: center;
    gap: 12rpx;
  }

  &__icon {
    font-size: 36rpx;
  }

  &__text {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  &__arrow {
    font-size: var(--font-size-xl);
    color: var(--color-text-placeholder);
  }
}

/* 退出登录 */
.logout-section {
  padding: 40rpx 32rpx 80rpx;
}

.logout-btn {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 88rpx;
  border-radius: var(--radius-xl);
  background-color: var(--color-bg-card);
  box-shadow: var(--shadow-sm);

  text {
    font-size: var(--font-size-base);
    color: var(--color-red);
  }

  &:active {
    opacity: 0.7;
  }
}
</style>
