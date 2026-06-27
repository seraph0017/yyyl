<template>
  <view class="page-member">
    <view class="member-header">
      <text class="member-header__eyebrow">会员中心</text>
      <text class="member-header__title">会员卡</text>
      <text class="member-header__desc">统一查看你的会员权益、状态和激活入口</text>
    </view>

    <view class="member-card" v-if="membershipCard">
      <view class="member-card__top">
        <view>
          <text class="member-card__name">会员卡</text>
          <text class="member-card__meta">{{ membershipCard.card_type_label }} · {{ membershipCard.usage_mode_label }}</text>
        </view>
        <text :class="['member-card__status', `member-card__status--${membershipCard.status}`]">{{ membershipCard.status_label }}</text>
      </view>

      <view class="member-card__stats">
        <view class="member-card__stat">
          <text class="member-card__stat-value">{{ membershipCard.remaining_days_label }}</text>
          <text class="member-card__stat-label">剩余天数</text>
        </view>
        <view class="member-card__stat">
          <text class="member-card__stat-value">{{ membershipCard.remaining_times_label }}</text>
          <text class="member-card__stat-label">剩余次数</text>
        </view>
      </view>

      <view class="member-card__grid">
        <view class="member-card__field">
          <text class="member-card__field-label">卡种</text>
          <text class="member-card__field-value">{{ membershipCard.card_type_label }}</text>
        </view>
        <view class="member-card__field">
          <text class="member-card__field-label">使用模式</text>
          <text class="member-card__field-value">{{ membershipCard.usage_mode_label }}</text>
        </view>
        <view class="member-card__field">
          <text class="member-card__field-label">状态</text>
          <text class="member-card__field-value">{{ membershipCard.status_label }}</text>
        </view>
        <view class="member-card__field">
          <text class="member-card__field-label">有效期</text>
          <text class="member-card__field-value">{{ membershipCard.valid_range_label }}</text>
        </view>
        <view class="member-card__field">
          <text class="member-card__field-label">适用商品</text>
          <text class="member-card__field-value member-card__field-value--muted">{{ membershipCard.applicable_products_label }}</text>
        </view>
      </view>
    </view>

    <view class="member-card member-card--empty" v-else>
      <text class="member-card__name">会员卡</text>
      <text class="member-card__empty-text">暂未获取到可用会员卡</text>
      <text class="member-card__empty-desc">可以先激活旧卡，或等待统一会员卡接口接入。</text>
    </view>

    <view class="activation-panel">
      <text class="activation-panel__title">激活会员卡</text>
      <text class="activation-panel__desc">支持统一激活接口，旧激活码流程也兼容</text>
      <view class="activation-panel__row">
        <input
          class="activation-panel__input"
          placeholder="请输入激活码"
          :value="activateCode"
          @input="onActivateInput"
          :maxlength="32"
        />
        <view class="activation-panel__button" @tap="onActivateCard">
          <text>激活</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ensureLogin } from '@/utils/auth'
import { get, post } from '@/utils/request'
import type {
  IMembershipCard,
  IMembershipCardApiResponse,
  ITimesCard,
  IAnnualCard,
} from '@/types'

const membershipCard = ref<IMembershipCard | null>(null)
const activateCode = ref('')
const loading = ref(false)

const cardTypeLabelMap: Record<IMembershipCard['card_type'], string> = {
  annual: '年卡',
  times: '次数卡',
}

const usageModeLabelMap: Record<IMembershipCard['usage_mode'], string> = {
  unlimited: '无限',
  limited: '次数限制',
}

const statusLabelMap: Record<IMembershipCard['status'], string> = {
  active: '生效中',
  expired: '已过期',
  cancelled: '已取消',
  inactive: '未激活',
}

onLoad(() => {
  loadData()
})

onShow(() => {
  if (!membershipCard.value && !loading.value) {
    loadData()
  }
})

async function loadData() {
  loading.value = true
  try {
    const loggedIn = await ensureLogin()
    if (!loggedIn) return
    membershipCard.value = await loadMembershipCard()
  } catch {
    uni.showToast({ title: '加载会员卡失败', icon: 'error' })
  } finally {
    loading.value = false
  }
}

async function loadMembershipCard(): Promise<IMembershipCard | null> {
  const unifiedCard = await get<IMembershipCardApiResponse>('/members/membership-card', undefined, {
    showError: false,
  }).catch(() => null)
  if (unifiedCard) {
    return normalizeMembershipCard(unifiedCard)
  }

  const [annualData, timesData] = await Promise.all([
    get<{ current_card: IAnnualCard | null }>('/members/annual-card', undefined, { showError: false }).catch(() => ({ current_card: null })),
    get<ITimesCard[]>('/members/times-cards', undefined, { showError: false }).catch(() => []),
  ])

  return buildMembershipCard(annualData.current_card, timesData || [])
}

