<template>
  <div class="page-container dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <div class="dashboard-header__left">
        <h2 class="dashboard-header__title">数据总览</h2>
        <span class="dashboard-header__date">{{ todayStr }}</span>
      </div>
      <div class="dashboard-header__right">
        <div class="live-indicator" v-if="isLive">
          <span class="live-indicator__dot" />
          <span class="live-indicator__text">实时</span>
        </div>
      </div>
    </div>

    <!-- 实时数据卡片 -->
    <el-row :gutter="20" class="mb-20">
      <el-col :span="6" v-for="card in realtimeCards" :key="card.title">
        <div class="stat-card" :style="{ '--card-accent': card.color }">
          <div class="stat-card__icon-ring">
            <el-icon :size="22"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-card__body">
            <div class="stat-card__label">{{ card.title }}</div>
            <div class="stat-card__value">{{ card.value }}</div>
            <div class="stat-card__trend" :class="card.trend === 'up' ? 'trend--up' : card.trend === 'down' ? 'trend--down' : ''">
              <el-icon v-if="card.trend === 'up'" :size="12"><Top /></el-icon>
              <el-icon v-else-if="card.trend === 'down'" :size="12"><Bottom /></el-icon>
              <span>{{ card.change }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 趋势图 + 销售排行 -->
    <el-row :gutter="20" class="mb-20">
      <el-col :span="16">
        <div class="card-box">
          <div class="card-box__header">
            <h3 class="card-box__title">
              <span class="card-box__title-bar" />
              趋势概览
            </h3>
            <el-radio-group v-model="trendDays" size="small" @change="fetchTrends">
              <el-radio-button :value="7">近7天</el-radio-button>
              <el-radio-button :value="30">近30天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="trendChartRef" class="chart-container" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box">
          <div class="card-box__header">
            <h3 class="card-box__title">
              <span class="card-box__title-bar" />
              销售排行
            </h3>
            <el-radio-group v-model="rankSort" size="small" @change="fetchRanking">
              <el-radio-button value="sales_count">销量</el-radio-button>
              <el-radio-button value="sales_amount">金额</el-radio-button>
            </el-radio-group>
          </div>
          <div class="ranking-list">
            <div v-for="(item, idx) in rankingList.slice(0, 5)" :key="item.product_id" class="ranking-item">
              <div class="ranking-item__medal" :class="{ 'ranking-item__medal--gold': idx === 0, 'ranking-item__medal--silver': idx === 1, 'ranking-item__medal--bronze': idx === 2 }">
                {{ idx + 1 }}
              </div>
              <div class="ranking-item__info">
                <span class="ranking-item__name">{{ item.product_name }}</span>
                <div class="ranking-item__bar">
                  <div class="ranking-item__bar-fill" :style="{ width: getBarWidth(item, idx) }" />
                </div>
              </div>
              <span class="ranking-item__value">
                {{ rankSort === 'sales_count' ? item.sales_count + '单' : '¥' + formatPrice(item.sales_amount) }}
              </span>
            </div>
            <el-empty v-if="!rankingList.length" description="暂无数据" :image-size="60" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 品类收入 + 会员数据 + 财务概览 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <div class="card-box">
          <h3 class="card-box__title mb-16">
            <span class="card-box__title-bar" />
            品类收入
          </h3>
          <div ref="pieChartRef" class="chart-container" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box">
          <h3 class="card-box__title mb-16">
            <span class="card-box__title-bar" />
            会员数据
          </h3>
          <div class="member-grid">
            <div class="member-card">
              <div class="member-card__value">{{ memberStats.total_members || 0 }}</div>
              <div class="member-card__label">总会员</div>
            </div>
            <div class="member-card member-card--primary">
              <div class="member-card__value">{{ memberStats.annual_members || 0 }}</div>
              <div class="member-card__label">年卡会员</div>
            </div>
            <div class="member-card member-card--accent">
              <div class="member-card__value">{{ memberStats.times_card_holders || 0 }}</div>
              <div class="member-card__label">次数卡</div>
            </div>
            <div class="member-card member-card--blue">
              <div class="member-card__value">{{ memberStats.active_members || 0 }}</div>
              <div class="member-card__label">活跃会员</div>
            </div>
          </div>
          <el-divider />
          <div class="member-new-row">
            <div class="member-new-item">
              <span class="member-new-item__value">{{ memberStats.new_today || 0 }}</span>
              <span class="member-new-item__label">今日新增</span>
            </div>
            <div class="member-new-item">
              <span class="member-new-item__value">{{ memberStats.new_this_week || 0 }}</span>
              <span class="member-new-item__label">本周新增</span>
            </div>
            <div class="member-new-item">
              <span class="member-new-item__value">{{ memberStats.new_this_month || 0 }}</span>
              <span class="member-new-item__label">本月新增</span>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box">
          <h3 class="card-box__title mb-16">
            <span class="card-box__title-bar" />
            财务概览
          </h3>
          <div class="finance-list">
            <div class="finance-row">
              <span class="finance-row__label">待确认</span>
              <span class="finance-row__value text-warning">¥{{ formatPrice(financeSummary.pending_amount || 0) }}</span>
            </div>
            <div class="finance-row">
              <span class="finance-row__label">可提现</span>
              <span class="finance-row__value text-success">¥{{ formatPrice(financeSummary.withdrawable_amount || 0) }}</span>
            </div>
            <div class="finance-row">
              <span class="finance-row__label">押金专户</span>
              <span class="finance-row__value text-info">¥{{ formatPrice(financeSummary.deposit_amount || 0) }}</span>
            </div>
          </div>
          <el-divider />
          <div class="finance-highlight">
            <div class="finance-highlight__header">
              <span class="finance-highlight__label">本月收入</span>
              <el-tag :type="(financeSummary.mom_rate || 0) >= 0 ? 'success' : 'danger'" size="small" round effect="plain">
                {{ (financeSummary.mom_rate || 0) >= 0 ? '+' : '' }}{{ (financeSummary.mom_rate || 0).toFixed(1) }}%
              </el-tag>
            </div>
            <div class="finance-highlight__value">¥{{ formatPrice(financeSummary.month_income || 0) }}</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Top, Bottom, ShoppingCart, Money, UserFilled, WarningFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getRealtimeData, getTrends, getSalesRanking, getMemberStats, getFinanceSummary, getCategoryRevenue } from '@/api/dashboard'
