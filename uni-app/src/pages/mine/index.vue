<template>
  <view class="page-mine">
    <!-- 沉浸式用户头部 -->
    <view class="user-header">
      <view class="user-header__bg" />
      <view class="user-header__pattern" />

      <!-- 已登录状态 -->
      <view class="user-header__content" v-if="userStore.isLoggedIn && userStore.userInfo">
        <view class="user-info">
          <view class="user-avatar">
            <image
              :src="userStore.userInfo.avatar_url"
              mode="aspectFill"
              v-if="userStore.userInfo.avatar_url"
            />
            <text class="user-avatar__placeholder" v-else>😊</text>
            <view class="user-avatar__ring" />
          </view>
          <view class="user-detail">
            <text class="user-name">{{ userStore.userInfo.nickname || '露营者' }}</text>
            <view class="user-tags">
              <view class="user-tag user-tag--gold" v-if="userStore.userInfo.is_annual_member">
                <text>👑 年卡会员</text>
              </view>
              <view class="user-tag" v-if="userStore.userInfo.is_staff">
                <text>🔧 员工</text>
              </view>
            </view>
          </view>
          <view class="user-settings" @tap="onEditProfile">
            <text>编辑</text>
          </view>
        </view>
      </view>

      <!-- 未登录状态 -->
      <view class="user-header__content user-header__content--guest" v-else>
        <view class="user-login">
          <view class="user-avatar user-avatar--guest">
            <text class="user-avatar__placeholder">🏕️</text>
          </view>
          <view class="user-login__content">
            <text class="user-login__title">欢迎来到{{ brandConfig.name }}</text>
            <text class="user-login__subtitle">登录解锁更多露营体验</text>
          </view>
          <button class="user-login__btn" @tap="onLogin">
            <text>登录</text>
          </button>
        </view>
      </view>
    </view>

    <!-- 订单快捷入口 -->
    <view class="order-section" v-if="userStore.isLoggedIn && userStore.userInfo">
      <view class="order-card">
        <view class="order-card__header">
          <text class="order-card__title">我的订单</text>
          <view class="order-card__more" @tap="onGoOrders">
            <text>全部</text>
            <text class="order-card__arrow">›</text>
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
    </view>

    <!-- 功能菜单 -->
    <view class="func-section" :class="{ 'func-section--no-order': !userStore.isLoggedIn || !userStore.userInfo }">
      <view class="func-card">
        <view
          class="func-item"
          v-for="(item, index) in menuItems"
          :key="item.key"
          @tap="onMenuTap(item.url)"
        >
          <view class="func-item__left">
            <view class="func-item__icon-wrap" :style="{ background: iconBgs[index] }">
              <text class="func-item__icon">{{ item.icon }}</text>
            </view>
            <text class="func-item__label">{{ item.label }}</text>
          </view>
          <view class="func-item__right">
            <text class="func-item__badge" v-if="item.badge">{{ item.badge }}</text>
            <text class="func-item__arrow">›</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 员工入口 -->
    <view
      class="staff-entry"
      v-if="userStore.isLoggedIn && userStore.isStaff"
      @tap="onStaffEntry"
    >
      <view class="staff-entry__card">
        <view class="staff-entry__left">
          <view class="staff-entry__icon-wrap">
            <text class="staff-entry__icon">📱</text>
          </view>
          <view class="staff-entry__info">
            <text class="staff-entry__title">员工核销</text>
            <text class="staff-entry__desc">扫码验票</text>
          </view>
        </view>
        <text class="staff-entry__arrow">›</text>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-section" v-if="userStore.isLoggedIn">
      <view class="logout-btn" @tap="onLogout">
        <text>退出登录</text>
      </view>
    </view>

    <!-- 品牌底部 -->
    <view class="brand-footer">
      <text class="brand-footer__icon">🏕️</text>
      <text class="brand-footer__name">{{ brandConfig.name }}</text>
      <text class="brand-footer__slogan">山野有归处 · 生活有光芒</text>
    </view>

    <view class="safe-bottom" />
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

const userStore = useUserStore()

const iconBgs = [
  'linear-gradient(135deg, #f8f0dc, #f2e4c4)',
  'linear-gradient(135deg, #e8f0e8, #d4e8d4)',
  'linear-gradient(135deg, #e8eef4, #d4e0ec)',
  'linear-gradient(135deg, #f4ece8, #ecd8d0)',
  'linear-gradient(135deg, #ede8f4, #dcd0ec)',
]

const orderMenuItems = ref<IOrderMenuItem[]>([
  { key: 'pending_payment', icon: '💰', name: '待支付' },
  { key: 'paid', icon: '📋', name: '待使用' },
  { key: 'completed', icon: '✅', name: '已完成' },
  { key: 'refunding', icon: '🔄', name: '售后' },
])

