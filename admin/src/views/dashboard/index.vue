<template>
  <div class="page-container dashboard">
    <!-- 实时数据卡片 -->
    <el-row :gutter="16" class="mb-20">
      <el-col :span="6" v-for="card in realtimeCards" :key="card.title">
        <div class="stat-card" :style="{ borderLeftColor: card.color }">
          <div class="stat-content">
            <div class="stat-label">{{ card.title }}</div>
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-change" :class="card.trend === 'up' ? 'up' : card.trend === 'down' ? 'down' : ''">
              <el-icon v-if="card.trend === 'up'"><Top /></el-icon>
              <el-icon v-else-if="card.trend === 'down'"><Bottom /></el-icon>
              <span>较昨日 {{ card.change }}</span>
            </div>
          </div>
          <el-icon class="stat-icon" :style="{ color: card.color }"><component :is="card.icon" /></el-icon>
        </div>
      </el-col>
    </el-row>

    <!-- 趋势图 + 销售排行 -->
    <el-row :gutter="16" class="mb-20">
      <el-col :span="16">
        <div class="card-box">
          <div class="flex-between mb-16">
            <h3 class="card-title">趋势概览</h3>
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
          <div class="flex-between mb-16">
            <h3 class="card-title">销售排行TOP5</h3>
            <el-radio-group v-model="rankSort" size="small" @change="fetchRanking">
              <el-radio-button value="sales_count">按销量</el-radio-button>
              <el-radio-button value="sales_amount">按金额</el-radio-button>
            </el-radio-group>
          </div>
          <div class="ranking-list">
            <div v-for="(item, idx) in rankingList.slice(0, 5)" :key="item.product_id" class="ranking-item">
              <span class="ranking-no" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
              <span class="ranking-name">{{ item.product_name }}</span>
              <span class="ranking-value">
                {{ rankSort === 'sales_count' ? item.sales_count + '单' : '¥' + formatPrice(item.sales_amount) }}
              </span>
            </div>
            <el-empty v-if="!rankingList.length" description="暂无数据" :image-size="60" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 品类收入 + 会员数据 + 财务概览 -->
    <el-row :gutter="16">
      <el-col :span="8">
        <div class="card-box">
          <h3 class="card-title mb-16">品类收入占比</h3>
          <div ref="pieChartRef" class="chart-container" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box">
          <h3 class="card-title mb-16">会员数据</h3>
          <div class="member-stats">
            <div class="member-stat-item">
              <div class="member-stat-value">{{ memberStats.total_members || 0 }}</div>
              <div class="member-stat-label">总会员</div>
            </div>
            <div class="member-stat-item">
              <div class="member-stat-value text-primary">{{ memberStats.annual_members || 0 }}</div>
              <div class="member-stat-label">年卡会员</div>
            </div>
            <div class="member-stat-item">
              <div class="member-stat-value" style="color: #FF9800;">{{ memberStats.times_card_holders || 0 }}</div>
              <div class="member-stat-label">次数卡用户</div>
            </div>
            <div class="member-stat-item">
              <div class="member-stat-value" style="color: #2196F3;">{{ memberStats.active_members || 0 }}</div>
              <div class="member-stat-label">活跃会员</div>
            </div>
          </div>
          <el-divider />
          <div class="member-new">
            <span>今日新增 <b>{{ memberStats.new_today || 0 }}</b></span>
            <span>本周新增 <b>{{ memberStats.new_this_week || 0 }}</b></span>
            <span>本月新增 <b>{{ memberStats.new_this_month || 0 }}</b></span>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box">
          <h3 class="card-title mb-16">财务概览</h3>
          <div class="finance-overview">
            <div class="finance-item">
              <div class="finance-label">待确认金额</div>
              <div class="finance-value text-warning">¥{{ formatPrice(financeSummary.pending_amount || 0) }}</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">可提现金额</div>
              <div class="finance-value text-success">¥{{ formatPrice(financeSummary.withdrawable_amount || 0) }}</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">押金专户</div>
              <div class="finance-value text-info">¥{{ formatPrice(financeSummary.deposit_amount || 0) }}</div>
            </div>
            <el-divider />
            <div class="finance-item">
              <div class="finance-label">本月收入</div>
              <div class="finance-value text-primary">¥{{ formatPrice(financeSummary.month_income || 0) }}</div>
            </div>
            <div class="finance-rate">
              <span>
                环比
                <el-tag :type="(financeSummary.mom_rate || 0) >= 0 ? 'success' : 'danger'" size="small">
                  {{ (financeSummary.mom_rate || 0) >= 0 ? '+' : '' }}{{ (financeSummary.mom_rate || 0).toFixed(1) }}%
                </el-tag>
              </span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { Top, Bottom, ShoppingCart, Money, UserFilled, WarningFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getRealtimeData, getTrends, getSalesRanking, getMemberStats, getFinanceSummary, getCategoryRevenue } from '@/api/dashboard'
import { formatPrice } from '@/utils'
import type { RealtimeData, SalesRankingItem, MemberStats, FinanceSummary, CategoryRevenue } from '@/types'