import { formatPrice } from '@/utils'
import type { RealtimeData, SalesRankingItem, MemberStats, FinanceSummary, CategoryRevenue } from '@/types'

const isLive = ref(true)
const todayStr = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
})

const realtimeData = ref<Partial<RealtimeData>>({})
const trendDays = ref(7)
const rankSort = ref<'sales_count' | 'sales_amount'>('sales_count')
const rankingList = ref<SalesRankingItem[]>([])
const memberStats = ref<Partial<MemberStats>>({})
const financeSummary = ref<Partial<FinanceSummary>>({})

const trendChartRef = ref<HTMLElement>()
const pieChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

const realtimeCards = computed(() => [
  {
    title: '今日订单',
    value: realtimeData.value.today_orders || 0,
    change: `较昨日 ${Math.abs((realtimeData.value.today_orders || 0) - (realtimeData.value.yesterday_orders || 0))}`,
    trend: realtimeData.value.orders_trend || 'flat',
    color: '#3d8b5e',
    icon: ShoppingCart,
  },
  {
    title: '今日收入',
    value: '¥' + formatPrice(realtimeData.value.today_income || 0),
    change: `较昨日 ¥${formatPrice(Math.abs((realtimeData.value.today_income || 0) - (realtimeData.value.yesterday_income || 0)))}`,
    trend: realtimeData.value.income_trend || 'flat',
    color: '#c8a872',
    icon: Money,
  },
  {
    title: '在营人数',
    value: realtimeData.value.current_visitors || 0,
    change: '当前在营',
    trend: 'flat',
    color: '#4a8ba8',
    icon: UserFilled,
  },
  {
    title: '库存告警',
    value: realtimeData.value.stock_alerts || 0,
    change: '低于阈值',
    trend: (realtimeData.value.stock_alerts || 0) > 0 ? 'up' : 'flat',
    color: '#c45c4a',
    icon: WarningFilled,
  },
])

