<template>
  <div class="page-container">
    <!-- 搭配统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">搭配订单数</div>
        <div class="stat-value">{{ bundleStats.total_bundle_orders }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">搭配率</div>
        <div class="stat-value">{{ (bundleStats.bundle_rate * 100).toFixed(1) }}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">搭配营收</div>
        <div class="stat-value price">¥{{ formatPrice(bundleStats.bundle_revenue) }}</div>
      </div>
    </div>

    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>搭配组合管理</h3>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>新建组合
        </el-button>
      </div>

      <!-- 搜索/筛选 -->
      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-input v-model="searchParams.keyword" placeholder="搜索组合名称" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="searchParams.status" placeholder="状态筛选" clearable @change="handleSearch">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch"><el-icon><Search /></el-icon>搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="main_product_name" label="主商品" min-width="140" show-overflow-tooltip />
        <el-table-column prop="name" label="组合名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="搭配项数" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.items?.length || 0 }} 项</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="有效期" width="220">
          <template #default="{ row }">
            {{ formatDate(row.start_at) }} ~ {{ formatDate(row.end_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="70" align="center" />
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="handleEdit(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--delete" circle size="small" @click="handleDelete(row)">
                  <el-icon><Delete /></el-icon>
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

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑搭配组合' : '新建搭配组合'"
      width="720px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="组合名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入组合名称" />
        </el-form-item>
        <el-form-item label="主商品" prop="main_product_id">
          <el-select v-model="formData.main_product_id" filterable placeholder="搜索选择主商品" style="width: 100%">
            <el-option v-for="p in productList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="有效期" prop="start_at">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="formData.sort_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="inactive">停用</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 搭配项列表 -->
        <el-divider content-position="left">搭配项</el-divider>
        <div v-for="(item, index) in formData.items" :key="index" class="bundle-item-row">
          <el-form-item :label="`搭配项 ${index + 1}`" class="bundle-item-form">
            <div class="bundle-item-fields">
              <el-select v-model="item.product_id" filterable placeholder="选择商品" style="width: 180px">
                <el-option v-for="p in productList" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
              <el-input-number v-model="item.bundle_price" :min="0" placeholder="搭配价(分)" controls-position="right" style="width: 140px" />
              <el-input-number v-model="item.max_quantity" :min="1" :max="99" placeholder="最大数量" controls-position="right" style="width: 120px" />
              <el-checkbox v-model="item.is_default_checked">默认勾选</el-checkbox>
              <el-input-number v-model="item.sort_order" :min="0" :max="99" placeholder="排序" controls-position="right" style="width: 90px" />
              <el-button type="danger" :icon="Delete" circle size="small" @click="removeItem(index)" />
            </div>
          </el-form-item>
        </div>
        <el-button type="primary" plain @click="addItem" style="margin-left: 100px">
          <el-icon><Plus /></el-icon>添加搭配项
        </el-button>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, Plus, Delete, Edit } from '@element-plus/icons-vue'
import { getBundleConfigs, createBundleConfig, updateBundleConfig, deleteBundleConfig, getBundleStats } from '@/api/bundle'
import { formatPrice, formatDate } from '@/utils'
import type { BundleConfig, BundleConfigCreate, BundleItemCreate, BundleStats } from '@/types'

// 简易商品列表（实际应从商品API获取）
import { get } from '@/utils/request'
const productList = ref<{ id: number; name: string }[]>([])
async function fetchProducts() {
  try {
    const res = await get<{ data: { list: { id: number; name: string }[] } }>('/admin/products', { page: 1, page_size: 200 })
    productList.value = res.data.list
  } catch { /* ignore */ }
}

const loading = ref(false)
const submitting = ref(false)
const tableData = ref<BundleConfig[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const dateRange = ref<[string, string] | null>(null)

const bundleStats = reactive<BundleStats>({
  total_bundle_orders: 0,
  bundle_rate: 0,
  bundle_revenue: 0,
  top_bundles: [],
})

const searchParams = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  status: undefined as string | undefined,
})

const defaultItem = (): BundleItemCreate => ({
  product_id: 0,
  sku_id: null,
  bundle_price: 0,
  max_quantity: 1,
  is_default_checked: false,
  sort_order: 0,
})

const formData = reactive<BundleConfigCreate>({
  name: '',
  main_product_id: 0,
  status: 'active',
  start_at: '',
  end_at: '',
  sort_order: 0,
  items: [defaultItem()],
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入组合名称', trigger: 'blur' }],
  main_product_id: [{ required: true, message: '请选择主商品', trigger: 'change' }],
  start_at: [{ required: true, message: '请选择有效期', trigger: 'change' }],
}

// 监听日期范围
watch(dateRange, (val) => {
  if (val) {
    formData.start_at = val[0]
    formData.end_at = val[1]
  } else {
    formData.start_at = ''
    formData.end_at = ''
  }
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getBundleConfigs(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await getBundleStats()
    Object.assign(bundleStats, res.data)
  } catch { /* ignore */ }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function handleReset() {
  searchParams.keyword = ''
  searchParams.status = undefined
  handleSearch()
}

function resetForm() {
  formData.name = ''
  formData.main_product_id = 0
  formData.status = 'active'
  formData.start_at = ''
  formData.end_at = ''
  formData.sort_order = 0
  formData.items = [defaultItem()]
  dateRange.value = null
  editingId.value = null
}

function handleCreate() {
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row: BundleConfig) {
  editingId.value = row.id
  formData.name = row.name
  formData.main_product_id = row.main_product_id
  formData.status = row.status
  formData.start_at = row.start_at
  formData.end_at = row.end_at
  formData.sort_order = row.sort_order
  formData.items = row.items.map(item => ({
    product_id: item.product_id,
    sku_id: item.sku_id,
    bundle_price: item.bundle_price,
    max_quantity: item.max_quantity,
    is_default_checked: item.is_default_checked,
    sort_order: item.sort_order,
  }))
  dateRange.value = [row.start_at, row.end_at]
  dialogVisible.value = true
}

async function handleDelete(row: BundleConfig) {
  await ElMessageBox.confirm(`确认删除搭配组合「${row.name}」？`, '删除确认', { type: 'warning' })
  await deleteBundleConfig(row.id)
  ElMessage.success('删除成功')
  fetchData()
  fetchStats()
}

function addItem() {
  formData.items.push(defaultItem())
}

function removeItem(index: number) {
  if (formData.items.length <= 1) {
    ElMessage.warning('至少保留一个搭配项')
    return
  }
  formData.items.splice(index, 1)
}

async function handleSubmit() {
  await formRef.value?.validate()
  if (!formData.items.length || formData.items.some(i => !i.product_id)) {
    ElMessage.warning('请完善搭配项商品信息')
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateBundleConfig(editingId.value, { ...formData })
      ElMessage.success('更新成功')
    } else {
      await createBundleConfig({ ...formData })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
    fetchStats()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchStats()
  fetchProducts()
})
</script>

<style lang="scss" scoped>
.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;

  .stat-card {
    flex: 1;
    background: var(--color-bg-card);
    border-radius: var(--radius-base);
    padding: 20px 24px;
    box-shadow: var(--shadow-light);
    border: 1px solid var(--color-border-light);
    transition: var(--transition-base);
    &:hover { box-shadow: var(--shadow-base); }

    .stat-label {
      font-size: 13px;
      color: var(--color-text-placeholder);
      margin-bottom: 8px;
      letter-spacing: 0.5px;
    }
    .stat-value {
      font-size: 28px;
      font-weight: 800;
      color: var(--color-text);
      &.price { color: var(--color-accent); }
    }
  }
}

.bundle-item-row {
  margin-bottom: 8px;
}

.bundle-item-fields {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}
</style>