const menuItems = ref<IMenuItem[]>([
  { key: 'member', icon: '👑', label: '会员中心', url: '/pages/member/index' },
  { key: 'ticket', icon: '🎫', label: '我的票', url: '/pages/ticket/index' },
  { key: 'address', icon: '📍', label: '收货地址', url: '/pages/address/index' },
  { key: 'identity', icon: '👤', label: '出行人信息', url: '/pages/identity/index' },
  { key: 'service', icon: '💬', label: '帮助与客服', url: '/pages/customer-service/index' },
])

onShow(() => {
  refreshLoginState()
})

onShareAppMessage(() => {
  return {
    title: brandConfig.shareTitle,
    path: '/pages/index/index',
  }
})

async function refreshLoginState() {
  userStore.restoreFromStorage()
  if (checkLoginStatus()) {
    try {
      const userInfo = await get<IUserInfo>('/users/me')
      if (userInfo) {
        userStore.setUser(userInfo)
        uni.setStorageSync('user_info', JSON.stringify(userInfo))
      }
    } catch {
      // 静默失败
    }
  }
}

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

function onMenuTap(url: string) {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  uni.navigateTo({ url })
}

function onOrderMenuTap(tabKey: string) {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  uni.switchTab({ url: '/pages/order/index' })
}

function onGoOrders() {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  uni.switchTab({ url: '/pages/order/index' })
}

function onEditProfile() {
  uni.navigateTo({ url: '/pages/profile/index' })
}

function onStaffEntry() {
  uni.navigateTo({ url: '/pages/staff/index' })
}
</script>

<style lang="scss" scoped>
.page-mine {
  min-height: 100vh;
  background-color: var(--color-bg);
}

/* ========== 沉浸式用户头部 ========== */
.user-header {
  position: relative;
  overflow: hidden;

  &__bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      170deg,
      #1e3a2f 0%,
      var(--color-primary) 40%,
      var(--color-primary-light) 75%,
      var(--color-bg) 100%
    );
  }

  &__pattern {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 40% at 80% 30%, rgba(200, 168, 114, 0.1) 0%, transparent 60%),
      radial-gradient(circle at 10% 80%, rgba(255, 255, 255, 0.04) 0%, transparent 40%);
    pointer-events: none;
  }

  &__content {
    position: relative;
    z-index: 1;
    padding: 32rpx 36rpx 56rpx;
    padding-top: calc(env(safe-area-inset-top, 0px) + 32rpx);
  }

  &__content--guest {
    padding-bottom: 64rpx;
  }
}

.user-info {
  display: flex;
  align-items: center;
}

.user-avatar {
  width: 128rpx;
  height: 128rpx;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;

  image {
    width: 100%;
    height: 100%;
  }

  &__placeholder {
    font-size: 56rpx;
  }

  &__ring {
    position: absolute;
    inset: -4rpx;
    border-radius: 50%;
    border: 3rpx solid rgba(200, 168, 114, 0.5);
    pointer-events: none;
  }

  &--guest {
    width: 112rpx;
    height: 112rpx;
    background: rgba(255, 255, 255, 0.12);
  }
}

.user-detail {
  flex: 1;
  margin-left: 28rpx;
  min-width: 0;
}

.user-name {
  font-size: var(--font-size-xxl);
  font-weight: 800;
  color: #fffefa;
  display: block;
  letter-spacing: 2rpx;
}

.user-tags {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}

.user-tag {
  display: inline-flex;
  align-items: center;
  padding: 4rpx 16rpx;
  border-radius: var(--radius-round);
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  border: 1rpx solid rgba(255, 255, 255, 0.15);

  text {
    font-size: var(--font-size-xs);
    color: rgba(255, 255, 255, 0.9);
    letter-spacing: 1rpx;
  }

  &--gold {
    background: linear-gradient(135deg, rgba(200, 168, 114, 0.25), rgba(200, 168, 114, 0.15));
    border-color: rgba(200, 168, 114, 0.3);

    text {
      color: var(--color-accent-light);
    }
  }
}

.user-settings {
  padding: 16rpx 24rpx;
  background: rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-round);
  border: 1rpx solid rgba(255, 255, 255, 0.15);

  text {
    font-size: var(--font-size-sm);
    color: rgba(255, 255, 255, 0.8);
    letter-spacing: 1rpx;
  }
}

/* ========== 未登录 ========== */
.user-login {
  display: flex;
  align-items: center;

  &__content {
    flex: 1;
    margin-left: 24rpx;
  }

  &__title {
    font-size: var(--font-size-xl);
    color: #fffefa;
    font-weight: 700;
    display: block;
    letter-spacing: 2rpx;
  }

  &__subtitle {
    font-size: var(--font-size-xs);
    color: rgba(255, 255, 255, 0.5);
    margin-top: 6rpx;
    display: block;
    letter-spacing: 1rpx;
  }

  &__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 68rpx;
    padding: 0 36rpx;
    background: linear-gradient(135deg, var(--color-accent), #b8944e);
    color: #fff;
    font-size: var(--font-size-sm);
    border-radius: var(--radius-round);
    border: none;
    font-weight: 600;
    letter-spacing: 2rpx;
    box-shadow: 0 4rpx 16rpx rgba(200, 168, 114, 0.3);

    &::after {
      border: none;
    }
  }
}

