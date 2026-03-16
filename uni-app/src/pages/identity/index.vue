<template>
  <view class="page-identity">
    <!-- 顶部装饰 -->
    <view class="page-header">
      <view class="page-header__bg" />
      <view class="page-header__content">
        <text class="page-header__title">出行人管理</text>
        <text class="page-header__desc">管理您的出行人信息，下单时快速选择</text>
      </view>
    </view>

    <!-- 出行人列表 -->
    <view class="identity-list" v-if="identities.length > 0">
      <view
        :class="['identity-card', 'card', item.is_default ? 'identity-card--default' : '']"
        v-for="item in identities"
        :key="item.id"
      >
        <!-- 默认标识角标 -->
        <view class="identity-card__badge" v-if="item.is_default">
          <text>默认</text>
        </view>

        <view class="identity-card__body">
          <!-- 头像区 -->
          <view class="identity-card__avatar">
            <text>{{ item.name.charAt(0) }}</text>
          </view>

          <!-- 信息区 -->
          <view class="identity-card__info">
            <view class="identity-card__name-row">
              <text class="identity-card__name">{{ item.name }}</text>
            </view>
            <view class="identity-card__detail-row">
              <view class="identity-card__detail-item">
                <text class="identity-card__detail-icon">🪪</text>
                <text class="identity-card__detail-text">{{ maskIdCard(item.id_card) }}</text>
              </view>
              <view class="identity-card__detail-item" v-if="item.phone">
                <text class="identity-card__detail-icon">📱</text>
                <text class="identity-card__detail-text">{{ maskPhone(item.phone) }}</text>
              </view>
            </view>
          </view>
        </view>

        <!-- 操作栏 -->
        <view class="identity-card__footer">
          <view class="identity-card__action" @tap="onSetDefault(item)" v-if="!item.is_default">
            <text class="identity-card__action-icon">☆</text>
            <text class="identity-card__action-text">设为默认</text>
          </view>
          <view class="identity-card__action identity-card__action--active" v-else>
            <text class="identity-card__action-icon">★</text>
            <text class="identity-card__action-text">默认出行人</text>
          </view>
          <view class="identity-card__action-divider" />
          <view class="identity-card__action" @tap="onEditIdentity(item)">
            <text class="identity-card__action-icon">✏️</text>
            <text class="identity-card__action-text">编辑</text>
          </view>
          <view class="identity-card__action-divider" />
          <view class="identity-card__action identity-card__action--danger" @tap="onDeleteIdentity(item)">
            <text class="identity-card__action-icon">🗑️</text>
            <text class="identity-card__action-text">删除</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view class="empty-state card" v-if="identities.length === 0 && !loading">
      <view class="empty-state__icon-box">
        <text class="empty-state__icon">👤</text>
      </view>
      <text class="empty-state__title">暂无出行人信息</text>
      <text class="empty-state__desc">添加出行人后，下单时可快速选择</text>
      <view class="empty-state__btn btn-primary" @tap="onAddIdentity">
        <text>添加出行人</text>
      </view>
    </view>

    <!-- 底部添加按钮 -->
    <view class="footer-add safe-bottom" v-if="identities.length > 0">
      <view class="footer-add__btn btn-primary" @tap="onAddIdentity">
        <text class="footer-add__icon">+</text>
        <text>添加出行人</text>
      </view>
    </view>

    <!-- 表单弹窗 -->
    <view class="form-overlay" v-if="showForm" @tap="onCancelForm">
      <view class="form-sheet" :class="{ 'form-sheet--show': formAnimated }" @tap.stop>
        <!-- 弹窗头 -->
        <view class="form-sheet__header">
          <view class="form-sheet__indicator" />
          <text class="form-sheet__title">{{ editingId ? '编辑出行人' : '添加出行人' }}</text>
          <view class="form-sheet__close" @tap="onCancelForm">
            <text>✕</text>
          </view>
        </view>

        <!-- 表单内容 -->
        <scroll-view scroll-y class="form-sheet__body">
          <!-- 姓名 -->
          <view class="form-field">
            <view class="form-field__label-row">
              <text class="form-field__label">姓名</text>
              <text class="form-field__required">*</text>
            </view>
            <view class="form-field__input-wrap">
              <input
                class="form-field__input"
                placeholder="请输入真实姓名"
                placeholder-class="form-field__placeholder"
                :value="formData.name"
                @input="(e: any) => formData.name = e.detail.value"
              />
            </view>
          </view>

          <!-- 身份证号 -->
          <view class="form-field">
            <view class="form-field__label-row">
              <text class="form-field__label">身份证号</text>
              <text class="form-field__required">*</text>
            </view>
            <view class="form-field__input-wrap">
              <input
                class="form-field__input"
                placeholder="请输入18位身份证号码"
                placeholder-class="form-field__placeholder"
                :value="formData.id_card"
                @input="(e: any) => formData.id_card = e.detail.value"
                :maxlength="18"
              />
            </view>
            <text class="form-field__hint" v-if="formData.id_card && !isValidIdCard(formData.id_card)">请输入正确的18位身份证号</text>
          </view>

          <!-- 手机号 -->
          <view class="form-field">
            <view class="form-field__label-row">
              <text class="form-field__label">手机号</text>
              <text class="form-field__required">*</text>
            </view>
            <view class="form-field__input-wrap">
              <input
                class="form-field__input"
                placeholder="请输入手机号码"
                placeholder-class="form-field__placeholder"
                :value="formData.phone"
                @input="(e: any) => formData.phone = e.detail.value"
                type="number"
                :maxlength="11"
              />
            </view>
            <text class="form-field__hint" v-if="formData.phone && formData.phone.length === 11 && !isValidPhone(formData.phone)">请输入正确的手机号码</text>
          </view>

          <!-- 设为默认 -->
          <view class="form-field form-field--switch" @tap="formData.is_default = !formData.is_default">
            <view class="form-field__label-row">
              <text class="form-field__label">设为默认出行人</text>
            </view>
            <view :class="['form-switch', formData.is_default ? 'form-switch--on' : '']">
              <view class="form-switch__thumb" />
            </view>
          </view>
        </scroll-view>

        <!-- 提交按钮 -->
        <view class="form-sheet__footer safe-bottom">
          <view class="form-sheet__btn btn-primary" @tap="onSaveIdentity" :class="{ 'form-sheet__btn--loading': saving }">
            <text v-if="!saving">{{ editingId ? '保存修改' : '确认添加' }}</text>
            <text v-else>保存中...</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { get, post, put, del } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import { isValidPhone, isValidIdCard } from '@/utils/util'
