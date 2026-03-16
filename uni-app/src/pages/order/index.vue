<template>
  <view class="page-order">
    <!-- Tab 栏 -->
    <view class="order-tabs">
      <view
        class="order-tab"
        :class="{ 'order-tab--active': activeTab === index }"
        v-for="(tab, index) in tabs"
        :key="tab.key"
        @tap="onTabChange(index)"
      >
        <text>{{ tab.name }}</text>
        <view class="order-tab__line" v-if="activeTab === index" />
      </view>
    </view>

    <!-- 订单列表 -->
    <view class="order-list" v-if="orders.length > 0">
      <view class="order-card card" v-for="order in orders" :key="order.id">
        <!-- 订单头部 -->
        <view class="order-card__header" @tap="onOrderTap(order.id)">
          <text class="order-card__no">订单号：{{ order.order_no }}</text>
          <text
            class="order-card__status"
            :style="{ color: getOrderStatusColor(order.status) }"
          >
            {{ getOrderStatusText(order.status) }}
          </text>
        </view>

        <!-- 商品列表 -->
        <view class="order-card__items" @tap="onOrderTap(order.id)">
          <view
            class="order-item"
            v-for="goods in order.items"
            :key="goods.id"
          >
            <view class="order-item__image">
              <image
                :src="goods.cover_image"
                mode="aspectFill"
                v-if="goods.cover_image"
              />
              <view class="order-item__placeholder" v-else>
                <text>🏕️</text>
              </view>
            </view>
            <view class="order-item__info">
              <text class="order-item__name text-ellipsis">{{ goods.product_name }}</text>
              <text class="order-item__date">日期：{{ goods.date }}</text>
            </view>
            <view class="order-item__right">
              <text class="order-item__price">¥{{ goods.actual_price }}</text>
              <text class="order-item__qty">×{{ goods.quantity }}</text>
            </view>
          </view>
        </view>

        <!-- 订单底部 -->
        <view class="order-card__footer">
          <view class="order-card__total">
            <text>共{{ order.items.length }}件 · 实付</text>
            <text class="order-card__total-price">¥{{ order.actual_amount }}</text>
          </view>
          <view class="order-card__actions">
            <!-- 待支付 -->
            <view
              class="order-btn order-btn--outline"
              v-if="order.status === 'pending_payment'"
              @tap.stop="onCancelOrder(order.id)"
            >
              <text>取消订单</text>
            </view>
            <view
              class="order-btn order-btn--primary"
              v-if="order.status === 'pending_payment'"
              @tap.stop="onPayOrder(order.id)"
            >
              <text>去支付</text>
            </view>

            <!-- 待使用 -->
            <view
              class="order-btn order-btn--outline"
              v-if="order.status === 'paid'"
              @tap.stop="onViewTicket(order.id)"
            >
              <text>查看票</text>
            </view>
            <view
              class="order-btn order-btn--outline"
              v-if="order.status === 'paid'"
              @tap.stop="onRefund(order.id)"
            >
              <text>退款</text>
            </view>

            <!-- 已完成/已取消 -->
            <view
              class="order-btn order-btn--primary"
              v-if="order.status === 'completed' || order.status === 'cancelled'"
              @tap.stop="onRebuy(order.items[0]?.product_id)"
            >
              <text>再次购买</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <EmptyState
      v-if="!loading && orders.length === 0"
      icon="📋"
      title="暂无订单"
      description="去露营吧，留下美好回忆"
      buttonText="去逛逛"
      @action="onGoShopping"
    />

    <!-- 加载中 -->
    <view class="loading-tip" v-if="loading">
      <text>加载中...</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onReachBottom } from '@dcloudio/uni-app'
import { get, post } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import { getOrderStatusText, getOrderStatusColor, formatDate } from '@/utils/util'
import EmptyState from '@/components/empty-state/index.vue'
import type { IOrder, OrderStatus, IPaginationResult } from '@/types'

interface IOrderTab {
  key: string
  name: string
}

// ---- 响应式数据 ----
const tabs = ref<IOrderTab[]>([
  { key: 'all', name: '全部' },
  { key: 'pending_payment', name: '待支付' },
  { key: 'paid', name: '待使用' },
  { key: 'completed', name: '已完成' },
  { key: 'refunding', name: '售后' },
])
const activeTab = ref(0)
const orders = ref<IOrder[]>([])
const loading = ref(true)
const page = ref(1)
const hasMore = ref(true)

// ---- 生命周期 ----
onShow(() => {
  loadOrders()
})

onReachBottom(() => {
  if (hasMore.value && !loading.value) {
    loadMore()
  }
})

// ---- Tab 切换 ----
function onTabChange(index: number) {
  activeTab.value = index
  page.value = 1
  hasMore.value = true
  orders.value = []
  loadOrders()
}

