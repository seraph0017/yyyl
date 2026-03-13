<template>
  <view class="page-address">
    <view class="address-card card" v-for="item in addresses" :key="item.id" @tap="onSelectAddress(item.id)">
      <view class="address-card__header">
        <text class="address-card__name">{{ item.name }}</text>
        <text class="address-card__phone">{{ item.phone }}</text>
        <text class="tag tag--primary" v-if="item.is_default">默认</text>
      </view>
      <text class="address-card__detail">{{ item.province }}{{ item.city }}{{ item.district }} {{ item.detail }}</text>
      <view class="address-card__actions">
        <text class="address-card__btn">编辑</text>
        <text class="address-card__btn address-card__btn--del" @tap.stop="onDeleteAddress(item.id)">删除</text>
      </view>
    </view>
    <view class="add-btn" @tap="onAddAddress"><text>+ 新增收货地址</text></view>
    <EmptyState v-if="addresses.length === 0" icon="📍" title="暂无收货地址" buttonText="新增地址" @action="onAddAddress" />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post, put, del } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import EmptyState from '@/components/empty-state/index.vue'
import type { IAddress } from '@/types'

const addresses = ref<IAddress[]>([])
const selectMode = ref(false)

onLoad((options) => {
  selectMode.value = options?.action === 'select'
  loadAddresses()
})

async function loadAddresses() {
  try {
    await ensureLogin()
    const data = await get<IAddress[]>('/users/addresses')
    addresses.value = data || []
  } catch {
    addresses.value = []
    uni.showToast({ title: '加载地址失败', icon: 'error' })
  }
}

function onSelectAddress(id: number) {
  if (selectMode.value) {
    const addr = addresses.value.find(a => a.id === id)
    if (addr) {
      const pages = getCurrentPages()
      const prevPage = pages[pages.length - 2] as any
      if (prevPage?.$vm) { prevPage.$vm.address = addr }
      uni.navigateBack()
    }
  }
}

function onAddAddress() {
  // TODO: 打开地址编辑表单，暂时用简单提示
  uni.showToast({ title: '添加地址功能开发中', icon: 'none' })
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
</style>
