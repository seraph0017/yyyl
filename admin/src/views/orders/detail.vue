<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>订单详情</h3>
        <div>
          <el-button type="primary" :disabled="!canRefund" @click="openRefundDialog">退款</el-button>
          <el-button @click="router.back()">返回</el-button>
        </div>
      </div>

      <el-skeleton :loading="loading" :rows="10" animated>
        <template #default>
          <!-- 基本信息 -->
          <el-descriptions :column="3" border class="mb-20">
            <el-descriptions-item label="订单号">{{ order.order_no }}</el-descriptions-item>
            <el-descriptions-item label="订单状态">
              <el-tag :type="getOrderTagType(order.status)" size="small">
                {{ getOrderStatusLabel(order.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="支付状态">
              <el-tag :type="getPaymentTagType(order.payment_status)" size="small">
                {{ getPaymentStatusLabel(order.payment_status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="用户昵称">{{ order.user_nickname }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ order.user_phone }}</el-descriptions-item>
            <el-descriptions-item label="支付方式">{{ order.payment_method }}</el-descriptions-item>
            <el-descriptions-item label="订单金额"><span class="price">¥{{ formatYuanAmount(order.total_amount) }}</span></el-descriptions-item>
            <el-descriptions-item label="实付金额">¥{{ formatYuanAmount(orderActualPaidAmount) }}</el-descriptions-item>
            <el-descriptions-item label="退款金额">¥{{ formatYuanAmount(order.refund_amount) }}</el-descriptions-item>
            <el-descriptions-item label="结算状态">
              <el-tag :type="getSettlementTagType(order.settlement_status)" size="small">
                {{ getSettlementStatusLabel(order.settlement_status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="已结算金额">¥{{ formatYuanAmount(order.settled_amount || 0) }}</el-descriptions-item>
            <el-descriptions-item label="下单时间">{{ formatDateTime(order.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="支付时间">{{ order.payment_time ? formatDateTime(order.payment_time) : '--' }}</el-descriptions-item>
            <el-descriptions-item label="过期时间">{{ formatDateTime(order.expire_at) }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="3">{{ order.remark || '无' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 商品列表 -->
          <h4 class="mb-16">商品明细</h4>
          <el-table :data="order.items" border class="mb-20">
            <el-table-column prop="product_name" label="商品名称" />
            <el-table-column label="品类" width="100">
              <template #default="{ row }">{{ getCategoryName(row.product_category) }}</template>
            </el-table-column>
            <el-table-column prop="sku_name" label="规格" width="120" />
            <el-table-column prop="quantity" label="数量" width="80" align="center" />
            <el-table-column label="单价" width="100" align="right">
              <template #default="{ row }">¥{{ formatYuanAmount(row.unit_price) }}</template>
            </el-table-column>
            <el-table-column label="实际价" width="100" align="right">
              <template #default="{ row }"><span class="price">¥{{ formatYuanAmount(row.actual_price) }}</span></template>
            </el-table-column>
            <el-table-column label="日期" width="120">
              <template #default="{ row }">{{ row.date || '--' }}</template>
            </el-table-column>
            <el-table-column label="票务状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.ticket_status" size="small" :type="row.ticket_status === 'used' ? 'success' : row.ticket_status === 'unused' ? 'warning' : 'info'">
                  {{ getTicketStatusLabel(row.ticket_status) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <h4 class="mb-16">退款历史</h4>
          <el-table :data="refunds" border class="mb-20" v-loading="refundLoading">
            <el-table-column prop="refund_no" label="退款单号" width="200" />
            <el-table-column label="模式" width="100" align="center">
              <template #default="{ row }">{{ getRefundModeLabel(row.refund_mode) }}</template>
            </el-table-column>
            <el-table-column label="订单处理" width="120" align="center">
              <template #default="{ row }">{{ row.order_action === 'cancel_order' ? '取消订单' : '保留订单' }}</template>
            </el-table-column>
            <el-table-column label="金额" width="120" align="right">
              <template #default="{ row }">¥{{ formatYuanAmount(row.refund_amount) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="getRefundStatusTagType(row.status)" size="small">{{ getRefundStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="center">
              <template #default="{ row }">
                <el-button v-if="row.status === 'pending'" link type="primary" @click="handleApproveRefund(row.id)">通过</el-button>
                <el-button v-if="row.status === 'pending'" link type="danger" @click="handleRejectRefund(row.id)">拒绝</el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-skeleton>
    </div>

    <el-dialog v-model="refundDialogVisible" title="订单退款" width="620px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="退款模式">
          <el-segmented v-model="refundForm.refund_mode" :options="refundModeOptions" @change="handleRefundModeChange" />
        </el-form-item>
        <el-form-item label="订单处理">
          <el-radio-group v-model="refundForm.order_action" @change="handleOrderActionChange">
            <el-radio-button v-if="canKeepOrderRefund" label="keep_order">保留订单</el-radio-button>
            <el-radio-button label="cancel_order">取消订单</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="释放库存">
          <el-switch v-model="refundForm.release_inventory" :disabled="refundForm.order_action === 'keep_order'" />
        </el-form-item>
        <el-form-item label="退款金额">
          <el-input-number v-model="refundAmountYuan" :min="0.01" :precision="2" :step="10" controls-position="right" />
        </el-form-item>
        <el-form-item v-if="refundForm.refund_mode === 'item'" label="退款商品">
          <el-checkbox-group v-model="selectedRefundItemIds" class="refund-items">
            <el-table :data="order.items" border size="small">
              <el-table-column width="48" align="center">
                <template #default="{ row }">
                  <el-checkbox :label="row.id" />
                </template>
              </el-table-column>
              <el-table-column prop="product_name" label="商品" />
              <el-table-column label="可退金额" width="100" align="right">
                <template #default="{ row }">¥{{ formatYuanAmount(row.actual_price) }}</template>
              </el-table-column>
              <el-table-column prop="quantity" label="数量" width="70" align="center" />
            </el-table>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="退款原因">
          <el-input v-model="refundForm.reason" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
        <el-alert
          v-if="isHighRiskRefund"
          class="mb-16"
          type="warning"
          show-icon
          :closable="false"
          title="全额退款且保留订单属于高风险操作，请确认不会影响后续核销和服务履约。"
        />
      </el-form>
      <template #footer>
        <el-button @click="refundDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="refundSubmitting" @click="submitRefund">提交退款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveRefundRecord, createRefund, getOrderDetail, getOrderRefunds, rejectRefundRecord } from '@/api/order'
import { useUserStore } from '@/stores/user'
import { formatDateTime, getCategoryName, orderStatusMap, paymentStatusMap } from '@/utils'
import type { Order, OrderStatus, PaymentStatus, RefundCreatePayload, RefundRecord } from '@/types'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const loading = ref(true)
const refundLoading = ref(false)
const refundDialogVisible = ref(false)
const refundSubmitting = ref(false)
const refundAmountYuan = ref(0)
const selectedRefundItemIds = ref<number[]>([])
const refunds = ref<RefundRecord[]>([])
const refundModeOptions = [
  { label: '全额', value: 'full' },
  { label: '部分', value: 'partial' },
  { label: '按项', value: 'item' },
]
const refundForm = reactive<RefundCreatePayload>({
  refund_mode: 'full',
  order_action: 'cancel_order',
  refund_amount: 0,
  release_inventory: true,
  reason: '',
})
const order = ref<Order>({
  id: 0,
  order_no: '',
  user_id: 0,
  user_nickname: '',
  user_phone: '',
  user_phone_masked: null,
  status: 'pending_payment',
  payment_status: 'unpaid',
  payment_method: '',
  total_amount: 0,
  actual_amount: 0,
  paid_amount: 0,
  refund_amount: 0,
  settled_amount: 0,
  settlement_status: 'unsettled',
  item_count: 0,
  remark: null,
  expire_at: '',
  payment_time: null,
  paid_at: null,
  created_at: '',
  updated_at: '',
  items: [],
})

const orderActualPaidAmount = computed(() => order.value.actual_amount ?? order.value.paid_amount ?? 0)

function formatYuanAmount(value?: number | string | null) {
  const amount = Number(value ?? 0)
  if (!Number.isFinite(amount)) return '0.00'
  return amount.toFixed(2)
}

async function fetchOrder() {
  const id = Number(route.params.id)
  try {
    const res = await getOrderDetail(id)
    order.value = res.data
    fetchRefunds()
  } catch {} finally {
    loading.value = false
  }
}

async function fetchRefunds() {
  if (!order.value.id) return
  refundLoading.value = true
  try {
    const res = await getOrderRefunds(order.value.id)
    refunds.value = res.data
  } finally {
    refundLoading.value = false
  }
}

const canRefund = computed(() => ['paid', 'verified', 'completed'].includes(order.value.status))
const isHighRiskRefund = computed(() => refundForm.refund_mode === 'full' && refundForm.order_action === 'keep_order')
const canKeepOrderRefund = computed(() => refundForm.refund_mode !== 'full' || userStore.isSuperAdmin)

function openRefundDialog() {
  refundForm.refund_mode = 'full'
  refundForm.order_action = 'cancel_order'
  refundForm.release_inventory = true
  refundForm.reason = ''
  refundAmountYuan.value = orderActualPaidAmount.value
  selectedRefundItemIds.value = order.value.items.map(item => item.id)
  refundDialogVisible.value = true
}

function handleRefundModeChange() {
  if (refundForm.refund_mode === 'full' && !userStore.isSuperAdmin) {
    refundForm.order_action = 'cancel_order'
    refundForm.release_inventory = true
  }
  if (refundForm.refund_mode === 'full') {
    refundAmountYuan.value = orderActualPaidAmount.value
    selectedRefundItemIds.value = order.value.items.map(item => item.id)
  }
  if (refundForm.refund_mode === 'item') {
    updateItemRefundAmount()
  }
}

function handleOrderActionChange() {
  refundForm.release_inventory = refundForm.order_action === 'cancel_order'
}

function updateItemRefundAmount() {
  const cents = order.value.items
    .filter(item => selectedRefundItemIds.value.includes(item.id))
    .reduce((sum, item) => sum + item.actual_price, 0)
  refundAmountYuan.value = cents
}

async function submitRefund() {
  if (!refundForm.reason.trim()) {
    ElMessage.warning('请填写退款原因')
    return
  }
  if (refundForm.refund_mode === 'item' && selectedRefundItemIds.value.length === 0) {
    ElMessage.warning('请选择退款商品')
    return
  }
  if (isHighRiskRefund.value) {
    await ElMessageBox.confirm('确认执行全额退款且不取消订单？', '高风险退款确认', { type: 'warning' })
  }

  refundSubmitting.value = true
  try {
    const amount = Number(refundAmountYuan.value.toFixed(2))
    const payload: RefundCreatePayload = {
      ...refundForm,
      refund_amount: amount,
      items: refundForm.refund_mode === 'item'
        ? order.value.items
          .filter(item => selectedRefundItemIds.value.includes(item.id))
          .map(item => ({ order_item_id: item.id, refund_amount: item.actual_price, quantity: item.quantity }))
        : undefined,
    }
    await createRefund(order.value.id, payload)
    ElMessage.success('退款记录已创建')
    refundDialogVisible.value = false
    await fetchOrder()
  } finally {
    refundSubmitting.value = false
  }
}

async function handleApproveRefund(refundId: number) {
  await ElMessageBox.confirm('确认通过该退款申请？', '退款审批', { type: 'warning' })
  await approveRefundRecord(refundId)
  ElMessage.success('退款已通过')
  fetchRefunds()
}

async function handleRejectRefund(refundId: number) {
  const result = await ElMessageBox.prompt('请输入拒绝理由', '拒绝退款', {
    inputType: 'textarea',
    inputValidator: value => !!value?.trim() || '请填写拒绝理由',
  })
  await rejectRefundRecord(refundId, result.value)
  ElMessage.success('已拒绝退款')
  fetchRefunds()
}

function getSettlementStatusLabel(status?: string) {
  return {
    unsettled: '未结算',
    partial: '部分结算',
    settled: '已结算',
    failed: '结算失败',
  }[status || 'unsettled'] || '未结算'
}

function getSettlementTagType(status?: string) {
  if (status === 'settled') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'partial') return 'warning'
  return 'info'
}

function getOrderStatusLabel(status: OrderStatus) {
  return orderStatusMap[status]?.label || status
}

function getOrderTagType(status: OrderStatus) {
  return (orderStatusMap[status]?.type || 'info') as any
}

function getPaymentStatusLabel(status: PaymentStatus) {
  return paymentStatusMap[status]?.label || status
}

function getPaymentTagType(status: PaymentStatus) {
  return (paymentStatusMap[status]?.type || 'info') as any
}

function getTicketStatusLabel(status: string) {
  return {
    unused: '未使用',
    used: '已使用',
    expired: '已过期',
    refunded: '已退票',
  }[status] || status
}

function getRefundModeLabel(mode: string) {
  return { full: '全额', partial: '部分', item: '按项' }[mode] || mode
}

function getRefundStatusLabel(status: string) {
  return {
    pending: '待审批',
    approved: '已通过',
    processing: '处理中',
    completed: '已完成',
    rejected: '已拒绝',
    failed: '失败',
  }[status] || status
}

function getRefundStatusTagType(status: string) {
  if (status === 'completed' || status === 'approved') return 'success'
  if (status === 'pending' || status === 'processing') return 'warning'
  if (status === 'rejected' || status === 'failed') return 'danger'
  return 'info'
}

onMounted(fetchOrder)

watch(selectedRefundItemIds, () => {
  if (refundForm.refund_mode === 'item') {
    updateItemRefundAmount()
  }
})
</script>

<style lang="scss" scoped>
.price { font-weight: 700; color: var(--color-accent); letter-spacing: 0.5px; }
</style>
