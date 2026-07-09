<template>
  <view class="page-address">
    <view class="address-card card" v-for="item in addresses" :key="item.id" @tap="onSelectAddress(item)">
      <view class="address-card__header">
        <text class="address-card__name">{{ item.contact_name }}</text>
        <text class="address-card__phone">{{ item.contact_phone }}</text>
        <text class="tag tag--primary" v-if="item.is_default">默认</text>
      </view>
      <text class="address-card__detail">{{ item.province }}{{ item.city }}{{ item.district }} {{ item.detail }}</text>
      <view class="address-card__actions">
        <text class="address-card__btn" @tap.stop="onEditAddress(item)">编辑</text>
        <text class="address-card__btn address-card__btn--del" @tap.stop="onDeleteAddress(item.id)">删除</text>
      </view>
    </view>
    <view class="add-btn" @tap="onAddAddress"><text>+ 新增收货地址</text></view>
    <EmptyState v-if="addresses.length === 0" icon="📍" title="暂无收货地址" buttonText="新增地址" @action="onAddAddress" />

    <view class="form-mask" v-if="showForm" @tap="closeForm">
      <view class="form-sheet" @tap.stop>
        <view class="form-sheet__header">
          <text class="form-sheet__title">{{ editingId ? '编辑地址' : '新增地址' }}</text>
          <text class="form-sheet__close" @tap="closeForm">✕</text>
        </view>

        <view class="form-field">
          <text class="form-field__label">收货人</text>
          <input v-model="form.contact_name" placeholder="请输入收货人姓名" />
        </view>
        <view class="form-field">
          <text class="form-field__label">手机号</text>
          <input v-model="form.contact_phone" type="text" maxlength="11" placeholder="请输入手机号" />
          <text class="form-field__hint" v-if="editingId && form.contact_phone?.includes('*')">手机号已脱敏，修改需重新输入完整手机号</text>
        </view>
        <view class="form-field">
          <text class="form-field__label">省份</text>
          <input v-model="form.province" placeholder="如 浙江省" />
        </view>
        <view class="form-field">
          <text class="form-field__label">城市</text>
          <input v-model="form.city" placeholder="如 杭州市" />
        </view>
        <view class="form-field">
          <text class="form-field__label">区县</text>
          <input v-model="form.district" placeholder="如 西湖区" />
        </view>
        <view class="form-field">
          <text class="form-field__label">详细地址</text>
          <input v-model="form.detail" placeholder="街道、门牌号等" />
        </view>
        <view class="form-field form-field--switch" @tap="form.is_default = !form.is_default">
          <text class="form-field__label">设为默认</text>
          <view :class="['toggle', form.is_default ? 'toggle--on' : '']"></view>
        </view>

        <view class="form-actions">
          <view class="form-actions__btn form-actions__btn--ghost" @tap="closeForm"><text>取消</text></view>
          <view class="form-actions__btn form-actions__btn--primary" @tap="saveAddress"><text>{{ saving ? '保存中...' : '保存' }}</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post, put, del } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import EmptyState from '@/components/empty-state/index.vue'
import type { IAddress, IAddressFormPayload } from '@/types'

const addresses = ref<IAddress[]>([])
const selectMode = ref(false)
const showForm = ref(false)
const saving = ref(false)
const editingId = ref(0)
const form = reactive<IAddressFormPayload>({
  contact_name: '',
  contact_phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
  is_default: false,
})

onLoad((options) => {
  selectMode.value = options?.action === 'select'
  loadAddresses()
})

async function loadAddresses() {
  try {
    const loggedIn = await ensureLogin()
    if (!loggedIn) return
    const data = await get<IAddress[]>('/users/addresses')
    addresses.value = data || []
  } catch {
    addresses.value = []
    uni.showToast({ title: '加载地址失败', icon: 'error' })
  }
}

function onSelectAddress(item: IAddress) {
  if (!selectMode.value) return
  const pages = getCurrentPages()
  const prevPage = pages[pages.length - 2] as any
  const currentPage = pages[pages.length - 1] as any
  if (prevPage?.$vm) {
    prevPage.$vm.address = item
  }
  currentPage?.getOpenerEventChannel?.().emit?.('select', item)
  uni.navigateBack()
}

function onAddAddress() {
  editingId.value = 0
  Object.assign(form, {
    contact_name: '',
    contact_phone: '',
    province: '',
    city: '',
    district: '',
    detail: '',
    is_default: addresses.value.length === 0,
  })
  showForm.value = true
}

