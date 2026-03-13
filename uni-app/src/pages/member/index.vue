<template>
  <!-- 会员中心 -->
  <view class="page-member">
    <view class="member-tabs">
      <view
        :class="['member-tab', activeTab === index ? 'member-tab--active' : '']"
        v-for="(item, index) in tabs"
        :key="item.key"
        @tap="onTabChange(index)"
      >
        <text>{{ item.name }}</text>
      </view>
    </view>

    <!-- 年卡 -->
    <view class="member-content" v-if="activeTab === 0">
      <view class="annual-card" v-if="annualCard">
        <view class="annual-card__header">
          <text class="annual-card__title">👑 年卡会员</text>
          <text class="annual-card__status">{{ annualCard.status === 'active' ? '生效中' : '已过期' }}</text>
        </view>
        <view class="annual-card__info">
          <view class="annual-card__stat">
            <text class="annual-card__stat-num">{{ annualCard.remaining_days }}</text>
            <text class="annual-card__stat-label">剩余天数</text>
          </view>
          <view class="annual-card__date">{{ annualCard.start_date }} ~ {{ annualCard.end_date }}</view>
        </view>
        <view class="annual-card__benefits">
          <text class="annual-card__benefits-title">权益使用情况</text>
          <view class="benefit-item" v-for="b in annualCard.benefits" :key="b.product_name">
            <text class="benefit-item__name">{{ b.product_name }}</text>
            <text class="benefit-item__usage">已用{{ b.used_times }}次 {{ b.total_times ? '/ 限' + b.total_times + '次' : '/ 不限次' }}</text>
          </view>
        </view>
      </view>
      <EmptyState v-else icon="💳" title="暂未开通年卡" description="开通年卡享受更多权益" buttonText="了解年卡" />
    </view>

    <!-- 次数卡 -->
    <view class="member-content" v-if="activeTab === 1">
      <view class="times-card card" v-for="item in timesCards" :key="item.id">
        <view class="times-card__header">
          <text class="times-card__name">🎟️ {{ item.name }}</text>
          <text :class="['times-card__status', `times-card__status--${item.status}`]">{{ item.status === 'active' ? '有效' : '已过期' }}</text>
        </view>
        <view class="times-card__stats">
          <view class="times-card__stat">
            <text class="times-card__stat-num">{{ item.remaining_times }}</text>
            <text class="times-card__stat-label">剩余次数</text>
          </view>
          <view class="times-card__stat">
            <text class="times-card__stat-num">{{ item.total_times }}</text>
            <text class="times-card__stat-label">总次数</text>
          </view>
        </view>
        <text class="times-card__date">有效期：{{ item.start_date }} ~ {{ item.end_date }}</text>
      </view>
      <!-- 激活输入 -->
      <view class="activate-section card">
        <text class="activate-title">输入激活码领取次数卡</text>
        <view class="activate-input-row">
          <input class="activate-input" placeholder="请输入16位激活码" :value="activateCode" @input="onActivateInput" :maxlength="16" />
          <view class="activate-btn" @tap="onActivateCard"><text>激活</text></view>
        </view>
      </view>
    </view>

    <!-- 积分 -->
    <view class="member-content" v-if="activeTab === 2">
      <view class="points-card card">
        <text class="points-card__label">当前积分</text>
        <text class="points-card__value">⭐ {{ points }}</text>
        <text class="points-card__tip">消费1元=1积分，积分有效期12个月</text>
      </view>
      <view class="points-section card">
        <text class="points-section__title">积分明细</text>
        <view class="points-record"><text>购买A区营位</text><text class="points-record__add">+128</text></view>
        <view class="points-record"><text>购买活动票</text><text class="points-record__add">+258</text></view>
        <view class="points-record"><text>积分兑换</text><text class="points-record__minus">-200</text></view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post } from '@/utils/request'
import { ensureLogin } from '@/utils/auth'
import EmptyState from '@/components/empty-state/index.vue'
import type { IAnnualCard, ITimesCard } from '@/types'

const tabs = ref([
  { key: 'annual', name: '年卡' },
  { key: 'times', name: '次数卡' },
  { key: 'points', name: '积分' },
])
const activeTab = ref(0)
const annualCard = ref<IAnnualCard | null>(null)
const timesCards = ref<ITimesCard[]>([])
const points = ref(0)
const activateCode = ref('')

onLoad((options) => {
  if (options?.tab) {
    const idx = tabs.value.findIndex(t => t.key === options.tab)
    if (idx >= 0) activeTab.value = idx
  }
  loadData()
})

async function loadData() {
  try {
    await ensureLogin()
    const [annualData, timesData, pointsData] = await Promise.all([
      get<IAnnualCard | null>('/members/annual-card').catch(() => null),
      get<ITimesCard[]>('/members/times-cards').catch(() => []),
      get<{ points: number }>('/members/points').catch(() => ({ points: 0 })),
    ])
    annualCard.value = annualData
    timesCards.value = timesData || []
    points.value = pointsData?.points || 0
  } catch {
    uni.showToast({ title: '加载会员数据失败', icon: 'error' })
  }
}

function onTabChange(index: number) {
  activeTab.value = index
}

