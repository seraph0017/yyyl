<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>订单管理</h3>
        <div>
          <el-button type="success" @click="openTemporaryOrderDialog">
            现场收款
          </el-button>
          <el-button type="warning" @click="showRefundQueueDrawer = true">
            <el-icon><RefreshLeft /></el-icon>退款队列
          </el-button>
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
            <div>{{ getOrderUserDisplay(row) }}</div>
            <div class="text-secondary">{{ getOrderPhoneDisplay(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单金额" width="120" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ formatYuanAmount(row.total_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="商品数" width="80" align="center">
          <template #default="{ row }">{{ getOrderItemCount(row) }}</template>
        </el-table-column>
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

    <el-dialog v-model="showTemporaryOrderDialog" title="现场收款" :width="temporaryDialogWidth" @closed="resetTemporaryOrderResult">
      <el-form label-width="104px">
        <el-form-item label="收款方式">
          <el-segmented
            v-model="temporaryOrderForm.payment_flow"
            :options="[
              { label: '顾客扫码', value: 'customer_scan_qr' },
              { label: '扫付款码', value: 'merchant_scan_code' },
            ]"
          />
        </el-form-item>
        <el-form-item label="临时单类型">
          <el-radio-group v-model="temporaryOrderForm.mode">
            <el-radio-button label="custom_amount">自定义金额</el-radio-button>
            <el-radio-button label="product">商品临时单</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="temporaryOrderForm.mode === 'product'">
          <el-form-item label="商品ID">
            <el-input-number v-model="temporaryOrderForm.product_id" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="SKU ID">
            <el-input-number v-model="temporaryOrderForm.sku_id" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="数量">
            <el-input-number v-model="temporaryOrderForm.quantity" :min="1" :max="999" controls-position="right" />
          </el-form-item>
          <el-form-item label="预约日期">
            <el-date-picker v-model="temporaryOrderForm.booking_date" type="date" value-format="YYYY-MM-DD" placeholder="营位商品必填" />
          </el-form-item>
          <el-form-item label="场次">
            <el-input v-model="temporaryOrderForm.time_slot" maxlength="20" clearable />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="收款项">
            <el-input v-model="temporaryOrderForm.item_name" maxlength="80" placeholder="如 现场补差价" clearable />
          </el-form-item>
          <el-form-item label="金额">
            <el-input-number v-model="temporaryOrderForm.amount" :min="0.01" :precision="2" controls-position="right" />
          </el-form-item>
        </template>

        <el-form-item v-if="temporaryOrderForm.payment_flow === 'merchant_scan_code'" label="付款码">
          <el-input v-model="temporaryOrderForm.auth_code" maxlength="128" placeholder="扫描或输入用户付款码 auth_code" clearable />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="temporaryOrderForm.remark" type="textarea" :rows="3" maxlength="200" show-word-limit placeholder="现场收款原因、商品说明或顾客信息" />
        </el-form-item>
      </el-form>

      <div v-if="temporarySession" class="temporary-result">
        <el-alert
          v-if="temporarySession.miniapp_path"
          type="success"
          :closable="false"
          title="临时收款码"
          description="将下方路径生成小程序码或复制给现场员工展示，顾客扫码后会生成正式订单并继续支付。"
        />
        <el-alert
          v-else
          type="info"
          :closable="false"
          title="付款码收款已提交"
          :description="temporaryCodePayDescription"
        />
        <el-descriptions :column="1" size="small" border class="temporary-result__detail">
          <el-descriptions-item label="会话号">{{ temporarySession.session_no }}</el-descriptions-item>
          <el-descriptions-item v-if="temporarySession.qrcode_image_url" label="小程序码">
            <el-image
              v-if="!temporaryQrcodeLoadFailed"
              class="temporary-result__qrcode"
              :src="temporarySession.qrcode_image_url"
              fit="contain"
              :preview-src-list="[temporarySession.qrcode_image_url]"
              @error="handleTemporaryQrcodeError"
            />
            <div v-else class="temporary-result__qrcode temporary-result__qrcode--error">
              <span>小程序码加载失败</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item v-if="temporarySession.miniapp_path" label="miniapp_path">
            <el-input :model-value="temporarySession.miniapp_path" readonly />
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ temporarySession.status }}</el-descriptions-item>
          <el-descriptions-item v-if="temporarySession.order_id" label="订单ID">{{ temporarySession.order_id }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="temporaryResultRequiresQuery" class="temporary-result__actions">
          <el-button type="primary" :loading="temporaryCodePayQuerying" @click="handleTemporaryCodePayQuery">
            查询付款结果
          </el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="showTemporaryOrderDialog = false">关闭</el-button>
        <el-button @click="resetTemporaryOrderForm">重置</el-button>
        <el-button type="primary" :loading="temporaryOrderSubmitting" @click="handleTemporaryOrderSubmit">
          创建
        </el-button>
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

    <el-drawer v-model="showRefundQueueDrawer" title="退款审批队列" size="min(720px, 92vw)" @open="fetchRefundQueue">
      <el-table :data="refundQueueList" v-loading="refundQueueLoading" stripe>
        <el-table-column prop="refund_no" label="退款单号" min-width="170" />
        <el-table-column prop="order_id" label="订单ID" width="90" />
        <el-table-column label="模式" width="90" align="center">
          <template #default="{ row }">{{ getRefundModeLabel(row.refund_mode) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="110" align="right">
          <template #default="{ row }">¥{{ formatYuanAmount(row.refund_amount) }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleApproveRefundRecord(row)">通过</el-button>
            <el-button link type="danger" @click="handleRejectRefundRecord(row)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="refundQueuePage"
          v-model:page-size="refundQueuePageSize"
          :total="refundQueueTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchRefundQueue"
          @size-change="fetchRefundQueue"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, View, RefreshLeft, Download } from '@element-plus/icons-vue'