function normalizeMembershipCard(data: IMembershipCardApiResponse): IMembershipCard {
  if ('card_type' in data) {
    return {
      ...data,
      card_type_label: data.card_type_label || cardTypeLabelMap[data.card_type],
      usage_mode_label: data.usage_mode_label || usageModeLabelMap[data.usage_mode],
      status_label: data.status_label || statusLabelMap[data.status],
      valid_range_label: data.valid_range_label || formatValidRange(data.start_date, data.end_date),
      remaining_days_label: data.remaining_days_label || formatCountLabel(data.remaining_days, '天'),
      remaining_times_label: data.remaining_times_label || formatCountLabel(data.remaining_times, '次'),
      applicable_products_label: data.applicable_products_label || formatApplicableProducts(data.applicable_products),
    }
  }

  return buildMembershipCard(data.current_card, data.times_cards || [])
}

function buildMembershipCard(currentCard: IAnnualCard | null, timesCards: ITimesCard[]): IMembershipCard {
  if (currentCard) {
    const benefitProducts = currentCard.benefits.map(item => item.product_name).filter(Boolean)
    return {
      card_type: 'annual',
      card_type_label: '年卡',
      usage_mode: 'unlimited',
      usage_mode_label: '无限',
      status: currentCard.status === 'active' ? 'active' : currentCard.status === 'expired' ? 'expired' : 'cancelled',
      status_label: statusLabelMap[currentCard.status === 'active' ? 'active' : currentCard.status === 'expired' ? 'expired' : 'cancelled'],
      start_date: currentCard.start_date,
      end_date: currentCard.end_date,
      valid_range_label: formatValidRange(currentCard.start_date, currentCard.end_date),
      remaining_days: currentCard.remaining_days,
      remaining_days_label: formatCountLabel(currentCard.remaining_days, '天'),
      remaining_times: null,
      remaining_times_label: '不限',
      applicable_products: benefitProducts,
      applicable_products_label: formatApplicableProducts(benefitProducts),
      activation_mode: 'code',
    }
  }

  const activeTimesCard = timesCards.find(item => item.status === 'active') || timesCards[0] || null
  const applicableProducts = activeTimesCard?.applicable_products || []
  return {
    card_type: 'times',
    card_type_label: '次数卡',
    usage_mode: 'limited',
    usage_mode_label: activeTimesCard ? '次数限制' : '次数限制',
    status: activeTimesCard ? activeTimesCard.status : 'inactive',
    status_label: statusLabelMap[activeTimesCard ? activeTimesCard.status : 'inactive'],
    start_date: activeTimesCard?.start_date || '',
    end_date: activeTimesCard?.end_date || '',
    valid_range_label: formatValidRange(activeTimesCard?.start_date || '', activeTimesCard?.end_date || ''),
    remaining_days: null,
    remaining_days_label: '不限',
    remaining_times: activeTimesCard ? activeTimesCard.remaining_times : 0,
    remaining_times_label: formatCountLabel(activeTimesCard ? activeTimesCard.remaining_times : 0, '次'),
    applicable_products: applicableProducts,
    applicable_products_label: formatApplicableProducts(applicableProducts),
    activation_mode: 'code',
  }
}

function formatValidRange(startDate: string, endDate: string): string {
  if (startDate && endDate) {
    return `${startDate} ~ ${endDate}`
  }
  if (startDate || endDate) {
    return startDate || endDate
  }
  return '暂无'
}

function formatCountLabel(value: number | null, unit: '天' | '次'): string {
  if (value === null) {
    return '不限'
  }
  return `${value}${unit}`
}

function formatApplicableProducts(products: Array<string | number>): string {
  if (!products.length) {
    return '全部适用商品'
  }
  return products.map(item => String(item)).join('、')
}

async function onActivateCard() {
  const code = activateCode.value.trim()
  if (!code) {
    uni.showToast({ title: '请输入激活码', icon: 'none' })
    return
  }

  try {
    await post('/members/membership-card/activate', { code }, { showError: false })
    uni.showToast({ title: '激活成功', icon: 'success' })
    activateCode.value = ''
    await loadData()
    return
  } catch {
    try {
      await post('/members/times-cards/activate', { code }, { showError: false })
      uni.showToast({ title: '激活成功', icon: 'success' })
      activateCode.value = ''
      await loadData()
      return
    } catch {
      uni.showToast({ title: '激活失败', icon: 'error' })
    }
  }
}

function onActivateInput(e: InputEvent) {
  const target = e.target as HTMLInputElement | null
  activateCode.value = target?.value || ''
}
</script>

