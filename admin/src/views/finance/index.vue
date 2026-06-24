<template>
  <div class="page-container">
    <el-row :gutter="16" class="mb-20">
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="finance-card" style="border-left-color: var(--color-accent);">
          <div class="fc-label">待确认金额</div>
          <div class="fc-value">¥{{ formatPrice(overview.pending_amount || 0) }}</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="finance-card" style="border-left-color: var(--color-primary);">
          <div class="fc-label">可提现金额</div>
          <div class="fc-value text-success">¥{{ formatPrice(overview.available_amount || overview.withdrawable_amount || 0) }}</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="finance-card" style="border-left-color: #4a8ba8;">
          <div class="fc-label">押金专户</div>
          <div class="fc-value">¥{{ formatPrice(overview.deposit_amount || 0) }}</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <div class="finance-card" style="border-left-color: var(--color-primary-light);">
          <div class="fc-label">本月收入</div>
          <div class="fc-value text-primary">¥{{ formatPrice(overview.month_income || 0) }}</div>
        </div>
      </el-col>
    </el-row>

    <div class="card-box">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="交易流水" name="transactions">
          <div class="flex-between mb-16">
            <h3>交易流水</h3>
          </div>

          <el-form :inline="true" class="mb-16">
            <el-form-item>
              <el-select v-model="params.type" placeholder="类型" clearable @change="handleSearch">
                <el-option label="收入" value="income" />
                <el-option label="退款" value="refund" />
                <el-option label="提现" value="withdraw" />
                <el-option label="押金退还" value="deposit_refund" />
                <el-option label="结算" value="settlement" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始"
                end-placeholder="结束"
                value-format="YYYY-MM-DD"
                @change="handleDateChange"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="transactions" v-loading="loading" stripe>
            <el-table-column prop="transaction_no" label="交易号" width="200" />
            <el-table-column label="类型" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="getTransactionTagType(row.type)">
                  {{ getTransactionTypeLabel(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="金额" width="120" align="right">
              <template #default="{ row }">
                <span :class="row.type === 'refund' || row.type === 'withdraw' ? 'text-danger' : 'text-success'">
                  {{ row.type === 'refund' || row.type === 'withdraw' ? '-' : '+' }}¥{{ formatPrice(row.amount) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="200" />
            <el-table-column prop="related_order_no" label="关联订单" width="200" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'pending' ? 'warning' : 'info'">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="params.page"
              v-model:page-size="params.page_size"
              :total="total"
              layout="total, sizes, prev, pager, next"
              @size-change="fetchTransactions"
              @current-change="fetchTransactions"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="结算记录" name="settlements">
          <div class="flex-between mb-16">
            <h3>结算记录</h3>
            <el-button :loading="settlementLoading" @click="fetchSettlements">刷新</el-button>
          </div>

          <el-table :data="settlements" v-loading="settlementLoading" stripe>
            <el-table-column prop="settlement_no" label="结算单号" width="210" />
            <el-table-column prop="order_id" label="订单ID" width="110" />
            <el-table-column label="金额" width="120" align="right">
              <template #default="{ row }">
                <span class="text-success">¥{{ formatPrice(row.amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'completed' ? 'success' : 'danger'">
                  {{ row.status === 'completed' ? '已完成' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="触发方式" width="110" align="center">
              <template #default="{ row }">
                {{ row.trigger_type === 'manual' ? '手动' : '自动' }}
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="失败原因" min-width="220" show-overflow-tooltip />
            <el-table-column label="结算时间" width="170">
              <template #default="{ row }">{{ row.settled_at ? formatDateTime(row.settled_at) : '-' }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column v-if="userStore.isSuperAdmin" label="操作" width="100" fixed="right" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'failed'"
                  link
                  type="primary"
                  :loading="retryingOrderId === row.order_id"
                  @click="handleRetrySettlement(row)"
                >
                  重试
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="settlementParams.page"
              v-model:page-size="settlementParams.page_size"
              :total="settlementTotal"
              layout="total, sizes, prev, pager, next"
              @size-change="fetchSettlements"
              @current-change="fetchSettlements"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getFinanceOverview, getSettlements, getTransactions } from '@/api/finance'
import { settleOrder } from '@/api/order'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { formatPrice, formatDateTime } from '@/utils'
import type {
  FinanceOverview,
  FinanceSettlement,
  FinanceTransaction,
  SettlementSearchParams,
  TransactionSearchParams,
} from '@/types'

const activeTab = ref<'transactions' | 'settlements'>('transactions')
const userStore = useUserStore()
const loading = ref(false)
const settlementLoading = ref(false)
const retryingOrderId = ref<number | null>(null)
const overview = ref<Partial<FinanceOverview>>({})
const transactions = ref<FinanceTransaction[]>([])
const settlements = ref<FinanceSettlement[]>([])
const total = ref(0)
const settlementTotal = ref(0)
const dateRange = ref<[string, string] | null>(null)
const params = reactive<TransactionSearchParams>({ page: 1, page_size: 20 })
const settlementParams = reactive<SettlementSearchParams>({ page: 1, page_size: 20 })

async function fetchOverview() {
  try {
    const res = await getFinanceOverview()
    overview.value = res.data
  } catch {
    overview.value = { pending_amount: 0, available_amount: 0, deposit_amount: 0, month_income: 0 }
  }
}

async function fetchTransactions() {
  loading.value = true
  try {
    const res = await getTransactions(params)
    transactions.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    transactions.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function fetchSettlements() {
  settlementLoading.value = true
  try {
    const res = await getSettlements(settlementParams)
    settlements.value = res.data.list
    settlementTotal.value = res.data.pagination.total
  } catch {
    settlements.value = []
    settlementTotal.value = 0
  } finally {
    settlementLoading.value = false
  }
}

function handleSearch() {
  params.page = 1
  fetchTransactions()
}

function handleDateChange(val: [string, string] | null) {
  params.start_date = val?.[0]
  params.end_date = val?.[1]
  handleSearch()
}

function handleTabChange(tabName: string | number) {
  if (tabName === 'settlements' && settlements.value.length === 0) {
    fetchSettlements()
  }
}

function getTransactionTypeLabel(type: string) {
  return {
    income: '收入',
    refund: '退款',
    withdraw: '提现',
    deposit_refund: '押金退还',
    settlement: '结算',
  }[type] || type
}

function getTransactionTagType(type: string) {
  if (type === 'income' || type === 'settlement') return 'success'
  if (type === 'refund') return 'danger'
  return 'info'
}

async function handleRetrySettlement(row: FinanceSettlement) {
  retryingOrderId.value = row.order_id
  try {
    await settleOrder(row.order_id)
    ElMessage.success('结算重试已完成')
    await Promise.all([fetchOverview(), fetchSettlements(), fetchTransactions()])
  } finally {
    retryingOrderId.value = null
  }
}

onMounted(() => {
  fetchOverview()
  fetchTransactions()
})
</script>

<style lang="scss" scoped>
.finance-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  padding: 24px;
  border-left: 4px solid;
  box-shadow: var(--shadow-light);
  border-top: 1px solid var(--color-border-light);
  border-right: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
  transition: var(--transition-base);

  &:hover {
    box-shadow: var(--shadow-base);
    transform: translateY(-2px);
  }

  .fc-label {
    font-size: 13px;
    color: var(--color-text-placeholder);
    margin-bottom: 10px;
    letter-spacing: 0;
  }

  .fc-value {
    font-size: 26px;
    font-weight: 800;
    color: var(--color-text);
    letter-spacing: 0;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}
</style>
