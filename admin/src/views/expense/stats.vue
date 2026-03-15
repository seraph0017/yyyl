<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>报销统计</h3>
        <el-button @click="router.push('/expenses')">
          <el-icon><Back /></el-icon>返回报销列表
        </el-button>
      </div>

      <!-- 筛选 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="monthrange"
            range-separator="至"
            start-placeholder="开始月份"
            end-placeholder="结束月份"
            value-format="YYYY-MM"
            @change="fetchStats"
          />
        </el-form-item>
      </el-form>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 月度趋势折线图 -->
        <div class="chart-card">
          <h4>月度报销趋势</h4>
          <div ref="trendChartRef" class="chart-container" />
        </div>

        <!-- 按类型统计饼图 -->
        <div class="chart-card">
          <h4>按类型分布</h4>
          <div ref="typeChartRef" class="chart-container" />
        </div>

        <!-- 按员工统计柱状图 -->
        <div class="chart-card full-width">
          <h4>按员工统计</h4>
          <div ref="staffChartRef" class="chart-container" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Back } from '@element-plus/icons-vue'
import { getExpenseStats } from '@/api/expense'
import * as echarts from 'echarts'
import type { ExpenseStats } from '@/types'

const router = useRouter()
const dateRange = ref<[string, string] | null>(null)

const trendChartRef = ref<HTMLElement>()
const typeChartRef = ref<HTMLElement>()
const staffChartRef = ref<HTMLElement>()

let trendChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null
let staffChart: echarts.ECharts | null = null

async function fetchStats() {
  try {
    const params: Record<string, string | number> = {}
    if (dateRange.value) {
      // 后端接受 year 和 month 参数
      const [startYear, startMonth] = dateRange.value[0].split('-')
      params.year = parseInt(startYear)
      params.month = parseInt(startMonth)
    }
    const res = await getExpenseStats(params)
    renderCharts(res.data)
  } catch { /* ignore */ }
}

function renderCharts(stats: ExpenseStats) {
  // 月度趋势折线图
  if (trendChart) {
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: stats.type_breakdown.map(i => i.expense_type_name),
      },
      yAxis: { type: 'value', name: '金额(元)' },
      series: [{
        name: '报销金额',
        type: 'line',
        smooth: true,
        data: stats.type_breakdown.map(i => (i.total_amount / 100).toFixed(2)),
        areaStyle: { color: 'rgba(64, 158, 255, 0.15)' },
        lineStyle: { color: '#409EFF' },
        itemStyle: { color: '#409EFF' },
      }],
      grid: { left: 60, right: 20, top: 30, bottom: 30 },
    })
  }

  // 按类型饼图
  if (typeChart) {
    typeChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        label: { formatter: '{b}\n{d}%' },
        data: stats.type_breakdown.map(i => ({
          name: i.expense_type_name,
          value: (i.total_amount / 100).toFixed(2),
        })),
      }],
    })
  }

  // 按员工柱状图
  if (staffChart) {
    staffChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: stats.staff_breakdown.map(i => i.staff_name),
        axisLabel: { rotate: 30 },
      },
      yAxis: { type: 'value', name: '金额(元)' },
      series: [
        {
          name: '报销金额',
          type: 'bar',
          data: stats.staff_breakdown.map(i => (i.total_amount / 100).toFixed(2)),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#67C23A' },
              { offset: 1, color: '#95d475' },
            ]),
          },
          barMaxWidth: 40,
        },
        {
          name: '报销笔数',
          type: 'bar',
          data: stats.staff_breakdown.map(i => i.count),
          itemStyle: { color: '#E6A23C' },
          barMaxWidth: 40,
        },
      ],
      legend: { data: ['报销金额', '报销笔数'], top: 0 },
      grid: { left: 60, right: 20, top: 40, bottom: 50 },
    })
  }
}

function initCharts() {
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
  }
  if (typeChartRef.value) {
    typeChart = echarts.init(typeChartRef.value)
  }
  if (staffChartRef.value) {
    staffChart = echarts.init(staffChartRef.value)
  }
}

function handleResize() {
  trendChart?.resize()
  typeChart?.resize()
  staffChart?.resize()
}

onMounted(async () => {
  await nextTick()
  initCharts()
  fetchStats()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  typeChart?.dispose()
  staffChart?.dispose()
})
</script>

<style lang="scss" scoped>
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #ebeef5;

  &.full-width {
    grid-column: 1 / -1;
  }

  h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    color: #606266;
  }
}

.chart-container {
  height: 320px;
  width: 100%;
}
</style>