function getBarWidth(item: SalesRankingItem, idx: number): string {
  if (!rankingList.value.length) return '0%'
  const max = rankSort.value === 'sales_count'
    ? rankingList.value[0].sales_count
    : rankingList.value[0].sales_amount
  const val = rankSort.value === 'sales_count' ? item.sales_count : item.sales_amount
  return `${(val / max * 100).toFixed(0)}%`
}

async function fetchRealtime() {
  try {
    const res = await getRealtimeData()
    realtimeData.value = res.data
  } catch {
    realtimeData.value = {
      today_orders: 42, today_income: 1268000, current_visitors: 18, stock_alerts: 3,
      yesterday_orders: 38, yesterday_income: 1120000, orders_trend: 'up', income_trend: 'up',
    }
  }
}

async function fetchTrends() {
  try {
    const res = await getTrends({ days: trendDays.value })
    renderTrendChart(res.data)
  } catch {
    const days = trendDays.value
    const dates = Array.from({ length: days }, (_, i) => {
      const d = new Date(); d.setDate(d.getDate() - days + i + 1)
      return `${d.getMonth() + 1}/${d.getDate()}`
    })
    renderTrendChart({
      dates,
      orders: dates.map(() => Math.floor(Math.random() * 50 + 20)),
      income: dates.map(() => Math.floor(Math.random() * 200000 + 80000)),
    })
  }
}

async function fetchRanking() {
  try {
    const res = await getSalesRanking({ sort_by: rankSort.value })
    rankingList.value = res.data
  } catch {
    rankingList.value = [
      { product_id: 1, product_name: '林间帐篷营位A', category: 'campsite', sales_count: 128, sales_amount: 3840000, cover_image: '' },
      { product_id: 2, product_name: '湖畔木屋B', category: 'campsite', sales_count: 96, sales_amount: 5760000, cover_image: '' },
      { product_id: 3, product_name: '亲子露营活动', category: 'activity', sales_count: 84, sales_amount: 2520000, cover_image: '' },
      { product_id: 4, product_name: '烧烤套餐', category: 'meal', sales_count: 72, sales_amount: 864000, cover_image: '' },
      { product_id: 5, product_name: '帐篷租赁(双人)', category: 'equipment_rental', sales_count: 56, sales_amount: 560000, cover_image: '' },
    ]
  }
}

async function fetchMemberStats() {
  try {
    const res = await getMemberStats()
    memberStats.value = res.data
  } catch {
    memberStats.value = {
      total_members: 1286, annual_members: 128, times_card_holders: 45, active_members: 380,
      new_today: 8, new_this_week: 42, new_this_month: 156,
    }
  }
}

async function fetchFinanceSummary() {
  try {
    const res = await getFinanceSummary()
    financeSummary.value = res.data
  } catch {
    financeSummary.value = {
      pending_amount: 2850000, withdrawable_amount: 18600000, deposit_amount: 3200000,
      month_income: 6800000, last_month_income: 5200000, mom_rate: 30.8, yoy_rate: 0,
    }
  }
}

async function fetchCategoryRevenue() {
  try {
    const res = await getCategoryRevenue()
    renderPieChart(res.data)
  } catch {
    renderPieChart([
      { category: 'campsite', category_name: '营位', revenue: 4200000, percentage: 45, order_count: 280 },
      { category: 'activity', category_name: '活动', revenue: 1800000, percentage: 20, order_count: 120 },
      { category: 'meal', category_name: '餐饮', revenue: 1200000, percentage: 13, order_count: 400 },
      { category: 'equipment_rental', category_name: '装备租赁', revenue: 800000, percentage: 9, order_count: 160 },
      { category: 'shop_item', category_name: '小商店', revenue: 600000, percentage: 7, order_count: 350 },
      { category: 'peripheral', category_name: '周边商品', revenue: 500000, percentage: 6, order_count: 85 },
    ])
  }
}

