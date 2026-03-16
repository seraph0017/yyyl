<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>订单管理</h3>
      </div>

      <!-- 搜索/筛选 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-input v-model="searchParams.keyword" placeholder="订单号/用户昵称/手机号" clearable style="width: 240px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.status" placeholder="订单状态" clearable @change="handleSearch">
            <el-option v-for="(v, k) in orderStatusMap" :key="k" :label="v.label" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="handleDateChange" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, View, RefreshLeft } from '@element-plus/icons-vue'
import { getOrders, approveRefund } from '@/api/order'
import { formatPrice, formatDateTime, orderStatusMap, paymentStatusMap } from '@/utils'
import type { Order, OrderSearchParams } from '@/types'

const router = useRouter()
const loading = ref(false)
const tableData = ref<Order[]>([])
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)

const searchParams = reactive<OrderSearchParams>({
  page: 1,
  page_size: 20,
  keyword: '',
  status: undefined,
  start_date: undefined,
  end_date: undefined,
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

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function handleReset() {
  searchParams.keyword = ''
  searchParams.status = undefined
  searchParams.start_date = undefined
  searchParams.end_date = undefined
  dateRange.value = null
  handleSearch()
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