function onActivateInput(e: any) {
  activateCode.value = e.detail.value
}

async function onActivateCard() {
  if (!activateCode.value.trim()) {
    uni.showToast({ title: '请输入激活码', icon: 'none' })
    return
  }
  try {
    await post('/members/times-cards/activate', { code: activateCode.value })
    uni.showToast({ title: '激活成功！', icon: 'success' })
    activateCode.value = ''
    loadData()
  } catch {
    uni.showToast({ title: '激活失败', icon: 'error' })
  }
}
</script>

<style lang="scss" scoped>
.page-member { min-height: 100vh; background-color: var(--color-bg); }

.member-tabs {
  display: flex; background-color: var(--color-bg-white); border-bottom: 1rpx solid #F0F0F0; position: sticky; top: 0; z-index: 10;
}

.member-tab {
  flex: 1; text-align: center; padding: 24rpx 0; position: relative;
  text { font-size: var(--font-size-base); color: var(--color-text-secondary); }
  &--active {
    text { color: var(--color-primary); font-weight: 600; }
    &::after { content: ''; position: absolute; bottom: 4rpx; left: 50%; transform: translateX(-50%); width: 40rpx; height: 6rpx; background-color: var(--color-primary); border-radius: 3rpx; }
  }
}

.member-content { padding: 24rpx; }

.annual-card {
  background: linear-gradient(135deg, #1A1A1A, #333); border-radius: var(--radius-xl); padding: 32rpx; color: #fff;
  &__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24rpx; }
  &__title { font-size: var(--font-size-xl); font-weight: 700; color: #FFD700; }
  &__status { font-size: var(--font-size-sm); color: #81C784; padding: 4rpx 16rpx; border: 1rpx solid #81C784; border-radius: var(--radius-round); }
  &__info { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 28rpx; }
  &__stat { display: flex; flex-direction: column; }
  &__stat-num { font-size: 56rpx; font-weight: 700; color: #FFD700; }
  &__stat-label { font-size: var(--font-size-sm); color: rgba(255,255,255,0.6); }
  &__date { font-size: var(--font-size-sm); color: rgba(255,255,255,0.5); }
  &__benefits { border-top: 1rpx solid rgba(255,255,255,0.1); padding-top: 20rpx; }
  &__benefits-title { font-size: var(--font-size-base); font-weight: 500; margin-bottom: 12rpx; display: block; }
}

.benefit-item {
  display: flex; justify-content: space-between; padding: 8rpx 0;
  &__name { font-size: var(--font-size-sm); color: rgba(255,255,255,0.8); }
  &__usage { font-size: var(--font-size-sm); color: #FFD700; }
}

.times-card {
  padding: 24rpx; margin-bottom: 16rpx;
  &__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20rpx; }
  &__name { font-size: var(--font-size-md); font-weight: 600; }
  &__status { font-size: var(--font-size-xs); padding: 4rpx 12rpx; border-radius: var(--radius-round);
    &--active { background-color: var(--color-primary-bg); color: var(--color-primary); }
    &--expired { background-color: rgba(229,57,53,0.08); color: var(--color-red); }
  }
  &__stats { display: flex; gap: 48rpx; margin-bottom: 12rpx; }
  &__stat { display: flex; flex-direction: column; }
  &__stat-num { font-size: var(--font-size-xxl); font-weight: 700; color: var(--color-primary); }
  &__stat-label { font-size: var(--font-size-xs); color: var(--color-text-placeholder); }
  &__date { font-size: var(--font-size-sm); color: var(--color-text-placeholder); }
}

.activate-section { padding: 24rpx; }
.activate-title { font-size: var(--font-size-md); font-weight: 600; display: block; margin-bottom: 16rpx; }
.activate-input-row { display: flex; gap: 16rpx; }
.activate-input { flex: 1; height: 80rpx; background-color: var(--color-bg-grey); border-radius: var(--radius-md); padding: 0 20rpx; font-size: var(--font-size-base); letter-spacing: 4rpx; }
.activate-btn { height: 80rpx; padding: 0 36rpx; display: flex; align-items: center; background-color: var(--color-primary); border-radius: var(--radius-md);
  text { color: #fff; font-size: var(--font-size-base); font-weight: 600; }
  &:active { opacity: 0.85; }
}

.points-card {
  padding: 32rpx; text-align: center;
  &__label { font-size: var(--font-size-base); color: var(--color-text-secondary); display: block; }
  &__value { font-size: 56rpx; font-weight: 700; color: var(--color-primary); display: block; margin: 12rpx 0; }
  &__tip { font-size: var(--font-size-sm); color: var(--color-text-placeholder); }
}

.points-section { padding: 24rpx; margin-top: 16rpx;
  &__title { font-size: var(--font-size-md); font-weight: 600; display: block; margin-bottom: 16rpx; }
}

.points-record {
  display: flex; justify-content: space-between; padding: 16rpx 0; border-bottom: 1rpx solid #F5F5F5;
  text { font-size: var(--font-size-base); color: var(--color-text-secondary); }
  &__add { color: var(--color-primary) !important; font-weight: 600; }
  &__minus { color: var(--color-red) !important; font-weight: 600; }
}
</style>