// ---- 加载订单 ----
async function loadOrders() {
  loading.value = true
  try {
    await ensureLogin()
    const tabKey = tabs.value[activeTab.value].key
    const params: Record<string, string | number | boolean | undefined> = {
      page: page.value,
      page_size: 10,
    }
    if (tabKey !== 'all') {
      params.status = tabKey
    }
    const data = await get<IPaginationResult<IOrder>>('/orders', params)
    if (page.value === 1) {
      orders.value = data.items || []
    } else {
      orders.value = [...orders.value, ...(data.items || [])]
    }
    hasMore.value = page.value < data.total_pages
  } catch {
    if (page.value === 1) orders.value = []
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  page.value += 1
  await loadOrders()
}

// ---- 格式化工具 ----
function formatOrderDate(date: string): string {
  return formatDate(date, 'MM-DD HH:mm')
}

// ---- 事件处理 ----

/** 查看订单详情 */
function onOrderTap(id: number) {
  uni.navigateTo({ url: `/pages/order-detail/index?id=${id}` })
}

/** 去支付 */
function onPayOrder(id: number) {
  uni.navigateTo({ url: `/pages/payment/index?order_id=${id}` })
}

/** 取消订单 */
function onCancelOrder(id: number) {
  uni.showModal({
    title: '取消订单',
    content: '确定要取消该订单吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await post(`/orders/${id}/cancel`)
          uni.showToast({ title: '已取消', icon: 'success' })
          page.value = 1
          loadOrders()
        } catch {
          uni.showToast({ title: '取消失败', icon: 'error' })
        }
      }
    },
  })
}

/** 再次购买 */
function onRebuy(productId: number | undefined) {
  if (!productId) return
  uni.navigateTo({ url: `/pages/product-detail/index?id=${productId}` })
}

/** 查看票 */
function onViewTicket(orderId: number) {
  uni.navigateTo({ url: `/pages/ticket/index?order_id=${orderId}` })
}

/** 申请退款 */
function onRefund(id: number) {
  uni.showModal({
    title: '申请退款',
    content: '确定要申请退款吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await post(`/orders/${id}/refund`)
          uni.showToast({ title: '已提交', icon: 'success' })
          page.value = 1
          loadOrders()
        } catch {
          uni.showToast({ title: '退款申请失败', icon: 'error' })
        }
      }
    },
  })
}

/** 空状态 - 去逛逛 */
function onGoShopping() {
  uni.switchTab({ url: '/pages/index/index' })
}
</script>

<style lang="scss" scoped>
.page-order {
  min-height: 100vh;
  background-color: var(--color-bg);
}

/* Tab 栏 — 磨砂玻璃 */
.order-tabs {
  display: flex;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1rpx solid rgba(42, 37, 32, 0.05);
  position: sticky;
  top: 0;
  z-index: 10;
}

.order-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28rpx 0 22rpx;
  position: relative;
  transition: var(--transition-base);

  text {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    letter-spacing: 0.5rpx;
  }

  &--active text {
    color: var(--color-primary);
    font-weight: 700;
  }

  &__line {
    position: absolute;
    bottom: 4rpx;
    width: 44rpx;
    height: 6rpx;
    background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
    border-radius: 3rpx;
  }
}

/* 订单列表 */
.order-list {
  padding: 20rpx 28rpx;
}

.order-card {
  margin-bottom: 20rpx;
  padding: 28rpx;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  border: 1rpx solid rgba(42, 37, 32, 0.03);
  transition: var(--transition-base);

  &:active {
    transform: scale(0.99);
  }

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 20rpx;
    border-bottom: 1rpx solid var(--color-bg-light);
  }

  &__no {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    letter-spacing: 0.5rpx;
  }

  &__status {
    font-size: var(--font-size-sm);
    font-weight: 700;
    letter-spacing: 0.5rpx;
  }

  &__items {
    padding: 16rpx 0;
  }

  &__footer {
    padding-top: 20rpx;
    border-top: 1rpx solid var(--color-bg-light);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__total {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &__total-price {
    font-size: var(--font-size-xl);
    color: var(--color-accent);
    font-weight: 800;
    letter-spacing: 1rpx;
  }

  &__actions {
    display: flex;
    gap: 16rpx;
  }
}

/* 订单商品项 */
.order-item {
  display: flex;
  align-items: center;
  padding: 14rpx 0;

  &__image {
    width: 128rpx;
    height: 128rpx;
    border-radius: var(--radius-lg);
    overflow: hidden;
    flex-shrink: 0;
    margin-right: 20rpx;

    image {
      width: 100%;
      height: 100%;
    }
  }

  &__placeholder {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, var(--color-bg-light), var(--color-bg-warm));
    display: flex;
    justify-content: center;
    align-items: center;

    text {
      font-size: 44rpx;
    }
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name {
    font-size: var(--font-size-base);
    color: var(--color-text);
    font-weight: 600;
    letter-spacing: 0.5rpx;
  }

  &__date {
    display: block;
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    margin-top: 8rpx;
  }

  &__right {
    text-align: right;
    flex-shrink: 0;
    margin-left: 16rpx;
  }

  &__price {
    font-size: var(--font-size-base);
    color: var(--color-text);
    font-weight: 600;
    display: block;
  }

  &__qty {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
  }
}

/* 操作按钮 */
.order-btn {
  height: 64rpx;
  padding: 0 32rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: var(--radius-round);
  font-size: var(--font-size-sm);
  font-weight: 600;
  letter-spacing: 1rpx;
  transition: var(--transition-base);

  &--primary {
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
    box-shadow: 0 4rpx 12rpx rgba(45, 74, 62, 0.2);
    text { color: var(--color-text-white); }
  }

  &--outline {
    border: 2rpx solid rgba(42, 37, 32, 0.15);
    color: var(--color-text-secondary);
    text { color: var(--color-text-secondary); }
  }

  &--text {
    color: var(--color-text-secondary);
  }

  &:active {
    opacity: 0.7;
    transform: scale(0.96);
  }
}

/* 文本省略 */
.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 加载提示 */
.loading-tip {
  text-align: center;
  padding: 48rpx;

  text {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    letter-spacing: 1rpx;
  }
}
</style>
