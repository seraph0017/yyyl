<template>
  <view class="bundle-picker" v-if="hasData && itemList.length > 0">
    <view class="bundle-picker__header">
      <text class="bundle-picker__title">🎁 搭配推荐</text>
    </view>

    <view class="bundle-picker__list">
      <view
        class="bundle-item"
        v-for="item in itemList"
        :key="item.product_id"
        @tap="toggleItem(item.product_id)"
      >
        <!-- 勾选框 -->
        <view
          class="bundle-item__checkbox"
          :class="{ 'bundle-item__checkbox--checked': item.checked }"
        >
          <text v-if="item.checked">✓</text>
        </view>

        <!-- 商品图 -->
        <image
          class="bundle-item__image"
          :src="resolveImageUrl(item.product_image)"
          mode="aspectFill"
          v-if="item.product_image"
          lazy-load
        />
        <view class="bundle-item__image bundle-item__image--placeholder" v-else>
          <text>📦</text>
        </view>

        <!-- 商品信息 -->
        <view class="bundle-item__info">
          <text class="bundle-item__name text-ellipsis">{{ item.product_name }}</text>
          <view class="bundle-item__price-row">
            <text class="bundle-item__price">¥{{ item.bundle_price.toFixed(2) }}</text>
            <text class="bundle-item__original" v-if="item.original_price > item.bundle_price">
              ¥{{ item.original_price.toFixed(2) }}
            </text>
          </view>
        </view>

        <!-- 数量选择 -->
        <view class="bundle-item__quantity" v-if="item.checked" @tap.stop>
          <view
            class="quantity-btn"
            :class="{ 'quantity-btn--disabled': item.quantity <= 1 }"
            @tap="changeQuantity(item.product_id, -1)"
          >
            <text>−</text>
          </view>
          <text class="quantity-value">{{ item.quantity }}</text>
          <view
            class="quantity-btn"
            :class="{ 'quantity-btn--disabled': item.quantity >= item.max_quantity }"
            @tap="changeQuantity(item.product_id, 1)"
          >
            <text>+</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 搭配合计 -->
    <view class="bundle-picker__footer" v-if="selectedItems.length > 0">
      <text class="bundle-picker__summary">
        已选 {{ selectedItems.length }} 件搭配
      </text>
      <text class="bundle-picker__total">
        搭配合计：<text class="bundle-picker__total-price">¥{{ totalPrice }}</text>
      </text>
    </view>
  </view>

  <!-- 加载状态 -->
  <view class="bundle-picker bundle-picker--loading" v-else-if="loading">
    <view class="skeleton-bar" style="width: 40%; height: 32rpx; margin-bottom: 20rpx;" />
    <view class="skeleton-bar" style="width: 100%; height: 120rpx; margin-bottom: 16rpx;" />
    <view class="skeleton-bar" style="width: 100%; height: 120rpx;" />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { get, resolveImageUrl } from '@/utils/request'
import type { IBundleItem } from '@/types'

interface BundleItemState {
  product_id: number
  product_name: string
  product_image: string
  original_price: number
  bundle_price: number
  max_quantity: number
  checked: boolean
  quantity: number
}

const props = defineProps<{
  productId: number
}>()

const emit = defineEmits<{
  (e: 'change', items: { product_id: number; quantity: number; bundle_price: number }[]): void
}>()

const loading = ref(false)
const hasData = ref(false)
const itemList = ref<BundleItemState[]>([])

const selectedItems = computed(() => itemList.value.filter((i) => i.checked))

const totalPrice = computed(() => {
  return selectedItems.value
    .reduce((sum, item) => sum + item.bundle_price * item.quantity, 0)
    .toFixed(2)
})

/** 切换勾选 */
function toggleItem(productId: number) {
  const item = itemList.value.find((i) => i.product_id === productId)
  if (!item) return
  item.checked = !item.checked
  if (!item.checked) {
    item.quantity = 1
  }
  emitChange()
}

