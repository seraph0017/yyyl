<template>
  <!-- 订单确认页 -->
  <view class="page-confirm">
    <!-- 出行人信息 -->
    <view class="section card" v-if="product && product.identity_mode !== 'none'">
      <view class="section__header">
        <text class="section__title">👤 出行人信息</text>
        <text class="section__required" v-if="product.identity_mode === 'required'">必填</text>
        <text class="section__optional" v-else>选填</text>
      </view>
      <view class="identity-list">
        <view
          :class="['identity-item', selectedIdentity && selectedIdentity.id === item.id ? 'identity-item--active' : '']"
          v-for="item in identities"
          :key="item.id"
          @tap="onSelectIdentity(item.id)"
        >
          <view class="identity-item__check">
            <view :class="['radio', selectedIdentity && selectedIdentity.id === item.id ? 'radio--checked' : '']"></view>
          </view>
          <view class="identity-item__info">
            <text class="identity-item__name">{{ item.name }}</text>
            <text class="identity-item__detail">{{ item.id_card }} · {{ item.phone }}</text>
          </view>
        </view>
      </view>
      <view class="identity-add" @tap="onAddIdentity">
        <text>+ 添加出行人</text>
      </view>
    </view>

    <!-- 收货地址 -->
    <view class="section card" v-if="needAddress" @tap="onSelectAddress">
      <view class="section__header">
        <text class="section__title">📍 收货地址</text>
      </view>
      <view class="address-info" v-if="address">
        <text class="address-info__name">{{ address.name }} {{ address.phone }}</text>
        <text class="address-info__detail">{{ address.province }}{{ address.city }}{{ address.district }}{{ address.detail }}</text>
      </view>
      <view class="address-placeholder" v-else>
        <text>请选择收货地址</text>
        <text class="address-placeholder__arrow">›</text>
      </view>
    </view>

    <!-- 商品信息 -->
    <view class="section card" v-if="product">
      <view class="section__header">
        <text class="section__title">🏕️ 商品信息</text>
      </view>
      <view class="confirm-product">
        <view class="confirm-product__image">
          <text>🏕️</text>
        </view>
        <view class="confirm-product__info">
          <text class="confirm-product__name">{{ product.name }}</text>
          <view class="confirm-product__dates" v-if="dates.length > 0">
            <text class="confirm-product__date" v-for="d in dates" :key="d">📅 {{ d }}</text>
          </view>
          <view class="confirm-product__price-row">
            <PriceTag :price="product.current_price" size="small" />
            <text class="confirm-product__qty">x{{ quantity }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 费用明细 -->
    <view class="section card">
      <view class="section__header">
        <text class="section__title">💰 费用明细</text>
      </view>
      <view class="fee-row">
        <text>商品金额</text>
        <text>¥{{ totalPrice }}</text>
      </view>
      <view class="fee-row fee-row--discount" v-if="discountAmount > 0">
        <text>连定优惠</text>
        <text>-¥{{ discountAmount }}</text>
      </view>
      <view class="fee-row fee-row--deposit" v-if="product && product.deposit_amount > 0">
        <text>押金</text>
        <text>¥{{ product.deposit_amount }}</text>
      </view>
      <view class="divider"></view>
      <view class="fee-row fee-row--total">
        <text>实付金额</text>
        <view class="fee-total-price">
          <text class="fee-total-symbol">¥</text>
          <text class="fee-total-amount">{{ actualPrice }}</text>
        </view>
      </view>
    </view>

    <!-- 底部提交 -->
    <view class="confirm-footer safe-bottom">
      <view class="confirm-footer__price">
        <text class="confirm-footer__label">合计：</text>
        <text class="confirm-footer__symbol">¥</text>
        <text class="confirm-footer__amount">{{ actualPrice }}</text>
      </view>
      <view :class="['confirm-footer__btn', submitting ? 'btn-disabled' : '']" @tap="onSubmitOrder">
        <text>{{ submitting ? '提交中...' : '提交订单' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import PriceTag from '@/components/price-tag/index.vue'
import type { IProduct, IIdentity, IAddress } from '@/types'

const from = ref('direct')
const productId = ref(0)
const cartItemIds = ref<string[]>([])
const dates = ref<string[]>([])
const quantity = ref(1)
const product = ref<IProduct | null>(null)
const identities = ref<IIdentity[]>([])
const selectedIdentity = ref<IIdentity | null>(null)
const address = ref<IAddress | null>(null)
const needAddress = ref(false)
const totalPrice = ref(0)
const discountAmount = ref(0)
const actualPrice = ref(0)
const submitting = ref(false)

onLoad((options) => {
  productId.value = Number(options?.product_id || 0)
  dates.value = options?.dates ? options.dates.split(',') : []
  quantity.value = Number(options?.quantity || 1)
  from.value = options?.from || 'direct'
  cartItemIds.value = options?.cart_item_ids ? options.cart_item_ids.split(',') : []

  loadData()
})

async function loadData() {
  try {
    await ensureLogin()

    // 加载商品信息（如果是直接购买）
    if (productId.value) {
      const p = await get<IProduct>(`/products/${productId.value}`)
      product.value = p
      needAddress.value = p.category === 'merchandise'
      const total = p.current_price * (dates.value.length || 1) * quantity.value
      const discount = dates.value.length >= 2 ? Math.floor(total * 0.2) : 0
      totalPrice.value = total
      discountAmount.value = discount
      actualPrice.value = total - discount
    }

    // 加载出行人列表
    const idList = await get<IIdentity[]>('/users/identities')
    identities.value = idList || []
    const defaultId = identities.value.find(i => i.is_default)
    if (defaultId) selectedIdentity.value = defaultId
    else if (identities.value.length > 0) selectedIdentity.value = identities.value[0]
  } catch {
    uni.showToast({ title: '加载数据失败', icon: 'error' })
  }
}

/** 选择身份 */
function onSelectIdentity(id: number) {
  const identity = identities.value.find(i => i.id === id) || null
  selectedIdentity.value = identity
}

/** 添加身份 */
function onAddIdentity() {
  uni.navigateTo({ url: '/pages/identity/index?action=add' })
}

/** 选择地址 */
function onSelectAddress() {
  uni.navigateTo({ url: '/pages/address/index?action=select' })
}

/** 提交订单 */
async function onSubmitOrder() {
  const p = product.value

  if (submitting.value) return
  if (!p && from.value !== 'cart') return

  // 验证身份
  if (p && p.identity_mode === 'required' && !selectedIdentity.value) {
    uni.showToast({ title: '请选择出行人信息', icon: 'none' })
    return
  }

  // 验证地址
  if (needAddress.value && !address.value) {
    uni.showToast({ title: '请选择收货地址', icon: 'none' })
    return
  }

  submitting.value = true

  try {
    const orderData: Record<string, unknown> = {}
    if (from.value === 'cart') {
      orderData.from = 'cart'
      orderData.cart_item_ids = cartItemIds.value.map(Number)
    } else {
      orderData.product_id = productId.value
      orderData.dates = dates.value
      orderData.quantity = quantity.value
    }
    if (selectedIdentity.value) orderData.identity_id = selectedIdentity.value.id
    if (address.value) orderData.address_id = address.value.id

    const result = await post<{ id: number; order_no: string; actual_amount: number }>('/orders', orderData)
    uni.navigateTo({
      url: `/pages/payment/index?order_id=${result.id}&amount=${result.actual_amount}&order_no=${result.order_no}`,
    })
  } catch {
    uni.showToast({ title: '提交订单失败', icon: 'error' })
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
.page-confirm {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding: 16rpx 24rpx 160rpx;
}

.section {
  margin-bottom: 16rpx;
  padding: 24rpx;

  &__header {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-bottom: 20rpx;
  }

  &__title {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  &__required {
    font-size: var(--font-size-xs);
    color: var(--color-red);
    padding: 2rpx 8rpx;
    background-color: rgba(229, 57, 53, 0.08);
    border-radius: var(--radius-sm);
  }

  &__optional {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    padding: 2rpx 8rpx;
    background-color: var(--color-bg-grey);
    border-radius: var(--radius-sm);
  }
}

/* 身份信息 */
.identity-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.identity-item {
  display: flex;
  align-items: center;
  padding: 20rpx;
  background-color: var(--color-bg-grey);
  border-radius: var(--radius-md);
  border: 2rpx solid transparent;
  transition: all 0.2s ease;

  &--active {
    background-color: var(--color-primary-bg);
    border-color: var(--color-primary-lighter);
  }

  &__check {
    margin-right: 16rpx;
  }

  &__info {
    flex: 1;
  }

  &__name {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
    display: block;
  }

  &__detail {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 4rpx;
    display: block;
  }
}

.radio {
  width: 36rpx;
  height: 36rpx;
  border: 3rpx solid #D0D0D0;
  border-radius: 50%;
  transition: all 0.2s ease;

  &--checked {
    border-color: var(--color-primary);
    background-color: var(--color-primary);
    box-shadow: inset 0 0 0 4rpx #fff;
  }
}

.identity-add {
  padding: 20rpx;
  text-align: center;
  margin-top: 12rpx;

  text {
    font-size: var(--font-size-base);
    color: var(--color-primary);
    font-weight: 500;
  }
}

/* 地址 */
.address-info {
  &__name {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
    display: block;
  }

  &__detail {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 6rpx;
    display: block;
  }
}

.address-placeholder {
  display: flex;
  justify-content: space-between;
  align-items: center;

  text { font-size: var(--font-size-base); color: var(--color-text-placeholder); }
  &__arrow { font-size: var(--font-size-xl); }
}

/* 商品信息 */
.confirm-product {
  display: flex;

  &__image {
    width: 160rpx;
    height: 160rpx;
    background-color: var(--color-bg-light);
    border-radius: var(--radius-md);
    display: flex;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
    margin-right: 20rpx;
    text { font-size: 56rpx; }
  }

  &__info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  &__name {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  &__dates {
    display: flex;
    flex-wrap: wrap;
    gap: 8rpx;
    margin-top: 8rpx;
  }

  &__date {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &__price-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 12rpx;
  }

  &__qty {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }
}

/* 费用明细 */
.fee-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12rpx 0;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);

  &--discount text:last-child {
    color: var(--color-primary);
  }

  &--total {
    font-weight: 600;
    text:first-child { color: var(--color-text); font-size: var(--font-size-md); }
  }
}

.fee-total-price {
  display: flex;
  align-items: baseline;
}

.fee-total-symbol {
  font-size: var(--font-size-base);
  color: var(--color-orange);
  font-weight: 700;
}

.fee-total-amount {
  font-size: var(--font-size-xxl);
  color: var(--color-orange);
  font-weight: 700;
}

/* 底部提交 */
.confirm-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 32rpx;
  background-color: var(--color-bg-white);
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
  z-index: 100;

  &__price {
    display: flex;
    align-items: baseline;
  }

  &__label {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
  }

  &__symbol {
    font-size: var(--font-size-base);
    color: var(--color-orange);
    font-weight: 700;
  }

  &__amount {
    font-size: var(--font-size-xxl);
    color: var(--color-orange);
    font-weight: 700;
  }

  &__btn {
    height: 84rpx;
    padding: 0 60rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
    border-radius: var(--radius-round);

    text { font-size: var(--font-size-lg); color: #fff; font-weight: 600; }
    &:active { opacity: 0.85; }
  }
}
</style>
