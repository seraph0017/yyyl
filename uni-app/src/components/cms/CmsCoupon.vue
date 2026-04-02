<template>
  <view class="cms-coupon">
    <!-- 加载中骨架 -->
    <view v-if="loading" class="cms-coupon__loading-wrap">
      <view class="cms-coupon__skeleton" v-for="i in 3" :key="i" />
    </view>

    <!-- 加载失败 -->
    <view v-else-if="loadError" class="cms-coupon__error">
      <text class="cms-coupon__error-text">优惠券加载失败</text>
      <view class="cms-coupon__retry" @tap="loadCoupons">
        <text>点击重试</text>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else-if="coupons.length === 0" class="cms-coupon__empty">
      <text class="cms-coupon__empty-text">暂无优惠券</text>
    </view>

    <!-- 横向滚动 -->
    <template v-else-if="layoutMode === 'horizontal'">
      <scroll-view
      class="cms-coupon__scroll"
      scroll-x
      :show-scrollbar="false"
    >
      <view class="cms-coupon__scroll-inner">
        <view
          v-for="coupon in coupons"
          :key="coupon.id"
          class="cms-coupon__card"
        >
          <view class="cms-coupon__info">
            <view class="cms-coupon__amount">
              <text class="cms-coupon__symbol">¥</text>
              <text class="cms-coupon__value">{{ coupon.discount_value }}</text>
            </view>
            <text class="cms-coupon__condition">{{ coupon.condition_text }}</text>
            <text class="cms-coupon__expire">{{ coupon.expire_text }}</text>
          </view>
          <view class="cms-coupon__action">
            <view
              class="cms-coupon__btn"
              :class="{ 'cms-coupon__btn--disabled': coupon.btn_disabled }"
              @tap.stop="onClaimTap(coupon)"
            >
              <text>{{ coupon.btn_text }}</text>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>
    </template>

    <!-- 纵向堆叠 -->
    <view v-else class="cms-coupon__vertical">
      <view
        v-for="coupon in coupons"
        :key="coupon.id"
        class="cms-coupon__card cms-coupon__card--vertical"
      >
        <view class="cms-coupon__info">
          <view class="cms-coupon__amount">
            <text class="cms-coupon__symbol">¥</text>
            <text class="cms-coupon__value">{{ coupon.discount_value }}</text>
          </view>
          <text class="cms-coupon__condition">{{ coupon.condition_text }}</text>
          <text class="cms-coupon__expire">{{ coupon.expire_text }}</text>
        </view>
        <view class="cms-coupon__action">
          <view
            class="cms-coupon__btn"
            :class="{ 'cms-coupon__btn--disabled': coupon.btn_disabled }"
            @tap.stop="onClaimTap(coupon)"
          >
            <text>{{ coupon.btn_text }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 优惠券区块组件
 * 挂载时请求优惠券详情，支持领取交互
 */
import { ref, computed, onMounted } from 'vue'
import { get, post } from '@/utils/request'
import { useUserStore } from '@/store/user'
import type { CmsCouponProps, CmsComponentStyle } from '@/types/cms'

interface CouponDisplay {
  id: number
  discount_value: number
  condition_text: string
  expire_text: string
  btn_text: string
  btn_disabled: boolean
  claimed: boolean
  status: string
  claiming: boolean
}

interface Props {
  data: CmsCouponProps
  componentStyle?: CmsComponentStyle
}

const props = defineProps<Props>()

const coupons = ref<CouponDisplay[]>([])
const loading = ref(true)
const loadError = ref(false)

const userStore = useUserStore()

/** 布局模式，默认 horizontal */
const layoutMode = computed(() => props.data.layout || 'horizontal')

/** 加载优惠券详情 */
async function loadCoupons() {
  if (!props.data.coupon_ids?.length) {
    loading.value = false
    return
  }

  loading.value = true
  loadError.value = false

  try {
    const result = await get<Array<Record<string, unknown>>>(
      '/coupons',
      { ids: props.data.coupon_ids.join(',') },
      { needAuth: false, showError: false },
    )

    const list = Array.isArray(result) ? result : []
    coupons.value = list.map((item) => {
      const status = String(item.status || 'available')
      const claimed = !!item.is_claimed

      let btnText = '立即领取'
      let btnDisabled = false

      if (claimed) {
        btnText = '已领取'
        btnDisabled = true
      } else if (status === 'sold_out' || (item.stock as number) === 0) {
        btnText = '已抢光'
        btnDisabled = true
      } else if (status === 'not_started') {
        btnText = '未开始'
        btnDisabled = true
      } else if (status === 'expired') {
        btnText = '已过期'
        btnDisabled = true
      }

      return {
        id: item.id as number,
        discount_value: (item.discount_value as number) || 0,
        condition_text: (item.min_amount as number) ? `满${item.min_amount}可用` : '无门槛',
        expire_text: (item.end_time as string) ? `${String(item.end_time).slice(0, 10)} 到期` : '',
        btn_text: btnText,
        btn_disabled: btnDisabled,
        claimed,
        status,
        claiming: false,
      }
    })
  } catch (err) {
    console.warn('[CmsCoupon] 优惠券加载失败:', err)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/** 领取优惠券 */
async function onClaimTap(coupon: CouponDisplay) {
  if (coupon.btn_disabled || coupon.claiming) return

  // 未登录检查
  if (!userStore.isLoggedIn) {
    uni.navigateTo({ url: '/pages/mine/index' })
    return
  }

  // 设置 loading 状态
  const idx = coupons.value.findIndex((c) => c.id === coupon.id)
  if (idx >= 0) {
    coupons.value = coupons.value.map((c, i) =>
      i === idx ? { ...c, claiming: true, btn_text: '领取中...' } : c,
    )
  }

  try {
    await post(`/coupons/${coupon.id}/claim`, {}, { showError: false })
    // 领取成功 — 更新按钮状态
    if (idx >= 0) {
      coupons.value = coupons.value.map((c, i) =>
        i === idx ? { ...c, btn_text: '已领取', btn_disabled: true, claimed: true, claiming: false } : c,
      )
    }
    uni.showToast({ title: '领取成功', icon: 'success' })
  } catch (err) {
    const errMsg = (err as Error)?.message || ''

    if (errMsg.includes('已领取') || errMsg.includes('already')) {
      if (idx >= 0) {
        coupons.value = coupons.value.map((c, i) =>
          i === idx ? { ...c, btn_text: '已领取', btn_disabled: true, claimed: true, claiming: false } : c,
        )
      }
    } else {
      // 恢复按钮状态
      if (idx >= 0) {
        coupons.value = coupons.value.map((c, i) =>
          i === idx ? { ...c, claiming: false, btn_text: '立即领取' } : c,
        )
      }
      uni.showToast({ title: '领取失败，请稍后重试', icon: 'none' })
    }
  }
}

onMounted(() => {
  loadCoupons()
})
</script>

<style lang="scss" scoped>
.cms-coupon {
  padding: 0 var(--spacing-lg);

  &__scroll {
    white-space: nowrap;
  }

  &__scroll-inner {
    display: inline-flex;
    gap: 16rpx;
  }

  &__vertical {
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }

  &__card {
    display: inline-flex;
    width: 320rpx;
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
    border-radius: var(--radius-lg);
    padding: 20rpx 24rpx;
    color: var(--color-text-white);
    position: relative;
    overflow: hidden;
    align-items: center;
    justify-content: space-between;

    // 优惠券锯齿边缘
    &::before,
    &::after {
      content: '';
      position: absolute;
      width: 24rpx;
      height: 24rpx;
      background: var(--color-bg);
      border-radius: 50%;
      top: 50%;
      transform: translateY(-50%);
    }
    &::before {
      left: -12rpx;
    }
    &::after {
      right: -12rpx;
    }

    // 纵向堆叠模式 — 全宽
    &--vertical {
      width: 100%;
      display: flex;
    }
  }

  &__info {
    flex: 1;
  }

  &__amount {
    display: flex;
    align-items: baseline;
  }

  &__symbol {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-accent);
  }

  &__value {
    font-size: var(--font-size-hero, 48rpx);
    font-weight: 800;
    color: var(--color-accent);
    margin-left: 4rpx;
  }

  &__condition {
    font-size: var(--font-size-xs);
    color: rgba(255, 254, 250, 0.8);
    margin-top: 4rpx;
    display: block;
  }

  &__expire {
    font-size: var(--font-size-xs);
    color: rgba(255, 254, 250, 0.6);
    margin-top: 4rpx;
    display: block;
  }

  &__action {
    flex-shrink: 0;
    margin-left: 16rpx;
  }

  &__btn {
    font-size: var(--font-size-xs);
    padding: 14rpx 24rpx;
    min-height: 56rpx;
    border: 1rpx solid rgba(255, 255, 255, 0.6);
    border-radius: var(--radius-round);
    color: var(--color-text-white);
    white-space: nowrap;

    &:active {
      opacity: 0.7;
    }

    // 不可领取状态
    &--disabled {
      opacity: 0.5;
      border-color: rgba(255, 255, 255, 0.3);
    }
  }

  // 加载骨架
  &__loading-wrap {
    display: flex;
    gap: 16rpx;
  }

  &__skeleton {
    width: 320rpx;
    height: 120rpx;
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    animation: shimmer 2s infinite;
    border-radius: var(--radius-lg);
    flex-shrink: 0;
  }

  // 加载失败
  &__error {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32rpx 0;
  }

  &__error-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    margin-bottom: 16rpx;
  }

  &__retry {
    padding: 12rpx 36rpx;
    background: var(--color-primary);
    border-radius: var(--radius-round);
    color: var(--color-text-white);
    font-size: var(--font-size-sm);

    &:active {
      opacity: 0.85;
    }
  }

  // 空状态
  &__empty {
    display: flex;
    justify-content: center;
    padding: 32rpx 0;
  }

  &__empty-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
  }
}

@keyframes shimmer {
  0% { background-position: 300% 0; }
  100% { background-position: -300% 0; }
}
</style>
