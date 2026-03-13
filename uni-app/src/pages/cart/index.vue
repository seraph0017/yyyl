<template>
  <view class="page-cart">
    <view class="cart-header" v-if="cartItems.length > 0">
      <text class="cart-header__count">共 {{ cartItems.length }} 件商品</text>
      <text class="cart-header__edit" @tap="editing = !editing">{{ editing ? '完成' : '管理' }}</text>
    </view>

    <view class="cart-list" v-if="cartItems.length > 0">
      <view class="cart-item card" v-for="(item, index) in cartItems" :key="item.id">
        <view class="cart-item__check" @tap="onToggleItem(index)">
          <view class="checkbox" :class="{ 'checkbox--checked': item.selected }">
            <text v-if="item.selected">✓</text>
          </view>
        </view>
        <view class="cart-item__image">
          <image :src="item.cover_image" mode="aspectFill" v-if="item.cover_image" />
          <view class="cart-item__placeholder" v-else><text>🛒</text></view>
        </view>
        <view class="cart-item__info">
          <text class="cart-item__name text-ellipsis-2">{{ item.product_name }}</text>
          <view class="cart-item__bottom">
            <price-tag :price="item.price" size="small" />
            <view class="cart-item__quantity">
              <view class="qty-btn" :class="{ 'qty-btn--disabled': item.quantity <= 1 }" @tap="onMinus(index)"><text>−</text></view>
              <text class="qty-value">{{ item.quantity }}</text>
              <view class="qty-btn" :class="{ 'qty-btn--disabled': item.quantity >= item.stock }" @tap="onAdd(index)"><text>+</text></view>
            </view>
          </view>
        </view>
        <view class="cart-item__delete" v-if="editing" @tap="onDelete(index)"><text>🗑️</text></view>
      </view>
    </view>

    <empty-state
      v-if="!loading && cartItems.length === 0"
      icon="🛒"
      title="购物车空空如也"
      description="去逛逛营地小商店和周边商品吧"
      buttonText="去逛逛"
      @action="onGoShopping"
    />

    <view class="cart-footer safe-bottom" v-if="cartItems.length > 0">
      <view class="cart-footer__left">
        <view class="cart-footer__check" @tap="onToggleAll">
          <view class="checkbox" :class="{ 'checkbox--checked': allSelected }">
            <text v-if="allSelected">✓</text>
          </view>
          <text class="cart-footer__check-text">全选</text>
        </view>
      </view>
      <view class="cart-footer__right" v-if="!editing">
        <view class="cart-footer__total">
          <text class="cart-footer__total-label">合计：</text>
          <text class="cart-footer__total-symbol">¥</text>
          <text class="cart-footer__total-price">{{ totalPrice }}</text>
        </view>
        <view class="cart-footer__btn" :class="{ 'cart-footer__btn--disabled': totalCount === 0 }" @tap="onCheckout">
          <text>结算({{ totalCount }})</text>
        </view>
      </view>
      <view class="cart-footer__right" v-if="editing">
        <view class="cart-footer__delete-btn" @tap="onBatchDelete"><text>删除</text></view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { get, put, del } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import { resolveImageUrl } from '@/utils/request'
import type { ICartItem } from '@/types'
import PriceTag from '@/components/price-tag/index.vue'
import EmptyState from '@/components/empty-state/index.vue'

const cartItems = ref<ICartItem[]>([])
const loading = ref(true)
const editing = ref(false)

const allSelected = computed(() => cartItems.value.length > 0 && cartItems.value.every((i) => i.selected))
const totalPrice = computed(() => cartItems.value.filter((i) => i.selected).reduce((sum, i) => sum + i.price * i.quantity, 0))
const totalCount = computed(() => cartItems.value.filter((i) => i.selected).reduce((sum, i) => sum + i.quantity, 0))

async function loadCartData() {
  loading.value = true
  try {
    const loggedIn = await ensureLogin()
    if (!loggedIn) { loading.value = false; return }
    const data = await get<ICartItem[]>('/cart/')
    cartItems.value = (data || []).map(item => ({
      ...item,
      cover_image: resolveImageUrl(item.cover_image),
      selected: true,
    }))
  } catch {
    cartItems.value = []
  } finally {
    loading.value = false
  }
}

function onToggleAll() {
  const newSelected = !allSelected.value
  cartItems.value.forEach((item) => { item.selected = newSelected })
}

function onToggleItem(index: number) {
  cartItems.value[index].selected = !cartItems.value[index].selected
}

async function onAdd(index: number) {
  const item = cartItems.value[index]
  if (item.quantity >= item.stock) {
    uni.showToast({ title: '已达库存上限', icon: 'none' })
    return
  }
  try {
    await put(`/cart/items/${item.id}`, { quantity: item.quantity + 1 })
    item.quantity++
  } catch {
    uni.showToast({ title: '修改数量失败', icon: 'error' })
  }
}

async function onMinus(index: number) {
  const item = cartItems.value[index]
  if (item.quantity <= 1) return
  try {
    await put(`/cart/items/${item.id}`, { quantity: item.quantity - 1 })
    item.quantity--
  } catch {
    uni.showToast({ title: '修改数量失败', icon: 'error' })
  }
}

