<template>
  <div class="page-container">
    <!-- 顶部统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">报销总额</div>
        <div class="stat-value price">¥{{ formatPrice(expenseStats.total_amount) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本月报销</div>
        <div class="stat-value price">¥{{ formatPrice(expenseStats.month_total) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">待审批</div>
        <div class="stat-value">{{ pendingCount }}</div>
      </div>
      <div class="stat-card clickable" @click="router.push('/expense-stats')">
        <div class="stat-label">查看统计报表</div>
        <div class="stat-value"><el-icon><TrendCharts /></el-icon></div>
      </div>
    </div>

    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>报销管理</h3>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>新建报销
        </el-button>
      </div>

      <!-- 搜索/筛选 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-select v-model="searchParams.status" placeholder="状态筛选" clearable @change="handleSearch">
            <el-option v-for="(v, k) in expenseStatusMap" :key="k" :label="v.label" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.expense_type_id" placeholder="报销类型" clearable @change="handleSearch">
            <el-option v-for="t in expenseTypes" :key="t.id" :label="t.name" :value="t.id" />
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

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="applicant_name" label="报销人" width="100" />
        <el-table-column prop="expense_type_name" label="报销类型" width="110" />
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ formatPrice(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="报销日期" width="120">
          <template #default="{ row }">{{ formatDate(row.expense_date) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="160" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="(expenseStatusMap[row.status]?.type as any) || 'info'" size="small">
              {{ expenseStatusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleDetail(row)">详情</el-button>
            <el-button v-if="row.status === 'pending'" text type="success" @click="handleApprove(row, true)">通过</el-button>
            <el-button v-if="row.status === 'pending'" text type="warning" @click="handleApprove(row, false)">驳回</el-button>
            <el-button v-if="row.status === 'approved'" text type="primary" @click="handleMarkPaid(row)">打款</el-button>
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

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="报销详情" width="600px">
      <el-descriptions v-if="currentDetail" :column="2" border>
        <el-descriptions-item label="报销人">{{ currentDetail.applicant_name }}</el-descriptions-item>
        <el-descriptions-item label="报销类型">{{ currentDetail.expense_type_name }}</el-descriptions-item>
        <el-descriptions-item label="金额">¥{{ formatPrice(currentDetail.amount) }}</el-descriptions-item>
        <el-descriptions-item label="报销日期">{{ formatDate(currentDetail.expense_date) }}</el-descriptions-item>
        <el-descriptions-item label="说明" :span="2">{{ currentDetail.description }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="(expenseStatusMap[currentDetail.status]?.type as any) || 'info'" size="small">
            {{ expenseStatusMap[currentDetail.status]?.label }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatDateTime(currentDetail.created_at) }}</el-descriptions-item>
        <el-descriptions-item v-if="currentDetail.reviewed_at" label="审批时间">{{ formatDateTime(currentDetail.reviewed_at) }}</el-descriptions-item>
        <el-descriptions-item v-if="currentDetail.review_remark" label="审批备注">{{ currentDetail.review_remark }}</el-descriptions-item>
        <el-descriptions-item v-if="currentDetail.paid_at" label="打款时间">{{ formatDateTime(currentDetail.paid_at) }}</el-descriptions-item>
      </el-descriptions>
      <!-- 凭证图片 -->
      <div v-if="currentDetail?.receipt_images?.length" class="receipt-images mt-16">
        <h4 class="mb-8">报销凭证</h4>
        <div class="image-list">
          <el-image
            v-for="(img, idx) in currentDetail.receipt_images"
            :key="idx"
            :src="img"
            :preview-src-list="currentDetail.receipt_images"
            :initial-index="idx"
            fit="cover"
            class="receipt-image"
          />
        </div>
      </div>
    </el-dialog>

    <!-- 新建报销弹窗 -->
    <el-dialog v-model="createVisible" title="新建报销" width="600px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="报销类型" prop="expense_type_id">
          <el-select v-model="createForm.expense_type_id" placeholder="选择报销类型" style="width: 100%">
            <el-option v-for="t in expenseTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额(分)" prop="amount">
          <el-input-number v-model="createForm.amount" :min="1" :max="99999999" style="width: 200px" />
        </el-form-item>
        <el-form-item label="报销日期" prop="expense_date">
          <el-date-picker v-model="createForm.expense_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item label="说明" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="报销说明" />
        </el-form-item>
        <el-form-item label="凭证图片">
          <el-input v-model="receiptInput" placeholder="图片URL，多个用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Plus, TrendCharts } from '@element-plus/icons-vue'
import { getExpenses, getExpenseTypes as fetchExpenseTypesApi, getExpenseStats, createExpense, approveExpense, markExpensePaid, getExpenseDetail } from '@/api/expense'
import { formatPrice, formatDate, formatDateTime } from '@/utils'
import type { ExpenseRequest, ExpenseType, ExpenseStats } from '@/types'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const tableData = ref<ExpenseRequest[]>([])
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)
const detailVisible = ref(false)
const createVisible = ref(false)
const currentDetail = ref<ExpenseRequest | null>(null)
const expenseTypes = ref<ExpenseType[]>([])
const receiptInput = ref('')
const createFormRef = ref<FormInstance>()

const expenseStats = reactive<ExpenseStats>({
  total_amount: 0,
  month_total: 0,
  type_breakdown: [],
  staff_breakdown: [],
})

const expenseStatusMap: Record<string, { label: string; type: string }> = {
  pending: { label: '待审批', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  paid: { label: '已打款', type: 'primary' },
}

const searchParams = reactive({
  page: 1,
  page_size: 20,
  status: undefined as string | undefined,
  expense_type_id: undefined as number | undefined,
  date_start: undefined as string | undefined,
  date_end: undefined as string | undefined,
})

const createForm = reactive({
  expense_type_id: undefined as number | undefined,
  amount: 0,
  expense_date: '',
  description: '',
})

const createRules: FormRules = {
  expense_type_id: [{ required: true, message: '请选择报销类型', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  expense_date: [{ required: true, message: '请选择报销日期', trigger: 'change' }],
  description: [{ required: true, message: '请输入报销说明', trigger: 'blur' }],
}

const pendingCount = computed(() => tableData.value.filter(i => i.status === 'pending').length)

async function fetchData() {
  loading.value = true
  try {
    const res = await getExpenses(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function fetchExpenseTypes() {
  try {
    const res = await fetchExpenseTypesApi()
    expenseTypes.value = res.data
  } catch { /* ignore */ }
}

async function fetchStats() {
  try {
    const res = await getExpenseStats()
    Object.assign(expenseStats, res.data)
  } catch { /* ignore */ }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function handleReset() {
  searchParams.status = undefined
  searchParams.expense_type_id = undefined
  searchParams.date_start = undefined
  searchParams.date_end = undefined
  dateRange.value = null
  handleSearch()
}

function handleDateChange(val: [string, string] | null) {
  if (val) {
    searchParams.date_start = val[0]
    searchParams.date_end = val[1]
  } else {
    searchParams.date_start = undefined
    searchParams.date_end = undefined
  }
  handleSearch()
}

async function handleDetail(row: ExpenseRequest) {
  try {
    const res = await getExpenseDetail(row.id)
    currentDetail.value = res.data
    detailVisible.value = true
  } catch { /* ignore */ }
}

async function handleApprove(row: ExpenseRequest, approved: boolean) {
  if (approved) {
    await ElMessageBox.confirm(`确认通过「${row.applicant_name}」的报销申请（¥${formatPrice(row.amount)}）？`, '审批确认', { type: 'warning' })
    await approveExpense(row.id, { approved: true })
    ElMessage.success('已通过')
  } else {
    const { value } = await ElMessageBox.prompt('请输入驳回理由', '驳回报销', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputValidator: (v) => !!v?.trim() || '请输入理由',
    })
    await approveExpense(row.id, { approved: false, review_remark: value })
    ElMessage.success('已驳回')
  }
  fetchData()
  fetchStats()
}

async function handleMarkPaid(row: ExpenseRequest) {
  await ElMessageBox.confirm(`确认标记「${row.applicant_name}」的报销（¥${formatPrice(row.amount)}）为已打款？`, '打款确认', { type: 'warning' })
  await markExpensePaid(row.id)
  ElMessage.success('已标记打款')
  fetchData()
  fetchStats()
}

function handleCreate() {
  createForm.expense_type_id = undefined
  createForm.amount = 0
  createForm.expense_date = ''
  createForm.description = ''
  receiptInput.value = ''
  createVisible.value = true
}

async function handleSubmitCreate() {
  await createFormRef.value?.validate()
  submitting.value = true
  try {
    const receipt_images = receiptInput.value
      ? receiptInput.value.split(',').map(s => s.trim()).filter(Boolean)
      : []
    await createExpense({ ...createForm, receipt_images })
    ElMessage.success('报销提交成功')
    createVisible.value = false
    fetchData()
    fetchStats()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchExpenseTypes()
  fetchStats()
})
</script>

<style lang="scss" scoped>
.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;

  .stat-card {
    flex: 1;
    background: #fff;
    border-radius: 8px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

    &.clickable {
      cursor: pointer;
      transition: box-shadow 0.2s;
      &:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12); }
    }

    .stat-label {
      font-size: 13px;
      color: #909399;
      margin-bottom: 8px;
    }
    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: #303133;
      &.price { color: #F44336; }
    }
  }
}

.price { font-weight: 600; color: #F44336; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
.mt-16 { margin-top: 16px; }
.mb-8 { margin-bottom: 8px; }

.receipt-images {
  .image-list {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .receipt-image {
    width: 120px;
    height: 90px;
    border-radius: 4px;
    border: 1px solid #ebeef5;
  }
}
</style>