import type { IIdentity } from '@/types'

const identities = ref<IIdentity[]>([])
const showForm = ref(false)
const formAnimated = ref(false)
const editingId = ref(0)
const loading = ref(true)
const saving = ref(false)
const formData = reactive({
  name: '',
  id_card: '',
  phone: '',
  is_default: false,
})

onLoad((options) => {
  loadIdentities().then(() => {
    // 从订单确认页跳转来，自动打开添加表单
    if (options?.action === 'add') {
      onAddIdentity()
    }
  })
})

onShow(() => {
  // 从其他页面返回时刷新
  if (identities.value.length > 0) {
    loadIdentities()
  }
})

/** 加载出行人列表 */
async function loadIdentities() {
  try {
    loading.value = true
    await ensureLogin()
    const data = await get<IIdentity[]>('/users/identities')
    identities.value = data || []
  } catch {
    identities.value = []
    uni.showToast({ title: '加载失败', icon: 'error' })
  } finally {
    loading.value = false
  }
}

/** 打开添加表单 */
function onAddIdentity() {
  editingId.value = 0
  formData.name = ''
  formData.id_card = ''
  formData.phone = ''
  formData.is_default = identities.value.length === 0 // 第一个自动默认
  showForm.value = true
  nextTick(() => { formAnimated.value = true })
}

/** 打开编辑表单 */
function onEditIdentity(item: IIdentity) {
  editingId.value = item.id
  formData.name = item.name
  formData.id_card = item.id_card
  formData.phone = item.phone
  formData.is_default = item.is_default
  showForm.value = true
  nextTick(() => { formAnimated.value = true })
}

/** 关闭表单 */
function onCancelForm() {
  formAnimated.value = false
  setTimeout(() => { showForm.value = false }, 300)
}

/** 保存出行人 */
async function onSaveIdentity() {
  if (saving.value) return

  if (!formData.name.trim()) {
    uni.showToast({ title: '请输入姓名', icon: 'none' })
    return
  }
  if (!isValidIdCard(formData.id_card)) {
    uni.showToast({ title: '请输入正确的身份证号', icon: 'none' })
    return
  }
  if (!isValidPhone(formData.phone)) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }

  try {
    saving.value = true
    const payload = {
      name: formData.name.trim(),
      id_card: formData.id_card,
      phone: formData.phone,
      is_default: formData.is_default,
    }

    if (editingId.value) {
      await put(`/users/identities/${editingId.value}`, payload)
    } else {
      await post('/users/identities', payload)
    }

    uni.showToast({ title: '保存成功', icon: 'success' })
    onCancelForm()
    loadIdentities()
  } catch {
    uni.showToast({ title: '保存失败', icon: 'error' })
  } finally {
    saving.value = false
  }
}