/* ========== 订单入口 ========== */
.order-section {
  padding: 0 36rpx;
  margin-top: -24rpx;
}

.order-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  padding: 28rpx;
  box-shadow: var(--shadow-md);
  border: 1rpx solid rgba(42, 37, 32, 0.04);

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24rpx;
  }

  &__title {
    font-size: var(--font-size-md);
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: 1rpx;
  }

  &__more {
    display: flex;
    align-items: center;
    gap: 4rpx;

    text {
      font-size: var(--font-size-sm);
      color: var(--color-text-placeholder);
    }
  }

  &__arrow {
    font-size: var(--font-size-lg);
  }
}

.order-menu {
  display: flex;
  justify-content: space-around;

  &__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8rpx 16rpx;
    transition: var(--transition-base);

    &:active {
      transform: scale(0.92);
    }
  }

  &__icon-wrap {
    position: relative;
    margin-bottom: 12rpx;
  }

  &__icon {
    font-size: 44rpx;
  }

  &__badge {
    position: absolute;
    top: -10rpx;
    right: -20rpx;
    min-width: 32rpx;
    height: 32rpx;
    padding: 0 8rpx;
    background: linear-gradient(135deg, var(--color-red), #a04030);
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
    letter-spacing: 0.5rpx;
  }
}

/* ========== 功能菜单 ========== */
.func-section {
  padding: 20rpx 36rpx 0;

  &--no-order {
    margin-top: -24rpx;
  }
}

.func-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  padding: 0 28rpx;
  box-shadow: var(--shadow-md);
  border: 1rpx solid rgba(42, 37, 32, 0.04);
}

.func-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 88rpx;
  border-bottom: 1rpx solid rgba(42, 37, 32, 0.04);
  transition: var(--transition-base);

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

  &__icon-wrap {
    width: 52rpx;
    height: 52rpx;
    border-radius: var(--radius-md);
    display: flex;
    justify-content: center;
    align-items: center;
  }

  &__icon {
    font-size: 26rpx;
  }

  &__label {
    font-size: var(--font-size-base);
    color: var(--color-text);
    font-weight: 500;
    letter-spacing: 1rpx;
  }

  &__right {
    display: flex;
    align-items: center;
    gap: 8rpx;
  }

  &__badge {
    min-width: 32rpx;
    height: 32rpx;
    padding: 0 10rpx;
    background: linear-gradient(135deg, var(--color-red), #a04030);
    border-radius: 16rpx;
    font-size: 18rpx;
    color: #fff;
    text-align: center;
    line-height: 32rpx;
    font-weight: 600;
  }

  &__arrow {
    font-size: var(--font-size-xl);
    color: var(--color-text-placeholder);
  }
}

/* ========== 员工入口 ========== */
.staff-entry {
  padding: 20rpx 36rpx 0;

  &__card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24rpx 28rpx;
    background: linear-gradient(135deg, #f3ede4, #faf6f0);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-sm);
    border: 1rpx solid rgba(200, 168, 114, 0.12);

    &:active {
      opacity: 0.85;
    }
  }

  &__left {
    display: flex;
    align-items: center;
    gap: 16rpx;
  }

  &__icon-wrap {
    width: 72rpx;
    height: 72rpx;
    border-radius: var(--radius-lg);
    background: linear-gradient(135deg, var(--color-primary-bg), rgba(45, 74, 62, 0.08));
    display: flex;
    justify-content: center;
    align-items: center;
  }

  &__icon {
    font-size: 32rpx;
  }

  &__info {
    display: flex;
    flex-direction: column;
  }

  &__title {
    font-size: var(--font-size-md);
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: 1rpx;
  }

  &__desc {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    margin-top: 4rpx;
  }

  &__arrow {
    font-size: var(--font-size-xl);
    color: var(--color-text-placeholder);
  }
}

/* ========== 退出登录 ========== */
.logout-section {
  padding: 48rpx 36rpx 40rpx;
}

.logout-btn {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 88rpx;
  border-radius: var(--radius-xl);
  background: var(--color-bg-card);
  box-shadow: var(--shadow-sm);
  border: 1rpx solid rgba(42, 37, 32, 0.04);

  text {
    font-size: var(--font-size-base);
    color: var(--color-red);
    letter-spacing: 2rpx;
  }

  &:active {
    opacity: 0.7;
    transform: scale(0.98);
  }
}

/* ========== 品牌底部 ========== */
.brand-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 0 40rpx;

  &__icon {
    font-size: 48rpx;
    margin-bottom: 16rpx;
    opacity: 0.6;
  }

  &__name {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    letter-spacing: 4rpx;
    font-weight: 500;
  }

  &__slogan {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    opacity: 0.6;
    margin-top: 8rpx;
    letter-spacing: 2rpx;
  }
}
</style>