function renderTrendChart(data: { dates: string[]; orders: number[]; income: number[] }) {
  if (!trendChartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(20, 30, 26, 0.9)',
      borderColor: 'rgba(61, 139, 94, 0.3)',
      textStyle: { color: '#e0e8e4', fontSize: 12 },
    },
    legend: {
      data: ['订单数', '收入(元)'],
      textStyle: { color: '#6b6560', fontSize: 12 },
      right: 0,
    },
    grid: { left: 60, right: 60, bottom: 30, top: 48 },
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLine: { lineStyle: { color: '#e8e2dc' } },
      axisLabel: { color: '#a09890', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value', name: '订单', position: 'left',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f0ece6', type: 'dashed' } },
        axisLabel: { color: '#a09890', fontSize: 11 },
        nameTextStyle: { color: '#a09890', fontSize: 11 },
      },
      {
        type: 'value', name: '收入(元)', position: 'right',
        axisLine: { show: false },
        splitLine: { show: false },
        axisLabel: { color: '#a09890', fontSize: 11, formatter: (v: number) => (v / 100).toFixed(0) },
        nameTextStyle: { color: '#a09890', fontSize: 11 },
      },
    ],
    series: [
      {
        name: '订单数', type: 'line', data: data.orders, smooth: true,
        symbol: 'circle', symbolSize: 6,
        itemStyle: { color: '#3d8b5e' },
        lineStyle: { width: 2.5 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(61,139,94,0.15)' },
            { offset: 1, color: 'rgba(61,139,94,0.02)' },
          ]),
        },
      },
      {
        name: '收入(元)', type: 'bar', yAxisIndex: 1, data: data.income,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#c8a872' },
            { offset: 1, color: 'rgba(200,168,114,0.4)' },
          ]),
          borderRadius: [6, 6, 0, 0],
        },
        barWidth: 16,
      },
    ],
  })
}

function renderPieChart(data: CategoryRevenue[]) {
  if (!pieChartRef.value) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  const colors = ['#3d8b5e', '#52b67a', '#7ed4a0', '#c8a872', '#4a8ba8', '#6b8a9a']
  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: ¥{c} ({d}%)',
      backgroundColor: 'rgba(20, 30, 26, 0.9)',
      borderColor: 'rgba(61, 139, 94, 0.3)',
      textStyle: { color: '#e0e8e4', fontSize: 12 },
    },
    legend: {
      orient: 'vertical', right: 8, top: 'center',
      textStyle: { fontSize: 11, color: '#6b6560' },
      itemWidth: 10, itemHeight: 10,
      itemGap: 10,
    },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        scaleSize: 6,
        itemStyle: {
          shadowBlur: 20,
          shadowColor: 'rgba(61, 139, 94, 0.3)',
        },
      },
      data: data.map(item => ({
        name: item.category_name,
        value: item.revenue,
      })),
    }],
  })
}

let realtimeTimer: ReturnType<typeof setInterval>
let trendTimer: ReturnType<typeof setInterval>

onMounted(async () => {
  await Promise.all([fetchRealtime(), fetchTrends(), fetchRanking(), fetchMemberStats(), fetchFinanceSummary()])
  await nextTick()
  fetchCategoryRevenue()

  realtimeTimer = setInterval(fetchRealtime, 30000)
  trendTimer = setInterval(() => {
    fetchTrends()
    fetchRanking()
    fetchMemberStats()
    fetchFinanceSummary()
    fetchCategoryRevenue()
  }, 300000)

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  clearInterval(realtimeTimer)
  clearInterval(trendTimer)
  trendChart?.dispose()
  pieChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 24px;
}

// ==================== 页面标题 ====================
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  &__left {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  &__title {
    font-size: 22px;
    font-weight: 700;
    color: var(--color-text);
    letter-spacing: 1px;
    margin: 0;
  }

  &__date {
    font-size: 13px;
    color: var(--color-text-placeholder);
    letter-spacing: 0.5px;
  }
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(61, 139, 94, 0.08);
  border: 1px solid rgba(61, 139, 94, 0.15);

  &__dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #52b67a;
    animation: pulse 2s ease-in-out infinite;
  }

  &__text {
    font-size: 11px;
    color: var(--color-primary);
    font-weight: 600;
    letter-spacing: 1px;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(82, 182, 122, 0.4); }
  50% { opacity: 0.6; box-shadow: 0 0 0 4px rgba(82, 182, 122, 0); }
}

