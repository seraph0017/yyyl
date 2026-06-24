<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>订单管理</h3>
        <div>
          <el-button type="primary" @click="showExportDialog = true">
            <el-icon><Download /></el-icon>导出
          </el-button>
          <el-button @click="showExportTaskDrawer = true">导出任务</el-button>
        </div>
      </div>

      <!-- 搜索/筛选 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-input v-model="searchParams.keyword" placeholder="订单号/用户/手机号/商品名" clearable style="width: 240px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.status" placeholder="订单状态" clearable @change="handleSearch">
            <el-option v-for="(v, k) in orderStatusMap" :key="k" :label="v.label" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.payment_status" placeholder="支付状态" clearable style="width: 130px" @change="handleSearch">
            <el-option v-for="(v, k) in paymentStatusMap" :key="k" :label="v.label" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input-number v-model="searchParams.product_id" placeholder="商品ID" :min="1" controls-position="right" style="width: 130px" @change="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.product_type" placeholder="品类" clearable style="width: 150px" @change="handleSearch">
            <el-option v-for="(label, key) in productTypeMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="handleDateChange" />
        </el-form-item>
        <el-form-item>
          <el-date-picker v-model="bookingDateRange" type="daterange" range-separator="至" start-placeholder="预定开始" end-placeholder="预定结束" value-format="YYYY-MM-DD" @change="handleBookingDateChange" />
        </el-form-item>
        <el-form-item>
          <el-date-picker v-model="paymentTimeRange" type="datetimerange" range-separator="至" start-placeholder="支付开始" end-placeholder="支付结束" value-format="YYYY-MM-DDTHH:mm:ssZ" @change="handlePaymentTimeChange" />
        </el-form-item>
        <el-form-item>
          <el-input-number v-model="searchParams.amount_min" placeholder="最小金额" :min="0" controls-position="right" style="width: 130px" @change="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-input-number v-model="searchParams.amount_max" placeholder="最大金额" :min="0" controls-position="right" style="width: 130px" @change="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.verify_status" placeholder="核销状态" clearable style="width: 130px" @change="handleSearch">
            <el-option label="待核销" value="pending" />
            <el-option label="已核销" value="verified" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input v-model="searchParams.source_channel" placeholder="二维码渠道" clearable style="width: 150px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch"><el-icon><Search /></el-icon>搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 订单表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="order_no" label="订单号" width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="router.push(`/orders/${row.id}`)">{{ row.order_no }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="用户" width="150">
          <template #default="{ row }">
            <div>{{ row.user_nickname }}</div>
            <div class="text-secondary">{{ row.user_phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单金额" width="120" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ formatPrice(row.total_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="item_count" label="商品数" width="80" align="center" />
        <el-table-column label="订单状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="(orderStatusMap[row.status]?.type as any) || 'info'" size="small">
              {{ orderStatusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="(paymentStatusMap[row.payment_status]?.type as any) || 'info'" size="small">
              {{ paymentStatusMap[row.payment_status]?.label || row.payment_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="详情" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--view" circle size="small" @click="router.push(`/orders/${row.id}`)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip v-if="row.status === 'refunding'" content="审批退款" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--reject" circle size="small" @click="handleRefund(row)">
                  <el-icon><RefreshLeft /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="searchParams.page"
          v-model:page-size="searchParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>

    <el-dialog v-model="showExportDialog" title="导出订单" width="460px">
      <el-form label-width="100px">
        <el-form-item label="文件格式">
          <el-radio-group v-model="exportForm.file_format">
            <el-radio-button label="csv">CSV</el-radio-button>
            <el-radio-button label="xlsx">XLSX</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="敏感字段">
          <el-switch
            v-model="exportForm.include_sensitive"
            active-text="包含"
            inactive-text="不包含"
          />
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false" title="导出将使用当前筛选条件，生成后的文件在导出任务中下载。" />
      <template #footer>
        <el-button @click="showExportDialog = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="handleExport">提交导出</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="showExportTaskDrawer" title="导出任务" size="520px" @open="fetchExportTasks">
      <el-table :data="exportTaskList" v-loading="exportTaskLoading" stripe>
        <el-table-column prop="task_no" label="任务号" min-width="150" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="row_count" label="行数" width="80" align="right" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :disabled="row.status !== 'completed'" @click="handleDownloadTask(row)">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="text-secondary export-total">共 {{ exportTaskTotal }} 个任务</div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, View, RefreshLeft, Download } from '@element-plus/icons-vue'
import { getOrders, approveRefund, createOrderExport, getOrderExportTasks, downloadOrderExportTask } from '@/api/order'
import { formatPrice, formatDateTime, orderStatusMap, paymentStatusMap } from '@/utils'
import type { Order, OrderSearchParams } from '@/types'
import type { OrderExportTask } from '@/types/order-export'
import { downloadFile } from '@/utils'

const router = useRouter()
const loading = ref(false)
const tableData = ref<Order[]>([])
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)
const bookingDateRange = ref<[string, string] | null>(null)
const paymentTimeRange = ref<[string, string] | null>(null)
const productTypeMap: Record<string, string> = {
  daily_camping: '日常露营',
  event_camping: '活动露营',
  rental: '装备租赁',
  daily_activity: '日常活动',
  special_activity: '特定活动',
  shop: '小商店',
  merchandise: '周边商品',
}

const searchParams = reactive<OrderSearchParams>({
  page: 1,
  page_size: 20,
  keyword: '',
  status: undefined,
  payment_status: undefined,
  start_date: undefined,
  end_date: undefined,
  product_id: undefined,
  product_type: undefined,
  booking_date_start: undefined,
  booking_date_end: undefined,
  payment_time_start: undefined,
  payment_time_end: undefined,
  amount_min: undefined,
  amount_max: undefined,
  verify_status: undefined,
  source_channel: undefined,
})
const exportTaskList = ref<OrderExportTask[]>([])
const exportTaskTotal = ref(0)
const exportTaskLoading = ref(false)
const showExportDialog = ref(false)
const showExportTaskDrawer = ref(false)
const exporting = ref(false)
const exportForm = reactive({
  file_format: 'csv' as 'csv' | 'xlsx',
  include_sensitive: false,
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getOrders(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function fetchExportTasks() {
  exportTaskLoading.value = true
  try {
    const res = await getOrderExportTasks({ page: 1, page_size: 20 })
    exportTaskList.value = res.data.list
    exportTaskTotal.value = res.data.pagination.total
  } finally {
    exportTaskLoading.value = false
  }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function handleReset() {
  searchParams.keyword = ''
  searchParams.status = undefined
  searchParams.payment_status = undefined
  searchParams.start_date = undefined
  searchParams.end_date = undefined
  searchParams.product_id = undefined
  searchParams.product_type = undefined
  searchParams.booking_date_start = undefined
  searchParams.booking_date_end = undefined
  searchParams.payment_time_start = undefined
  searchParams.payment_time_end = undefined
  searchParams.amount_min = undefined
  searchParams.amount_max = undefined
  searchParams.verify_status = undefined
  searchParams.source_channel = undefined
  dateRange.value = null
  bookingDateRange.value = null
  paymentTimeRange.value = null
  handleSearch()
}

async function handleExport() {
  exporting.value = true
  try {
    await createOrderExport({
      filters: { ...searchParams },
      file_format: exportForm.file_format,
      include_sensitive: exportForm.include_sensitive,
    })
    ElMessage.success('导出任务已提交')
    showExportDialog.value = false
    showExportTaskDrawer.value = true
    fetchExportTasks()
  } finally {
    exporting.value = false
  }
}

async function handleDownloadTask(task: OrderExportTask) {
  const res = await downloadOrderExportTask(task.id)
  downloadFile(res.data as Blob, `${task.task_no}.${task.file_format}`)
}

function handleDateChange(val: [string, string] | null) {
  if (val) {
    searchParams.start_date = val[0]
    searchParams.end_date = val[1]
  } else {
    searchParams.start_date = undefined
    searchParams.end_date = undefined
  }
  handleSearch()
}

function handleBookingDateChange(val: [string, string] | null) {
  if (val) {
    searchParams.booking_date_start = val[0]
    searchParams.booking_date_end = val[1]
  } else {
    searchParams.booking_date_start = undefined
    searchParams.booking_date_end = undefined
  }
  handleSearch()
}

function handlePaymentTimeChange(val: [string, string] | null) {
  if (val) {
    searchParams.payment_time_start = val[0]
    searchParams.payment_time_end = val[1]
  } else {
    searchParams.payment_time_start = undefined
    searchParams.payment_time_end = undefined
  }
  handleSearch()
}

async function handleRefund(row: Order) {
  try {
    await ElMessageBox.confirm(`确认审批订单 ${row.order_no} 的退款申请？金额: ¥${formatPrice(row.total_amount)}`, '退款审批', {
      confirmButtonText: '同意退款',
      cancelButtonText: '拒绝',
      distinguishCancelAndClose: true,
      type: 'warning',
    })
    await approveRefund(row.id, { approved: true })
    ElMessage.success('退款已批准')
    fetchData()
  } catch (action: any) {
    if (action === 'cancel') {
      const reason = await ElMessageBox.prompt('请输入拒绝理由', '拒绝退款', {
        confirmButtonText: '确认拒绝',
        cancelButtonText: '取消',
      })
      await approveRefund(row.id, { approved: false, reason: reason.value })
      ElMessage.success('已拒绝退款')
      fetchData()
    }
  }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.text-secondary { font-size: 12px; color: var(--color-text-placeholder); }
.price { font-weight: 700; color: var(--color-accent); letter-spacing: 0.5px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
</style>