import { getOrders, createOrderExport, getOrderExportTasks, downloadOrderExportTask, createTemporaryOrder, queryTemporaryCodePay, getRefundQueue, approveRefundRecord, rejectRefundRecord } from '@/api/order'
import { formatDateTime, orderStatusMap, paymentStatusMap } from '@/utils'
import type {
  Order,
  OrderSearchParams,
  TemporaryOrderCodePayResult,
  TemporaryOrderCreatePayload,
  TemporaryOrderCreateResult,
  TemporaryOrderSession,
  RefundRecord,
} from '@/types'
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
const refundQueueList = ref<RefundRecord[]>([])
const refundQueueTotal = ref(0)
const refundQueueLoading = ref(false)
const refundQueuePage = ref(1)
const refundQueuePageSize = ref(20)
const showExportDialog = ref(false)
const showExportTaskDrawer = ref(false)
const showTemporaryOrderDialog = ref(false)
const showRefundQueueDrawer = ref(false)
const exporting = ref(false)
const temporaryOrderSubmitting = ref(false)
const temporaryCodePayQuerying = ref(false)
const temporaryOrderResult = ref<TemporaryOrderCreateResult | null>(null)
const temporaryQrcodeLoadFailed = ref(false)
const temporaryDialogWidth = 'min(620px, calc(100vw - 32px))'
const exportForm = reactive({
  file_format: 'csv' as 'csv' | 'xlsx',
  include_sensitive: false,
})
const temporaryOrderForm = reactive({
  payment_flow: 'customer_scan_qr' as 'customer_scan_qr' | 'merchant_scan_code',
  mode: 'custom_amount' as 'custom_amount' | 'product',
  product_id: undefined as number | undefined,
  sku_id: undefined as number | undefined,
  quantity: 1,
  booking_date: '',
  time_slot: '',
  item_name: '',
  amount: undefined as number | undefined,
  remark: '',
  auth_code: '',
  device_id: 'admin-onsite-counter',
})