function onDelete(index: number) {
  const item = cartItems.value[index]
  uni.showModal({
    title: '提示', content: '确定删除该商品吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await del(`/cart/items/${item.id}`)
          cartItems.value.splice(index, 1)
        } catch {
          uni.showToast({ title: '删除失败', icon: 'error' })
        }
      }
    },
  })
}

function onBatchDelete() {
  const selected = cartItems.value.filter((i) => i.selected)
  if (selected.length === 0) return uni.showToast({ title: '请选择要删除的商品', icon: 'none' })
  uni.showModal({
    title: '提示', content: `确定删除选中的${selected.length}件商品吗？`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await Promise.all(selected.map(item => del(`/cart/items/${item.id}`)))
          cartItems.value = cartItems.value.filter((i) => !i.selected)
        } catch {
          uni.showToast({ title: '删除失败', icon: 'error' })
          loadCartData()
        }
      }
    },
  })
}

function onCheckout() {
  if (totalCount.value === 0) return uni.showToast({ title: '请选择要结算的商品', icon: 'none' })
  const selectedIds = cartItems.value.filter(i => i.selected).map(i => i.id).join(',')
  uni.navigateTo({ url: `/pages/order-confirm/index?from=cart&cart_item_ids=${selectedIds}` })
}

function onGoShopping() {
  uni.switchTab({ url: '/pages/category/index' })
}

onShow(() => { loadCartData() })
</script>

<style lang="scss" scoped>
.page-cart { min-height: 100vh; background-color: var(--color-bg); padding-bottom: 140rpx; }

.cart-header {
  display: flex; justify-content: space-between; align-items: center; padding: 20rpx 32rpx;
  &__count { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
  &__edit { font-size: var(--font-size-base); color: var(--color-primary); padding: 8rpx 16rpx; }
}

.checkbox {
  width: 44rpx; height: 44rpx; border: 3rpx solid #d0d0d0; border-radius: 50%;
  display: flex; justify-content: center; align-items: center; flex-shrink: 0;
  text { font-size: 24rpx; color: #fff; font-weight: 700; }
  &--checked { background-color: var(--color-primary); border-color: var(--color-primary); }
}

.cart-list { padding: 0 32rpx; }

.cart-item {
  display: flex; align-items: center; padding: 24rpx 20rpx; margin-bottom: 16rpx;
  &__check { padding: 8rpx; margin-right: 12rpx; }
  &__image {
    width: 160rpx; height: 160rpx; border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; margin-right: 20rpx;
    image { width: 100%; height: 100%; }
  }
  &__placeholder { width: 100%; height: 100%; background-color: var(--color-bg-light); display: flex; justify-content: center; align-items: center; text { font-size: 48rpx; } }
  &__info { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: space-between; min-height: 160rpx; }
  &__name { font-size: var(--font-size-base); font-weight: 500; color: var(--color-text); line-height: 1.4; }
  &__bottom { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 16rpx; }
  &__quantity { display: flex; align-items: center; gap: 4rpx; }
  &__delete { padding: 12rpx; margin-left: 8rpx; text { font-size: 36rpx; } }
}

.qty-btn {
  width: 52rpx; height: 52rpx; display: flex; justify-content: center; align-items: center;
  background-color: var(--color-bg-grey); border-radius: var(--radius-sm);
  text { font-size: 28rpx; color: var(--color-text); font-weight: 600; }
  &--disabled { opacity: 0.3; pointer-events: none; }
  &:active { background-color: #e8e8e8; }
}

.qty-value { min-width: 56rpx; text-align: center; font-size: var(--font-size-base); font-weight: 500; }

.cart-footer {
  position: fixed; bottom: 0; left: 0; right: 0; display: flex; justify-content: space-between;
  align-items: center; height: 110rpx; padding: 0 32rpx; background-color: var(--color-bg-white);
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06); z-index: 100;
  &__left { display: flex; align-items: center; }
  &__check { display: flex; align-items: center; gap: 12rpx; padding: 8rpx; }
  &__check-text { font-size: var(--font-size-base); color: var(--color-text-secondary); }
  &__right { display: flex; align-items: center; gap: 20rpx; }
  &__total { display: flex; align-items: baseline; }
  &__total-label { font-size: var(--font-size-base); color: var(--color-text-secondary); }
  &__total-symbol { font-size: var(--font-size-sm); color: var(--color-orange); font-weight: 700; }
  &__total-price { font-size: var(--font-size-xxl); color: var(--color-orange); font-weight: 700; }
  &__btn {
    height: 76rpx; padding: 0 40rpx; display: flex; justify-content: center; align-items: center;
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary)); border-radius: var(--radius-round);
    text { font-size: var(--font-size-base); color: #fff; font-weight: 600; }
    &--disabled { opacity: 0.5; pointer-events: none; }
  }
  &__delete-btn {
    height: 76rpx; padding: 0 40rpx; display: flex; justify-content: center; align-items: center;
    background-color: var(--color-red); border-radius: var(--radius-round);
    text { font-size: var(--font-size-base); color: #fff; font-weight: 600; }
  }
}
</style>