/** 设为默认 */
async function onSetDefault(item: IIdentity) {
  try {
    await put(`/users/identities/${item.id}`, { is_default: true })
    uni.showToast({ title: '已设为默认', icon: 'success' })
    loadIdentities()
  } catch {
    uni.showToast({ title: '设置失败', icon: 'error' })
  }
}

/** 删除出行人 */
function onDeleteIdentity(item: IIdentity) {
  uni.showModal({
    title: '删除出行人',
    content: `确定删除「${item.name}」的信息吗？`,
    confirmColor: '#c45c4a',
    success: async (res) => {
      if (res.confirm) {
        try {
          await del(`/users/identities/${item.id}`)
          identities.value = identities.value.filter(x => x.id !== item.id)
          uni.showToast({ title: '已删除', icon: 'success' })
        } catch {
          uni.showToast({ title: '删除失败', icon: 'error' })
        }
      }
    },
  })
}

/** 脱敏身份证号 */
function maskIdCard(idCard: string): string {
  if (!idCard || idCard.length < 8) return idCard
  return idCard.slice(0, 4) + '****' + idCard.slice(-4)
}

/** 脱敏手机号 */
function maskPhone(phone: string): string {
  if (!phone || phone.length < 7) return phone
  return phone.slice(0, 3) + '****' + phone.slice(-4)
}
</script>

<style lang="scss" scoped>
.page-identity {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding-bottom: 180rpx;
}

/* === 顶部装饰 === */
.page-header {
  position: relative;
  height: 260rpx;
  overflow: hidden;

  &__bg {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 50%, var(--color-accent) 150%);
  }

  &__content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    height: 100%;
    padding: 0 40rpx 32rpx;
  }

  &__title {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--color-text-white);
    letter-spacing: 2rpx;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: rgba(255, 254, 250, 0.7);
    margin-top: 8rpx;
    letter-spacing: 1rpx;
  }
}

/* === 出行人卡片列表 === */
.identity-list {
  padding: 24rpx 24rpx 0;
  margin-top: -40rpx;
  position: relative;
  z-index: 2;
}

.identity-card {
  position: relative;
  margin-bottom: 24rpx;
  transition: var(--transition-base);

  &--default {
    border: 2rpx solid rgba(200, 168, 114, 0.3);
    box-shadow: var(--shadow-glow);
  }

  &__badge {
    position: absolute;
    top: 0;
    right: 0;
    background: linear-gradient(135deg, var(--color-accent), #b8944e);
    padding: 6rpx 20rpx;
    border-radius: 0 var(--radius-xl) 0 var(--radius-md);

    text {
      font-size: var(--font-size-xs);
      color: #fff;
      font-weight: 600;
      letter-spacing: 1rpx;
    }
  }

  &__body {
    display: flex;
    align-items: flex-start;
    padding: 32rpx 28rpx 20rpx;
    gap: 24rpx;
  }

  &__avatar {
    width: 88rpx;
    height: 88rpx;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4rpx 16rpx rgba(45, 74, 62, 0.2);

    text {
      font-size: var(--font-size-xl);
      color: var(--color-text-white);
      font-weight: 700;
    }
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name-row {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-bottom: 12rpx;
  }

  &__name {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: 1rpx;
  }

  &__detail-row {
    display: flex;
    flex-direction: column;
    gap: 8rpx;
  }

  &__detail-item {
    display: flex;
    align-items: center;
    gap: 8rpx;
  }

  &__detail-icon {
    font-size: var(--font-size-sm);
  }

  &__detail-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    letter-spacing: 2rpx;
  }

  &__footer {
    display: flex;
    align-items: center;
    padding: 0 28rpx;
    height: 80rpx;
    border-top: 1rpx solid rgba(42, 37, 32, 0.05);
  }

  &__action {
    display: flex;
    align-items: center;
    gap: 6rpx;
    flex: 1;
    justify-content: center;
    height: 80rpx;

    &--active &-text {
      color: var(--color-accent) !important;
      font-weight: 600;
    }

    &--active &-icon {
      color: var(--color-accent);
    }

    &--danger &-text {
      color: var(--color-red) !important;
    }

    &:active {
      opacity: 0.6;
    }
  }

  &__action-icon {
    font-size: var(--font-size-sm);
  }

  &__action-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &__action-divider {
    width: 1rpx;
    height: 28rpx;
    background-color: rgba(42, 37, 32, 0.08);
  }
}

/* === 空状态 === */
.empty-state {
  margin: 48rpx 24rpx;
  padding: 80rpx 48rpx 56rpx;
  display: flex;
  flex-direction: column;
  align-items: center;

  &__icon-box {
    width: 140rpx;
    height: 140rpx;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--color-bg-warm), var(--color-bg-light));
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 32rpx;
  }

  &__icon {
    font-size: 64rpx;
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--color-text);
    margin-bottom: 12rpx;
  }

  &__desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-bottom: 48rpx;
  }

  &__btn {
    width: 360rpx;
    height: 88rpx;
  }
}

