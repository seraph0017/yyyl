<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>数据统计</h3>
        <el-button type="primary" @click="handleExport"><el-icon><Download /></el-icon>导出报表</el-button>
      </div>

      <!-- 筛选 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item label="报表类型">
          <el-select v-model="reportType" @change="fetchReport">
            <el-option label="销售报表" value="sales" />
            <el-option label="用户分析" value="users" />
            <el-option label="商品排行" value="products" />
            <el-option label="页面浏览" value="page_views" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间粒度" v-if="reportType === 'sales'">
          <el-select v-model="params.granularity" @change="fetchReport">
            <el-option label="按日" value="day" />
            <el-option label="按周" value="week" />
            <el-option label="按月" value="month" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" @change="handleDateChange" />
        </el-form-item>
      </el-form>

      <!-- 销售报表 -->
      <template v-if="reportType === 'sales'">
        <el-row :gutter="16" class="mb-20">
          <el-col :span="6" v-for="stat in salesSummary" :key="stat.label">
            <div class="stat-mini">
              <div class="stat-mini-label">{{ stat.label }}</div>
              <div class="stat-mini-value">{{ stat.value }}</div>
            </div>
          </el-col>
        </el-row>
        <div ref="salesChartRef" style="height: 400px;" />
      </template>

      <!-- 用户分析 -->
      <template v-if="reportType === 'users'">
        <div ref="userChartRef" style="height: 400px;" />
      </template>

      <!-- 商品排行 -->
      <template v-if="reportType === 'products'">
        <div ref="productChartRef" style="height: 400px;" />
      </template>

      <!-- 页面浏览 -->
      <template v-if="reportType === 'page_views'">
        <el-row :gutter="16" class="mb-20">
          <el-col :span="8" v-for="stat in pageViewSummary" :key="stat.label">
            <div class="stat-mini">
              <div class="stat-mini-label">{{ stat.label }}</div>
              <div class="stat-mini-value">{{ stat.value }}</div>
            </div>
          </el-col>
        </el-row>
        <el-table :data="pageViewList" stripe>
          <el-table-column prop="stat_date" label="日期" width="120" />
          <el-table-column prop="page_title" label="页面标题" min-width="160">
            <template #default="{ row }">{{ row.page_title || row.page_key }}</template>
          </el-table-column>
          <el-table-column prop="page_key" label="页面标识" min-width="180" />
          <el-table-column prop="view_count" label="PV" width="100" align="right" />
          <el-table-column prop="user_count" label="登录访问" width="110" align="right" />
          <el-table-column label="最近访问" width="170">
            <template #default="{ row }">{{ row.last_viewed_at ? formatDateTime(row.last_viewed_at) : '-' }}</template>
          </el-table-column>
        </el-table>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { getSalesReport, exportReport, getPageViewStats, type PageViewStatItem } from '@/api/system'
import { formatPrice, downloadFile, formatDateTime } from '@/utils'

const reportType = ref('sales')
const dateRange = ref<[string, string]>([
  dayjs().subtract(30, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD'),
])
const params = reactive({ granularity: 'day' as 'day' | 'week' | 'month' })

const salesChartRef = ref<HTMLElement>()
const userChartRef = ref<HTMLElement>()
const productChartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const salesSummary = ref([
  { label: '总订单数', value: '0' },
  { label: '总收入', value: '¥0' },
  { label: '客单价', value: '¥0' },
  { label: '退款金额', value: '¥0' },
])
const pageViewList = ref<PageViewStatItem[]>([])
const pageViewSummary = ref([
  { label: '总浏览量', value: '0' },
  { label: '登录访问', value: '0' },
  { label: '页面/日期数', value: '0' },
])

async function fetchReport() {
  await nextTick()
  try {
    if (reportType.value === 'sales') {
      const res = await getSalesReport({
        granularity: params.granularity,
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
      })
      const data = res.data
      salesSummary.value = [
        { label: '总订单数', value: String(data.summary.total_orders) },
        { label: '总收入', value: '¥' + formatPrice(data.summary.total_income) },
        { label: '客单价', value: '¥' + formatPrice(data.summary.avg_order_amount) },
        { label: '退款金额', value: '¥' + formatPrice(data.summary.refund_amount) },
      ]
      renderSalesChart(data.details)
    } else if (reportType.value === 'page_views') {
      const res = await getPageViewStats({
        start_date: dateRange.value[0],
        end_date: dateRange.value[1],
        page: 1,
        page_size: 100,
      })
      pageViewList.value = res.data.list
      const summary = res.data.summary
      pageViewSummary.value = [
        { label: '总浏览量', value: String(summary.view_count) },
        { label: '登录访问', value: String(summary.user_count) },
        { label: '页面/日期数', value: String(summary.record_count) },
      ]
    }
  } catch {
    // 模拟渲染
    if (reportType.value === 'sales' && salesChartRef.value) {
      renderSalesChart([])
    }
  }
}

function renderSalesChart(details: any[]) {
  if (!salesChartRef.value) return
  chartInstance?.dispose()
  chartInstance = echarts.init(salesChartRef.value)
  const dates = details.map(d => d.date)
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['订单数', '收入', '退款'] },
    grid: { left: 60, right: 60, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '订单' },
      { type: 'value', name: '金额(元)' },
    ],
    series: [
      { name: '订单数', type: 'bar', data: details.map(d => d.orders), itemStyle: { color: '#3d8b5e', borderRadius: [4,4,0,0] } },
      { name: '收入', type: 'line', yAxisIndex: 1, data: details.map(d => d.income / 100), smooth: true, itemStyle: { color: '#2d4a3e' } },
      { name: '退款', type: 'line', yAxisIndex: 1, data: details.map(d => (d.refund || 0) / 100), smooth: true, itemStyle: { color: '#c45c4a' }, lineStyle: { type: 'dashed' } },
    ],
  })
}

async function handleExport() {
  try {
    const res = await exportReport({
      type: reportType.value,
      params: { start_date: dateRange.value[0], end_date: dateRange.value[1], granularity: params.granularity },
    })
    downloadFile(res.data, `${reportType.value}_report_${dayjs().format('YYYYMMDD')}.xlsx`)
    ElMessage.success('导出成功')
  } catch { ElMessage.info('导出功能需要后端支持') }
}

function handleDateChange() { fetchReport() }

onMounted(fetchReport)
onUnmounted(() => { chartInstance?.dispose() })
</script>

<style lang="scss" scoped>
.stat-mini {
  background: var(--color-bg-warm); border-radius: var(--radius-base); padding: 20px; text-align: center;
  border: 1px solid var(--color-border-light); transition: var(--transition-base);
  &:hover { box-shadow: var(--shadow-light); }
  .stat-mini-label { font-size: 13px; color: var(--color-text-placeholder); margin-bottom: 6px; letter-spacing: 0.5px; }
  .stat-mini-value { font-size: 24px; font-weight: 800; color: var(--color-text); }
}
</style>
