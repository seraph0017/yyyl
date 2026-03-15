<template>
  <div class="page-container">
    <!-- 财务概览卡片 -->
    <el-row :gutter="16" class="mb-20">
      <el-col :span="6">
        <div class="finance-card" style="border-left-color: #FF9800;">
          <div class="fc-label">待确认金额</div>
          <div class="fc-value">¥{{ formatPrice(overview.pending_amount || 0) }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="finance-card" style="border-left-color: #4CAF50;">
          <div class="fc-label">可提现金额</div>
          <div class="fc-value text-success">¥{{ formatPrice(overview.withdrawable_amount || 0) }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="finance-card" style="border-left-color: #2196F3;">
          <div class="fc-label">押金专户</div>
          <div class="fc-value">¥{{ formatPrice(overview.deposit_amount || 0) }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="finance-card" style="border-left-color: #2E7D32;">
          <div class="fc-label">本月收入</div>
          <div class="fc-value text-primary">¥{{ formatPrice(overview.month_income || 0) }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 交易流水 -->
    <div class="card-box">
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
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" @change="handleDateChange" />
        </el-form-item>
        <el-form-item><el-button type="primary" @click="handleSearch">查询</el-button></el-form-item>
      </el-form>

      <el-table :data="transactions" v-loading="loading" stripe>
        <el-table-column prop="transaction_no" label="交易号" width="200" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.type === 'income' ? 'success' : row.type === 'refund' ? 'danger' : 'info'">
              {{ { income: '收入', refund: '退款', withdraw: '提现', deposit_refund: '押金退还' }[row.type as string] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">
            <span :class="row.type === 'income' ? 'text-success' : 'text-danger'">
              {{ row.type === 'income' ? '+' : '-' }}¥{{ formatPrice(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="related_order_no" label="关联订单" width="200" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'pending' ? 'warning' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="params.page" v-model:page-size="params.page_size" :total="total" layout="total, sizes, prev, pager, next" @size-change="fetchTransactions" @current-change="fetchTransactions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getFinanceOverview, getTransactions } from '@/api/finance'
import { formatPrice, formatDateTime } from '@/utils'
import type { FinanceOverview, FinanceTransaction, TransactionSearchParams } from '@/types'

const loading = ref(false)
const overview = ref<Partial<FinanceOverview>>({})
const transactions = ref<FinanceTransaction[]>([])
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)
const params = reactive<TransactionSearchParams>({ page: 1, page_size: 20 })

async function fetchOverview() {
  try { const res = await getFinanceOverview(); overview.value = res.data }
  catch { overview.value = { pending_amount: 285000, withdrawable_amount: 1860000, deposit_amount: 320000, month_income: 680000 } }
}

async function fetchTransactions() {
  loading.value = true
  try { const res = await getTransactions(params); transactions.value = res.data.list; total.value = res.data.pagination.total }
  catch { transactions.value = [] }
  finally { loading.value = false }
}

function handleSearch() { params.page = 1; fetchTransactions() }
function handleDateChange(val: [string, string] | null) {
  params.start_date = val?.[0]; params.end_date = val?.[1]; handleSearch()
}

onMounted(() => { fetchOverview(); fetchTransactions() })
</script>

<style lang="scss" scoped>
.finance-card {
  background: #fff; border-radius: 8px; padding: 20px; border-left: 4px solid; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  .fc-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
  .fc-value { font-size: 24px; font-weight: 700; color: #303133; }
}
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