const temporarySession = computed<TemporaryOrderSession | null>(() => {
  if (!temporaryOrderResult.value) return null
  if (isTemporaryCodePayResult(temporaryOrderResult.value)) return temporaryOrderResult.value.session
  return temporaryOrderResult.value
})

const temporaryCodePayDescription = computed(() => {
  if (!temporaryOrderResult.value || !isTemporaryCodePayResult(temporaryOrderResult.value)) return ''
  const state = temporaryOrderResult.value.trade_state || '处理中'
  const transaction = temporaryOrderResult.value.transaction_id ? `，微信单号 ${temporaryOrderResult.value.transaction_id}` : ''
  return `当前交易状态：${state}${transaction}`
})

const temporaryResultRequiresQuery = computed(() => {
  return Boolean(
    temporaryOrderResult.value
    && isTemporaryCodePayResult(temporaryOrderResult.value)
    && temporaryOrderResult.value.requires_query
    && temporarySession.value?.id,
  )
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

async function fetchRefundQueue() {
  refundQueueLoading.value = true
  try {
    const res = await getRefundQueue({ page: refundQueuePage.value, page_size: refundQueuePageSize.value })
    refundQueueList.value = res.data.list
    refundQueueTotal.value = res.data.pagination.total
  } finally {
    refundQueueLoading.value = false
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

function openTemporaryOrderDialog() {
  showTemporaryOrderDialog.value = true
}

function resetTemporaryOrderResult() {
  temporaryOrderResult.value = null
  temporaryQrcodeLoadFailed.value = false
}

function resetTemporaryOrderForm() {
  temporaryOrderForm.payment_flow = 'customer_scan_qr'
  temporaryOrderForm.mode = 'custom_amount'
  temporaryOrderForm.product_id = undefined
  temporaryOrderForm.sku_id = undefined
  temporaryOrderForm.quantity = 1
  temporaryOrderForm.booking_date = ''
  temporaryOrderForm.time_slot = ''
  temporaryOrderForm.item_name = ''
  temporaryOrderForm.amount = undefined
  temporaryOrderForm.remark = ''
  temporaryOrderForm.auth_code = ''
  temporaryOrderResult.value = null
  temporaryQrcodeLoadFailed.value = false
}

function isTemporaryCodePayResult(result: TemporaryOrderCreateResult): result is TemporaryOrderCodePayResult {
  return Boolean((result as TemporaryOrderCodePayResult).session && (result as TemporaryOrderCodePayResult).order)
}

function buildTemporaryOrderPayload(): TemporaryOrderCreatePayload {
  const payload: TemporaryOrderCreatePayload = {
    payment_flow: temporaryOrderForm.payment_flow,
    mode: temporaryOrderForm.mode,
    quantity: temporaryOrderForm.quantity,
    remark: temporaryOrderForm.remark.trim(),
  }
  if (temporaryOrderForm.mode === 'product') {
    if (!temporaryOrderForm.product_id) throw new Error('请选择商品ID')
    payload.product_id = temporaryOrderForm.product_id
    if (temporaryOrderForm.sku_id) payload.sku_id = temporaryOrderForm.sku_id
    if (temporaryOrderForm.booking_date) payload.booking_date = temporaryOrderForm.booking_date
    if (temporaryOrderForm.time_slot.trim()) payload.time_slot = temporaryOrderForm.time_slot.trim()
  } else {
    if (!temporaryOrderForm.item_name.trim()) throw new Error('请填写收款项')
    if (!temporaryOrderForm.amount || temporaryOrderForm.amount <= 0) throw new Error('请填写收款金额')
    if (!temporaryOrderForm.remark.trim()) throw new Error('请填写现场收款备注')
    payload.item_name = temporaryOrderForm.item_name.trim()
    payload.amount = temporaryOrderForm.amount
  }
  if (temporaryOrderForm.payment_flow === 'merchant_scan_code') {
    if (!temporaryOrderForm.auth_code.trim()) throw new Error('请扫描或输入用户付款码')
    payload.auth_code = temporaryOrderForm.auth_code.trim()
    payload.device_id = temporaryOrderForm.device_id
  }
  return payload
}

async function handleTemporaryOrderSubmit() {
  temporaryOrderSubmitting.value = true
  try {
    const payload = buildTemporaryOrderPayload()
    const res = await createTemporaryOrder(payload)
    temporaryOrderResult.value = res.data
    temporaryQrcodeLoadFailed.value = false
    if (isTemporaryCodePayResult(res.data)) {
      ElMessage.success('付款码收款已提交')
    } else {
      ElMessage.success('现场临时订单已创建')
    }
    fetchData()
  } catch (err: any) {
    ElMessage.error(err?.message || '现场收款创建失败')
  } finally {
    temporaryOrderSubmitting.value = false
  }
}

async function handleTemporaryCodePayQuery() {
  if (!temporarySession.value?.id) return
  temporaryCodePayQuerying.value = true
  try {
    const res = await queryTemporaryCodePay(temporarySession.value.id)
    temporaryOrderResult.value = res.data
    if (res.data.trade_state === 'SUCCESS') {
      ElMessage.success('付款已确认')
      fetchData()
      return
    }
    ElMessage.info(res.data.requires_query ? '仍需稍后继续查单' : `当前状态：${res.data.trade_state || '未知'}`)
  } catch (err: any) {
    ElMessage.error(err?.message || '付款码查单失败')
  } finally {
    temporaryCodePayQuerying.value = false
  }
}

function handleTemporaryQrcodeError() {
  temporaryQrcodeLoadFailed.value = true
  ElMessage.warning('小程序码加载失败，请复制 miniapp_path 备用')
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

function formatYuanAmount(value: number | string | null | undefined): string {
  const amount = Number(value || 0)
  return Number.isFinite(amount) ? amount.toFixed(2) : '0.00'
}

function getOrderUserDisplay(row: Order): string {
  return row.user_nickname || row.user_name || `用户 #${row.user_id || '-'}`
}

function getOrderPhoneDisplay(row: Order): string {
  return row.user_phone_masked || row.user_phone || '-'
}

function getOrderItemCount(row: Order): number {
  return row.item_count ?? row.items?.length ?? 0
}

function getRefundModeLabel(mode: string) {
  return { full: '全额', partial: '部分', item: '按项' }[mode] || mode
}

async function handleApproveRefundRecord(row: RefundRecord) {
  await ElMessageBox.confirm(`确认通过退款 ${row.refund_no}？金额: ¥${formatYuanAmount(row.refund_amount)}`, '退款审批', {
    type: 'warning',
  })
  await approveRefundRecord(row.id)
  ElMessage.success('退款已通过')
  fetchRefundQueue()
  fetchData()
}

async function handleRejectRefundRecord(row: RefundRecord) {
  const reason = await ElMessageBox.prompt('请输入拒绝理由', '拒绝退款', {
    inputType: 'textarea',
    inputValidator: value => !!value?.trim() || '请填写拒绝理由',
  })
  await rejectRefundRecord(row.id, reason.value)
  ElMessage.success('已拒绝退款')
  fetchRefundQueue()
  fetchData()
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.text-secondary { font-size: 12px; color: var(--color-text-placeholder); }
.price { font-weight: 700; color: var(--color-accent); letter-spacing: 0.5px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.temporary-result { margin-top: 16px; }
.temporary-result__detail { margin-top: 12px; }
.temporary-result__actions { margin-top: 12px; display: flex; justify-content: flex-end; }
.temporary-result__qrcode {
  width: 168px;
  height: 168px;
  border-radius: 8px;
  border: 1px solid var(--color-border-light);
  background: #fff;
}
.temporary-result__qrcode--error {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  background: var(--color-bg);
}
</style>