// ==================== 数据卡片 ====================
.stat-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--shadow-light);
  border: 1px solid var(--color-border-light);
  transition: var(--transition-base);

  &:hover {
    box-shadow: var(--shadow-base);
    transform: translateY(-2px);
  }

  &__icon-ring {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(var(--card-accent), 0.08), rgba(var(--card-accent), 0.04));
    color: var(--card-accent);
    flex-shrink: 0;
    background: linear-gradient(135deg, color-mix(in srgb, var(--card-accent) 12%, transparent), color-mix(in srgb, var(--card-accent) 5%, transparent));
    color: var(--card-accent);
  }

  &__body {
    flex: 1;
    min-width: 0;
  }

  &__label {
    font-size: 12px;
    color: var(--color-text-placeholder);
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  &__value {
    font-size: 26px;
    font-weight: 800;
    color: var(--color-text);
    letter-spacing: 0.5px;
    font-variant-numeric: tabular-nums;
  }

  &__trend {
    font-size: 11px;
    color: var(--color-text-placeholder);
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 2px;
  }
}

.trend--up { color: #52b67a !important; }
.trend--down { color: #c45c4a !important; }

// ==================== 卡片增强 ====================
.card-box {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  &__title {
    font-size: 15px;
    font-weight: 700;
    color: var(--color-text);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.5px;
  }

  &__title-bar {
    width: 3px;
    height: 14px;
    border-radius: 2px;
    background: linear-gradient(180deg, var(--color-primary), var(--color-accent));
  }
}

.chart-container {
  height: 300px;
}

// ==================== 排行榜 ====================
.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  gap: 12px;

  &__medal {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    color: var(--color-text-placeholder);
    background: var(--color-bg);
    flex-shrink: 0;

    &--gold { background: linear-gradient(135deg, #c8a872, #dbc49e); color: #fff; }
    &--silver { background: linear-gradient(135deg, #a0a0a0, #c0c0c0); color: #fff; }
    &--bronze { background: linear-gradient(135deg, #b87340, #d4956a); color: #fff; }
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name {
    font-size: 13px;
    color: var(--color-text-secondary);
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 6px;
  }

  &__bar {
    height: 4px;
    background: var(--color-bg);
    border-radius: 2px;
    overflow: hidden;
  }

  &__bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
    border-radius: 2px;
    transition: width 0.6s var(--ease-out-expo);
  }

  &__value {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
}

// ==================== 会员网格 ====================
.member-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.member-card {
  text-align: center;
  padding: 16px 12px;
  border-radius: var(--radius-small);
  background: var(--color-bg);
  transition: var(--transition-base);

  &__value {
    font-size: 22px;
    font-weight: 800;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }

  &__label {
    font-size: 11px;
    color: var(--color-text-placeholder);
    margin-top: 4px;
    letter-spacing: 0.5px;
  }

  &--primary .member-card__value { color: var(--color-primary); }
  &--accent .member-card__value { color: var(--color-accent); }
  &--blue .member-card__value { color: #4a8ba8; }
}

.member-new-row {
  display: flex;
  justify-content: space-around;
}

.member-new-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;

  &__value {
    font-size: 16px;
    font-weight: 700;
    color: var(--color-primary);
  }

  &__label {
    font-size: 11px;
    color: var(--color-text-placeholder);
    letter-spacing: 0.5px;
  }
}

// ==================== 财务 ====================
.finance-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.finance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;

  &__label {
    font-size: 13px;
    color: var(--color-text-placeholder);
  }

  &__value {
    font-size: 17px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
}

.finance-highlight {
  padding: 16px;
  border-radius: var(--radius-small);
  background: linear-gradient(135deg, rgba(61, 139, 94, 0.06), rgba(200, 168, 114, 0.04));
  border: 1px solid rgba(61, 139, 94, 0.08);

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  &__label {
    font-size: 13px;
    color: var(--color-text-secondary);
  }

  &__value {
    font-size: 24px;
    font-weight: 800;
    color: var(--color-primary);
    font-variant-numeric: tabular-nums;
  }
}
</style>