/* === 底部添加按钮 === */
.footer-add {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20rpx 32rpx;
  background: linear-gradient(to top, var(--color-bg) 60%, transparent);
  z-index: 100;

  &__btn {
    gap: 8rpx;
  }

  &__icon {
    font-size: var(--font-size-xl);
    font-weight: 300;
  }
}

/* === 表单弹窗（底部弹出式） === */
.form-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(42, 37, 32, 0.45);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

.form-sheet {
  width: 100%;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  transform: translateY(100%);
  transition: transform 0.35s var(--ease-out-expo);
  max-height: 85vh;
  display: flex;
  flex-direction: column;

  &--show {
    transform: translateY(0);
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24rpx 32rpx 20rpx;
    position: relative;
  }

  &__indicator {
    position: absolute;
    top: 16rpx;
    left: 50%;
    transform: translateX(-50%);
    width: 64rpx;
    height: 6rpx;
    border-radius: 3rpx;
    background-color: rgba(42, 37, 32, 0.1);
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
    margin-top: 16rpx;
    letter-spacing: 1rpx;
  }

  &__close {
    position: absolute;
    right: 24rpx;
    top: 32rpx;
    width: 56rpx;
    height: 56rpx;
    border-radius: 50%;
    background-color: var(--color-bg-grey);
    display: flex;
    align-items: center;
    justify-content: center;

    text {
      font-size: var(--font-size-base);
      color: var(--color-text-secondary);
    }

    &:active {
      background-color: var(--color-bg-light);
    }
  }

  &__body {
    flex: 1;
    padding: 8rpx 32rpx 24rpx;
    overflow: hidden;
  }

  &__footer {
    padding: 16rpx 32rpx 24rpx;
    border-top: 1rpx solid rgba(42, 37, 32, 0.05);
  }

  &__btn {
    width: 100%;

    &--loading {
      opacity: 0.7;
      pointer-events: none;
    }
  }
}

/* === 表单字段 === */
.form-field {
  margin-bottom: 28rpx;

  &--switch {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20rpx 0;
    border-top: 1rpx solid rgba(42, 37, 32, 0.05);
    margin-top: 8rpx;
  }

  &__label-row {
    display: flex;
    align-items: center;
    gap: 4rpx;
    margin-bottom: 12rpx;
  }

  &--switch &__label-row {
    margin-bottom: 0;
  }

  &__label {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-text);
  }

  &__required {
    font-size: var(--font-size-sm);
    color: var(--color-red);
  }

  &__input-wrap {
    position: relative;
    background-color: var(--color-bg-grey);
    border-radius: var(--radius-lg);
    border: 2rpx solid transparent;
    transition: border-color 0.3s ease;

    &:focus-within {
      border-color: var(--color-primary-lighter);
      background-color: var(--color-bg-white);
    }
  }

  &__input {
    height: 92rpx;
    padding: 0 24rpx;
    font-size: var(--font-size-base);
    color: var(--color-text);
    width: 100%;
    box-sizing: border-box;
  }

  &__placeholder {
    color: var(--color-text-placeholder);
  }

  &__hint {
    display: block;
    font-size: var(--font-size-xs);
    color: var(--color-red);
    margin-top: 8rpx;
    padding-left: 4rpx;
  }
}

/* === 开关 === */
.form-switch {
  width: 92rpx;
  height: 52rpx;
  border-radius: 26rpx;
  background-color: var(--color-bg-light);
  position: relative;
  transition: background-color 0.3s ease;
  flex-shrink: 0;

  &--on {
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  }

  &__thumb {
    position: absolute;
    top: 6rpx;
    left: 6rpx;
    width: 40rpx;
    height: 40rpx;
    border-radius: 50%;
    background-color: #fff;
    box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.15);
    transition: transform 0.3s var(--ease-out-expo);
  }

  &--on &__thumb {
    transform: translateX(40rpx);
  }
}
</style>