function onEditAddress(item: IAddress) {
  editingId.value = item.id
  Object.assign(form, {
    contact_name: item.contact_name,
    contact_phone: item.contact_phone,
    province: item.province,
    city: item.city,
    district: item.district,
    detail: item.detail,
    is_default: item.is_default,
  })
  showForm.value = true
}

function onDeleteAddress(id: number) {
  uni.showModal({
    title: '提示',
    content: '确定删除该地址吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await del(`/users/addresses/${id}`)
          addresses.value = addresses.value.filter(a => a.id !== id)
          uni.showToast({ title: '已删除', icon: 'success' })
        } catch {
          uni.showToast({ title: '删除失败', icon: 'error' })
        }
      }
    },
  })
}

function closeForm() {
  showForm.value = false
}

async function saveAddress() {
  if (saving.value) return
  if (!form.contact_name?.trim() || !form.contact_phone?.trim() || !form.province?.trim() || !form.city?.trim() || !form.district?.trim() || !form.detail?.trim()) {
    uni.showToast({ title: '请填写完整地址信息', icon: 'none' })
    return
  }
  const phoneValue = form.contact_phone.trim()
  const isMaskedPhone = phoneValue.includes('*')
  if (!isMaskedPhone && !/^1[3-9]\d{9}$/.test(phoneValue)) {
    uni.showToast({ title: '请输入正确手机号', icon: 'none' })
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      contact_name: form.contact_name.trim(),
      province: form.province.trim(),
      city: form.city.trim(),
      district: form.district.trim(),
      detail: form.detail.trim(),
      is_default: Boolean(form.is_default),
    }
    if (!editingId.value || !isMaskedPhone) {
      payload.contact_phone = phoneValue
    }
    if (editingId.value) {
      await put(`/users/addresses/${editingId.value}`, payload)
    } else {
      await post('/users/addresses', payload)
    }
    uni.showToast({ title: '已保存', icon: 'success' })
    showForm.value = false
    await loadAddresses()
  } catch {
    uni.showToast({ title: '保存失败', icon: 'error' })
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
.page-address { min-height: 100vh; background-color: var(--color-bg); padding: 16rpx 24rpx; }
.address-card {
  padding: 24rpx; margin-bottom: 16rpx;
  &__header { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
  &__name { font-size: var(--font-size-md); font-weight: 600; }
  &__phone { font-size: var(--font-size-base); color: var(--color-text-secondary); }
  &__detail { font-size: var(--font-size-base); color: var(--color-text-secondary); line-height: 1.5; display: block; }
  &__actions { display: flex; gap: 24rpx; margin-top: 16rpx; padding-top: 16rpx; border-top: 1rpx solid #F0F0F0; }
  &__btn { font-size: var(--font-size-sm); color: var(--color-primary); padding: 8rpx; &--del { color: var(--color-red); } }
}
.add-btn { text-align: center; padding: 28rpx; text { font-size: var(--font-size-base); color: var(--color-primary); font-weight: 500; } &:active { opacity: 0.7; } }

.form-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.36);
  z-index: 30;
  display: flex;
  align-items: flex-end;
}

.form-sheet {
  width: 100%;
  background: #fff;
  border-top-left-radius: 24rpx;
  border-top-right-radius: 24rpx;
  padding: 24rpx;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20rpx;
  }

  &__title {
    font-size: var(--font-size-md);
    font-weight: 600;
  }

  &__close {
    font-size: 40rpx;
    color: var(--color-text-secondary);
  }
}

.form-field {
  margin-bottom: 18rpx;

  &__label {
    display: block;
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-bottom: 8rpx;
  }

  &__hint {
    display: block;
    margin-top: 6rpx;
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    line-height: 1.4;
  }

  input {
    width: 100%;
    box-sizing: border-box;
    padding: 18rpx 20rpx;
    border-radius: 12rpx;
    border: 1rpx solid #e9e9e9;
    background: #fff;
    font-size: var(--font-size-base);
  }

  &--switch {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10rpx 0;
  }
}

.toggle {
  width: 72rpx;
  height: 40rpx;
  border-radius: 20rpx;
  background: #d8d8d8;
  position: relative;

  &::after {
    content: '';
    position: absolute;
    left: 4rpx;
    top: 4rpx;
    width: 32rpx;
    height: 32rpx;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.2s;
  }

  &--on {
    background: var(--color-primary);
    &::after { transform: translateX(32rpx); }
  }
}

.form-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;

  &__btn {
    flex: 1;
    height: 76rpx;
    border-radius: 38rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-base);

    &--ghost {
      border: 1rpx solid #ddd;
      color: var(--color-text-secondary);
    }

    &--primary {
      background: var(--color-primary);
      color: #fff;
    }
  }
}
</style>
