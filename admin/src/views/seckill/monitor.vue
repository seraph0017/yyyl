<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>秒杀监控</h3>
        <div class="monitor-controls">
          <el-select v-model="selectedProductId" filterable placeholder="选择秒杀商品" style="width: 280px" @change="handleProductChange">
            <el-option v-for="p in productList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-tag v-if="polling" type="success" effect="dark" class="live-tag">
            <span class="live-dot" />LIVE
          </el-tag>
          <el-button v-if="selectedProductId" :type="polling ? 'danger' : 'success'" @click="togglePolling">
            {{ polling ? '停止监控' : '开始监控' }}
          </el-button>
        </div>
      </div>

      <template v-if="monitorData">
        <!-- 数据面板 -->
        <div class="monitor-grid">
          <div class="monitor-card">
            <div class="monitor-icon online">
              <el-icon size="28"><User /></el-icon>
            </div>
            <div class="monitor-info">
              <div class="monitor-label">在线等待人数</div>
              <div class="monitor-value">{{ monitorData.online_count }}</div>
            </div>
          </div>
          <div class="monitor-card">
            <div class="monitor-icon stock">
              <el-icon size="28"><Box /></el-icon>
            </div>
            <div class="monitor-info">
              <div class="monitor-label">剩余库存</div>
              <div class="monitor-value" :class="{ danger: monitorData.remaining_stock <= 5 }">
                {{ monitorData.remaining_stock }}
              </div>
            </div>
          </div>
          <div class="monitor-card">
            <div class="monitor-icon orders">
              <el-icon size="28"><Document /></el-icon>
            </div>
            <div class="monitor-info">
              <div class="monitor-label">已创建订单</div>
              <div class="monitor-value">{{ monitorData.orders_created }}</div>
            </div>
          </div>
          <div class="monitor-card">
            <div class="monitor-icon paid">
              <el-icon size="28"><CircleCheck /></el-icon>
            </div>
            <div class="monitor-info">
              <div class="monitor-label">已支付订单</div>
              <div class="monitor-value">{{ monitorData.orders_paid }}</div>
            </div>
          </div>
          <div class="monitor-card">
            <div class="monitor-icon qps">
              <el-icon size="28"><Odometer /></el-icon>
            </div>
            <div class="monitor-info">
              <div class="monitor-label">峰值 QPS</div>
              <div class="monitor-value">{{ monitorData.peak_qps }}</div>
            </div>
          </div>
        </div>

        <!-- 转化率 -->
        <div class="conversion-bar mt-16">
          <div class="conversion-item">
            <span class="conversion-label">下单转化率</span>
            <el-progress
              :percentage="conversionRate"
              :stroke-width="18"
              :format="(p: number) => p.toFixed(1) + '%'"
              style="flex: 1"
            />
          </div>
          <div class="conversion-item">
            <span class="conversion-label">支付转化率</span>
            <el-progress
              :percentage="payRate"
              :stroke-width="18"
              :color="'#67C23A'"
              :format="(p: number) => p.toFixed(1) + '%'"
              style="flex: 1"
            />
          </div>
        </div>

        <!-- 最后刷新时间 -->
        <div class="last-refresh mt-16">
          <span class="text-secondary">最近刷新：{{ lastRefreshTime }}</span>
          <span class="text-secondary">刷新间隔：5秒</span>
        </div>
      </template>

      <el-empty v-else-if="!selectedProductId" description="请选择一个秒杀商品开始监控" />
      <div v-else v-loading="loading" style="min-height: 200px" />
    </div>

    <!-- 秒杀复盘报告 -->
    <div v-if="selectedProductId" class="card-box mt-16">
      <div class="flex-between mb-16">
        <h3>秒杀复盘报告</h3>
        <el-button type="primary" plain @click="fetchReport">查看报告</el-button>
      </div>
      <div v-if="reportData" class="report-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="商品名称">{{ monitorData?.product_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="总访问人数">{{ (reportData as any).total_visitors ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="总创建订单">{{ (reportData as any).total_orders_created ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="总支付订单">{{ (reportData as any).total_orders_paid ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="总销售额">¥{{ formatPrice((reportData as any).total_revenue ?? 0) }}</el-descriptions-item>
          <el-descriptions-item label="售罄时间">{{ (reportData as any).sold_out_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="峰值并发">{{ (reportData as any).peak_concurrent ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="平均响应时间">{{ (reportData as any).avg_response_ms ?? '-' }} ms</el-descriptions-item>
        </el-descriptions>
      </div>
      <el-empty v-else description="点击上方按钮查看复盘报告" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Box, Document, CircleCheck, Odometer } from '@element-plus/icons-vue'
import { getSeckillMonitor, getSeckillReport } from '@/api/seckill'
import { get } from '@/utils/request'
import { formatPrice, formatDateTime } from '@/utils'
import type { SeckillMonitorData } from '@/types'

const loading = ref(false)
const polling = ref(false)
const selectedProductId = ref<number | null>(null)
const monitorData = ref<SeckillMonitorData | null>(null)
const reportData = ref<object | null>(null)
const lastRefreshTime = ref('')
let pollingTimer: ReturnType<typeof setInterval> | null = null

// 商品列表
const productList = ref<{ id: number; name: string }[]>([])
async function fetchProducts() {
  try {
    const res = await get<{ data: { list: { id: number; name: string }[] } }>('/admin/products', { page: 1, page_size: 200 })
    productList.value = res.data.list
  } catch { /* ignore */ }
}

// 转化率
const conversionRate = computed(() => {
  if (!monitorData.value || !monitorData.value.online_count) return 0
  return Math.min((monitorData.value.orders_created / monitorData.value.online_count) * 100, 100)
})

const payRate = computed(() => {
  if (!monitorData.value || !monitorData.value.orders_created) return 0
  return Math.min((monitorData.value.orders_paid / monitorData.value.orders_created) * 100, 100)
})

async function fetchMonitorData() {
  if (!selectedProductId.value) return
  loading.value = true
  try {
    const res = await getSeckillMonitor(selectedProductId.value)
    monitorData.value = res.data
    lastRefreshTime.value = formatDateTime(new Date())
  } catch {
    // 轮询时出错不中断
  } finally {
    loading.value = false
  }
}

function handleProductChange() {
  monitorData.value = null
  reportData.value = null
  stopPolling()
  if (selectedProductId.value) {
    fetchMonitorData()
  }
}

function togglePolling() {
  if (polling.value) {
    stopPolling()
  } else {
    startPolling()
  }
}

function startPolling() {
  polling.value = true
  fetchMonitorData()
  pollingTimer = setInterval(fetchMonitorData, 5000)
}

function stopPolling() {
  polling.value = false
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

async function fetchReport() {
  if (!selectedProductId.value) return
  try {
    const res = await getSeckillReport(selectedProductId.value)
    reportData.value = res.data
    ElMessage.success('报告加载成功')
  } catch {
    ElMessage.error('加载报告失败')
  }
}

onMounted(fetchProducts)

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.monitor-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-tag {
  animation: pulse 1.5s infinite;
  .live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #fff;
    border-radius: 50%;
    margin-right: 6px;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.monitor-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.monitor-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #ebeef5;

  .monitor-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    &.online { background: linear-gradient(135deg, #667eea, #764ba2); }
    &.stock { background: linear-gradient(135deg, #f093fb, #f5576c); }
    &.orders { background: linear-gradient(135deg, #4facfe, #00f2fe); }
    &.paid { background: linear-gradient(135deg, #43e97b, #38f9d7); }
    &.qps { background: linear-gradient(135deg, #fa709a, #fee140); }
  }

  .monitor-label {
    font-size: 13px;
    color: #909399;
    margin-bottom: 4px;
  }
  .monitor-value {
    font-size: 28px;
    font-weight: 700;
    color: #303133;
    &.danger { color: #F56C6C; }
  }
}

.conversion-bar {
  display: flex;
  gap: 32px;

  .conversion-item {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 12px;

    .conversion-label {
      font-size: 13px;
      color: #606266;
      white-space: nowrap;
    }
  }
}

.last-refresh {
  display: flex;
  justify-content: space-between;
}

.text-secondary { font-size: 12px; color: #909399; }
.mt-16 { margin-top: 16px; }

.report-content {
  :deep(.el-descriptions__label) {
    width: 120px;
  }
}

@media (max-width: 1400px) {
  .monitor-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