/** 更改数量 */
function changeQuantity(productId: number, delta: number) {
  const item = itemList.value.find((i) => i.product_id === productId)
  if (!item) return
  const newQty = item.quantity + delta
  if (newQty < 1 || newQty > item.max_quantity) return
  item.quantity = newQty
  emitChange()
}

/** 触发变更事件 */
function emitChange() {
  const selected = selectedItems.value.map((item) => ({
    product_id: item.product_id,
    quantity: item.quantity,
    bundle_price: item.bundle_price,
  }))
  emit('change', selected)
}

/** 加载搭配数据 */
async function loadBundles() {
  if (!props.productId) return
  loading.value = true

  try {
    // 后端返回 BundleRecommendItem[] 数组
    const data = await get<IBundleItem[]>(
      `/products/${props.productId}/bundles`,
      undefined,
      { showError: false },
    )

    if (data && Array.isArray(data) && data.length > 0) {
      hasData.value = true
      itemList.value = data.map((item) => ({
        product_id: item.product_id,
        product_name: item.product_name,
        product_image: item.product_image || '',
        original_price: item.original_price,
        bundle_price: item.bundle_price,
        max_quantity: item.max_quantity,
        checked: item.is_default_checked,
        quantity: 1,
      }))
      // 默认选中的项触发一次变更
      emitChange()
    }
  } catch {
    // 无搭配数据，静默处理
    hasData.value = false
  } finally {
    loading.value = false
  }
}

watch(() => props.productId, () => {
  loadBundles()
})

onMounted(() => {
  loadBundles()
})
</script>

<style lang="scss" scoped>
.bundle-picker {
  margin: 24rpx 0;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);

  &--loading {
    padding: 28rpx;
  }

  &__header {
    padding: 28rpx 28rpx 16rpx;
    display: flex;
    align-items: baseline;
    gap: 12rpx;
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text);
  }

  &__subtitle {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
  }

  &__list {
    padding: 0 28rpx;
  }

  &__footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20rpx 28rpx;
    margin-top: 8rpx;
    background-color: var(--color-bg-grey);
  }

  &__summary {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &__total {
    font-size: var(--font-size-sm);
    color: var(--color-text);
  }

  &__total-price {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-orange);
  }
}

.bundle-item {
  display: flex;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid rgba(0, 0, 0, 0.05);

  &:last-child {
    border-bottom: none;
  }

  &:active {
    opacity: 0.8;
  }

  &__checkbox {
    width: 44rpx;
    height: 44rpx;
    border-radius: 50%;
    border: 2rpx solid #d9d9d9;
    display: flex;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
    margin-right: 16rpx;
    transition: all 0.2s;

    text {
      font-size: 24rpx;
      color: #fff;
    }

    &--checked {
      background-color: var(--color-primary);
      border-color: var(--color-primary);
    }
  }

  &__image {
    width: 120rpx;
    height: 120rpx;
    border-radius: var(--radius-md);
    flex-shrink: 0;
    margin-right: 16rpx;

    &--placeholder {
      background-color: var(--color-bg-light);
      display: flex;
      justify-content: center;
      align-items: center;
      text { font-size: 48rpx; }
    }
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: 500;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__price-row {
    display: flex;
    align-items: baseline;
    gap: 8rpx;
    margin-top: 8rpx;
  }

  &__price {
    font-size: var(--font-size-base);
    font-weight: 700;
    color: var(--color-orange);
  }

  &__original {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    text-decoration: line-through;
  }

  &__quantity {
    display: flex;
    align-items: center;
    gap: 4rpx;
    flex-shrink: 0;
    margin-left: 12rpx;
  }
}

.quantity-btn {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--color-bg-grey);
  border-radius: var(--radius-sm);

  text {
    font-size: var(--font-size-lg);
    color: var(--color-text);
    font-weight: 700;
  }

  &:active { opacity: 0.7; }

  &--disabled {
    opacity: 0.3;
    &:active { opacity: 0.3; }
  }
}

.quantity-value {
  width: 56rpx;
  text-align: center;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.skeleton-bar {
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