<style lang="scss" scoped>
.page-member {
  min-height: 100vh;
  padding: 24rpx;
  background: linear-gradient(180deg, #f6f7f2 0%, #ffffff 34%, #f7f2e8 100%);
  box-sizing: border-box;
}

.member-header {
  margin-bottom: 24rpx;
  &__eyebrow {
    display: block;
    font-size: 24rpx;
    color: #8b8f7a;
    margin-bottom: 8rpx;
  }
  &__title {
    display: block;
    font-size: 44rpx;
    font-weight: 700;
    color: #2d4a3e;
    margin-bottom: 8rpx;
  }
  &__desc {
    display: block;
    font-size: 26rpx;
    color: #69736d;
    line-height: 1.6;
  }
}

.member-card {
  background: linear-gradient(135deg, #2d4a3e 0%, #3d5d4f 48%, #6d5130 100%);
  border-radius: 24rpx;
  padding: 28rpx;
  color: #fff;
  margin-bottom: 20rpx;
  box-shadow: 0 12rpx 28rpx rgba(45, 74, 62, 0.18);

  &--empty {
    background: #ffffff;
    color: #2d4a3e;
    border: 1rpx solid #e8ece5;
  }

  &__top {
    display: flex;
    justify-content: space-between;
    gap: 20rpx;
    margin-bottom: 24rpx;
  }

  &__name {
    display: block;
    font-size: 34rpx;
    font-weight: 700;
    margin-bottom: 6rpx;
  }

  &__meta {
    display: block;
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.78);
  }

  &--empty &__meta {
    color: #6b766f;
  }

  &__status {
    flex-shrink: 0;
    height: 44rpx;
    line-height: 44rpx;
    padding: 0 16rpx;
    border-radius: 999rpx;
    font-size: 22rpx;
    background: rgba(255, 255, 255, 0.18);
    &--active {
      background: rgba(129, 199, 132, 0.2);
      color: #dff4e4;
    }
    &--expired,
    &--cancelled,
    &--inactive {
      background: rgba(255, 255, 255, 0.14);
      color: rgba(255, 255, 255, 0.82);
    }
  }

  &__stats {
    display: flex;
    gap: 20rpx;
    margin-bottom: 20rpx;
  }

  &__stat {
    flex: 1;
    min-width: 0;
    padding: 20rpx 18rpx;
    border-radius: 20rpx;
    background: rgba(255, 255, 255, 0.12);
  }

  &__stat-value {
    display: block;
    font-size: 34rpx;
    font-weight: 700;
    margin-bottom: 6rpx;
  }

  &__stat-label {
    display: block;
    font-size: 22rpx;
    color: rgba(255, 255, 255, 0.78);
  }

  &__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16rpx;
  }

  &__field {
    min-width: 0;
    padding: 16rpx 18rpx;
    border-radius: 18rpx;
    background: rgba(255, 255, 255, 0.1);
  }

  &--empty &__field {
    background: #f6f8f3;
  }

  &__field-label {
    display: block;
    font-size: 22rpx;
    color: rgba(255, 255, 255, 0.72);
    margin-bottom: 8rpx;
  }

  &--empty &__field-label {
    color: #7b857d;
  }

  &__field-value {
    display: block;
    font-size: 26rpx;
    font-weight: 600;
    word-break: break-word;
    line-height: 1.45;
    &--muted {
      font-weight: 500;
    }
  }

  &__empty-text {
    display: block;
    font-size: 30rpx;
    font-weight: 600;
    margin: 18rpx 0 8rpx;
  }

  &__empty-desc {
    display: block;
    font-size: 24rpx;
    color: #6b766f;
    line-height: 1.6;
  }
}

.activation-panel {
  padding: 24rpx;
  border-radius: 24rpx;
  background: #fff;
  border: 1rpx solid #e8ece5;

  &__title {
    display: block;
    font-size: 30rpx;
    font-weight: 700;
    color: #2d4a3e;
    margin-bottom: 8rpx;
  }

  &__desc {
    display: block;
    font-size: 24rpx;
    color: #6b766f;
    margin-bottom: 20rpx;
  }

  &__row {
    display: flex;
    gap: 16rpx;
  }

  &__input {
    flex: 1;
    height: 80rpx;
    min-width: 0;
    padding: 0 20rpx;
    border-radius: 18rpx;
    background: #f6f8f3;
    font-size: 28rpx;
    letter-spacing: 2rpx;
    box-sizing: border-box;
  }

  &__button {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 80rpx;
    padding: 0 32rpx;
    border-radius: 18rpx;
    background: #c8a872;
    flex-shrink: 0;
    text {
      color: #fff;
      font-size: 28rpx;
      font-weight: 600;
    }
  }
}
</style>