// 数据
const realtimeData = ref<Partial<RealtimeData>>({})
const trendDays = ref(7)
const rankSort = ref<'sales_count' | 'sales_amount'>('sales_count')
const rankingList = ref<SalesRankingItem[]>([])
const memberStats = ref<Partial<MemberStats>>({})
const financeSummary = ref<Partial<FinanceSummary>>({})

// 图表ref
const trendChartRef = ref<HTMLElement>()
const pieChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

// 实时数据卡片
const realtimeCards = computed(() => [
  {
    title: '今日订单',
    value: realtimeData.value.today_orders || 0,
    change: `${Math.abs((realtimeData.value.today_orders || 0) - (realtimeData.value.yesterday_orders || 0))}`,
    trend: realtimeData.value.orders_trend || 'flat',
    color: '#2E7D32',
    icon: ShoppingCart,
  },
  {
    title: '今日收入',
    value: '¥' + formatPrice(realtimeData.value.today_income || 0),
    change: `¥${formatPrice(Math.abs((realtimeData.value.today_income || 0) - (realtimeData.value.yesterday_income || 0)))}`,
    trend: realtimeData.value.income_trend || 'flat',
    color: '#FF9800',
    icon: Money,
  },
  {
    title: '当前在营人数',
    value: realtimeData.value.current_visitors || 0,
    change: '--',
    trend: 'flat',
    color: '#2196F3',
    icon: UserFilled,
  },
  {
    title: '库存告警',
    value: realtimeData.value.stock_alerts || 0,
    change: '低于阈值',
    trend: (realtimeData.value.stock_alerts || 0) > 0 ? 'up' : 'flat',
    color: '#F44336',
    icon: WarningFilled,
  },
])

// 获取数据
async function fetchRealtime() {
  try {
    const res = await getRealtimeData()
    realtimeData.value = res.data
  } catch {
    // 使用模拟数据
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
    // 模拟数据
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
    tooltip: { trigger: 'axis' },
    legend: { data: ['订单数', '收入(元)'] },
    grid: { left: 60, right: 60, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: data.dates },
    yAxis: [
      { type: 'value', name: '订单', position: 'left' },
      { type: 'value', name: '收入(元)', position: 'right', axisLabel: { formatter: (v: number) => (v / 100).toFixed(0) } },
    ],
    series: [
      { name: '订单数', type: 'line', data: data.orders, smooth: true, itemStyle: { color: '#2E7D32' }, areaStyle: { color: 'rgba(46,125,50,0.1)' } },
      { name: '收入(元)', type: 'bar', yAxisIndex: 1, data: data.income, itemStyle: { color: '#81C784', borderRadius: [4, 4, 0, 0] } },
    ],
  })
}

function renderPieChart(data: CategoryRevenue[]) {
  if (!pieChartRef.value) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  const colors = ['#2E7D32', '#4CAF50', '#81C784', '#FF9800', '#2196F3', '#9C27B0', '#F44336']
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { fontSize: 12 } },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      data: data.map(item => ({
        name: item.category_name,
        value: item.revenue,
      })),
    }],
  })
}

// 定时刷新
let realtimeTimer: ReturnType<typeof setInterval>
let trendTimer: ReturnType<typeof setInterval>

onMounted(async () => {
  await Promise.all([fetchRealtime(), fetchTrends(), fetchRanking(), fetchMemberStats(), fetchFinanceSummary()])
  await nextTick()
  fetchCategoryRevenue()

  // 实时数据30秒刷新
  realtimeTimer = setInterval(fetchRealtime, 30000)
  // 趋势5分钟刷新
  trendTimer = setInterval(() => {
    fetchTrends()
    fetchRanking()
    fetchMemberStats()
    fetchFinanceSummary()
    fetchCategoryRevenue()
  }, 300000)

  // 监听窗口大小变化
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
  padding: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-left: 4px solid;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s;

  &:hover { transform: translateY(-2px); }

  .stat-content {
    .stat-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
    .stat-value { font-size: 28px; font-weight: 700; color: #303133; margin-bottom: 4px; }
    .stat-change {
      font-size: 12px; color: #909399;
      &.up { color: #4CAF50; }
      &.down { color: #F44336; }
    }
  }

  .stat-icon { font-size: 40px; opacity: 0.15; }
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.chart-container {
  height: 300px;
}

.ranking-list {
  .ranking-item {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f5f5f5;

    &:last-child { border-bottom: none; }

    .ranking-no {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #f0f0f0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
      color: #909399;
      margin-right: 12px;

      &.top { background: #4CAF50; color: #fff; }
    }

    .ranking-name {
      flex: 1;
      font-size: 13px;
      color: #606266;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .ranking-value {
      font-size: 13px;
      font-weight: 600;
      color: #303133;
    }
  }
}

.member-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;

  .member-stat-item {
    text-align: center;
    .member-stat-value { font-size: 24px; font-weight: 700; }
    .member-stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
  }
}

.member-new {
  display: flex;
  justify-content: space-around;
  font-size: 13px;
  color: #606266;

  b { color: #2E7D32; }
}

.finance-overview {
  .finance-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;

    .finance-label { font-size: 13px; color: #909399; }
    .finance-value { font-size: 18px; font-weight: 600; }
  }

  .finance-rate {
    text-align: right;
    font-size: 13px;
    color: #909399;
  }
}
</style>
