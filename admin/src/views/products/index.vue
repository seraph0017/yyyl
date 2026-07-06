<template>
  <div class="page-container">
    <div class="card-box">
      <!-- 搜索栏 -->
      <div class="flex-between mb-16 top-toolbar">
        <div class="search-bar">
          <el-input v-model="searchParams.keyword" placeholder="搜索商品名称" clearable style="width: 240px" @clear="handleSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="productGroupFilter" placeholder="商品类型" clearable style="width: 150px" @change="handleProductGroupFilterChange">
            <el-option label="营位" value="campsite" />
            <el-option label="活动" value="activity" />
            <el-option label="租赁" value="rental" />
            <el-option label="商品" value="product" />
          </el-select>
          <el-select v-model="searchParams.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
            <el-option label="上架" value="on_sale" />
            <el-option label="下架" value="off_sale" />
            <el-option label="草稿" value="draft" />
          </el-select>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>搜索
          </el-button>
        </div>
        <div class="top-actions">
          <el-segmented v-model="activeSegment" :options="segmentOptions" @change="handleSegmentChange" />
          <el-button type="primary" @click="router.push('/products/create')">
            <el-icon><Plus /></el-icon>新增商品
          </el-button>
        </div>
      </div>

      <div class="type-toolbar">
        <el-radio-group v-model="quickType" size="small" @change="handleQuickTypeChange">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="campsite">营位</el-radio-button>
          <el-radio-button label="activity">活动</el-radio-button>
          <el-radio-button label="rental">租赁</el-radio-button>
          <el-radio-button label="product">商品</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="商品信息" min-width="280">
          <template #default="{ row }">
            <div class="product-info">
              <el-image :src="getProductCover(row)" class="product-cover" fit="cover">
                <template #error><div class="image-placeholder"><el-icon><Picture /></el-icon></div></template>
              </el-image>
              <div>
                <div class="product-name">{{ row.name }}</div>
                <div class="tag-row">
                  <el-tag size="small" type="info">{{ getTypeName(row.type) }}</el-tag>
                  <el-tag size="small" effect="plain">{{ getCategoryName(row.category) }}</el-tag>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="基础价" width="120" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ formatYuanAmount(row.base_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'on_sale' ? 'success' : row.status === 'draft' ? 'info' : 'danger'" size="small">
              {{ row.status === 'on_sale' ? '上架' : row.status === 'draft' ? '草稿' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" align="center" />
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="router.push(`/products/${row.id}/edit`)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="row.status === 'on_sale' ? '下架' : '上架'" placement="top" :show-after="400">
                <el-button
                  class="action-btn"
                  :class="row.status === 'on_sale' ? 'action-btn--offline' : 'action-btn--online'"
                  circle size="small"
                  @click="handleToggleStatus(row)"
                >
                  <el-icon>
                    <Bottom v-if="row.status === 'on_sale'" />
                    <Top v-else />
                  </el-icon>
                </el-button>
              </el-tooltip>
              <el-popconfirm title="确定删除该商品？" @confirm="handleDelete(row.id)" width="200">
                <template #reference>
                  <el-tooltip content="删除" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--delete" circle size="small">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </el-tooltip>
                </template>
              </el-popconfirm>
              <el-tooltip content="二维码" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--view" circle size="small" @click="handleQrcode(row)">
                  <el-icon><Share /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <el-dialog v-model="qrcodePreviewVisible" title="商品二维码" width="420px" destroy-on-close @closed="closeQrcodePreview">
      <div class="qrcode-preview" v-if="currentQrcode">
        <img v-if="qrcodePreviewUrl" :src="qrcodePreviewUrl" alt="商品二维码" class="qrcode-preview__image" />
        <el-skeleton v-else animated :rows="4" />
        <div class="qrcode-preview__title">{{ currentQrcode.title }}</div>
        <div class="qrcode-preview__meta">scene：{{ currentQrcode.scene }}</div>
        <div class="qrcode-preview__meta">路径：{{ currentQrcode.path }}</div>
      </div>
      <template #footer>
        <el-button @click="qrcodePreviewVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!currentQrcode" @click="downloadCurrentQrcode">
          下载透明底 PNG
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Picture, Edit, Delete, Top, Bottom, Share } from '@element-plus/icons-vue'
import { getProducts, updateProductStatus, deleteProduct } from '@/api/product'
import { createQrcode, downloadQrcode } from '@/api/qrcode'
import { downloadFile, formatDateTime, getCategoryName } from '@/utils'
import type { Product, ProductSearchParams } from '@/types'
import type { Qrcode } from '@/types/qrcode'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const tableData = ref<Product[]>([])
const total = ref(0)
const qrcodePreviewVisible = ref(false)
const currentQrcode = ref<Qrcode | null>(null)
const currentQrcodeBlob = ref<Blob | null>(null)
const qrcodePreviewUrl = ref('')
type ProductGroup = 'campsite' | 'activity' | 'rental' | 'product'
const activeSegment = ref<'all' | ProductGroup>('all')
const quickType = ref<ProductGroup | ''>('')
const productGroupFilter = ref<ProductGroup | ''>('')
const segmentOptions = [
  { label: '全部', value: 'all' },
  { label: '营位', value: 'campsite' },
  { label: '活动', value: 'activity' },
  { label: '租赁', value: 'rental' },
  { label: '商品', value: 'product' },
]
const PRODUCT_GROUP_TYPES: Record<ProductGroup, ProductSearchParams['types']> = {
  campsite: ['daily_camping', 'event_camping'],
  activity: ['daily_activity', 'special_activity'],
  rental: ['rental'],
  product: ['shop', 'merchandise'],
}

const searchParams = reactive<ProductSearchParams>({
  page: 1,
  page_size: 20,
  keyword: '',
  type: undefined,
  status: undefined,
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getProducts(searchParams)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    // 模拟数据
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function applyProductGroup(value?: unknown) {
  const group = String(value || '') as ProductGroup
  const nextTypes = PRODUCT_GROUP_TYPES[group]
  if (!nextTypes) {
    searchParams.type = undefined
    delete searchParams.types
    activeSegment.value = 'all'
    quickType.value = ''
    productGroupFilter.value = ''
    return
  }
  searchParams.type = undefined
  searchParams.types = nextTypes
  activeSegment.value = group
  quickType.value = group
  productGroupFilter.value = group
}

function handleSegmentChange(value: string | number | boolean | undefined) {
  const selected = String(value || 'all')
  if (selected === 'all') {
    searchParams.type = undefined
    delete searchParams.types
    activeSegment.value = 'all'
    quickType.value = ''
    productGroupFilter.value = ''
  } else {
    applyProductGroup(selected)
  }
  handleSearch()
}

function handleQuickTypeChange(value: string | number | boolean | undefined) {
  const selected = String(value || '')
  if (!selected) {
    searchParams.type = undefined
    delete searchParams.types
    activeSegment.value = 'all'
    quickType.value = ''
    productGroupFilter.value = ''
  } else {
    applyProductGroup(selected)
  }
  handleSearch()
}

function handleProductGroupFilterChange(value: string | number | boolean | undefined) {
  const selected = String(value || '')
  if (!selected) {
    searchParams.type = undefined
    delete searchParams.types
    activeSegment.value = 'all'
    quickType.value = ''
    productGroupFilter.value = ''
  } else {
    applyProductGroup(selected)
  }
  handleSearch()
}

function getProductCover(row: Product): string {
  const first = row.images?.[0]
  return (typeof first === 'string' ? first : first?.url) || row.cover_image || ''
}

function formatYuanAmount(value: number | string | null | undefined): string {
  const amount = Number(value || 0)
  return Number.isFinite(amount) ? amount.toFixed(2) : '0.00'
}

function getTypeName(type: string): string {
  const map: Record<string, string> = {
    daily_camping: '营位',
    event_camping: '活动营位',
    rental: '租赁',
    daily_activity: '日常活动',
    special_activity: '特定活动',
    shop: '商品',
    merchandise: '商品',
  }
  return map[type] || type
}

async function handleToggleStatus(row: Product) {
  const newStatus = row.status === 'on_sale' ? 'off_sale' : 'on_sale'
  try {
    await updateProductStatus(row.id, newStatus)
    ElMessage.success(`已${newStatus === 'on_sale' ? '上架' : '下架'}`)
    row.status = newStatus
  } catch {}
}

async function handleDelete(id: number) {
  try {
    await deleteProduct(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {}
}

async function handleQrcode(row: Product) {
  await ElMessageBox.confirm(`确认为商品「${row.name}」生成小程序码？`, '商品二维码', {
    type: 'info',
    confirmButtonText: '生成',
    cancelButtonText: '取消',
  })
  const res = await createQrcode({
    target_type: ['daily_activity', 'special_activity'].includes(row.type) ? 'activity_product' : 'product',
    target_key: String(row.id),
    title: row.name,
    channel: 'admin_product',
  })
  await openQrcodePreview(res.data)
  ElMessage.success('商品二维码已生成')
}

async function openQrcodePreview(qrcode: Qrcode) {
  closeQrcodePreview()
  currentQrcode.value = qrcode
  qrcodePreviewVisible.value = true
  qrcodePreviewUrl.value = buildQrcodePreviewUrl(qrcode)
}

function closeQrcodePreview() {
  if (qrcodePreviewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(qrcodePreviewUrl.value)
  }
  qrcodePreviewUrl.value = ''
  currentQrcodeBlob.value = null
  currentQrcode.value = null
}

function buildQrcodePreviewUrl(qrcode: Qrcode): string {
  if (!qrcode.image_url) return ''
  const version = encodeURIComponent(qrcode.generated_at || qrcode.updated_at || qrcode.short_code || String(qrcode.id))
  const separator = qrcode.image_url.includes('?') ? '&' : '?'
  return `${qrcode.image_url}${separator}v=${version}`
}

async function downloadCurrentQrcode() {
  if (!currentQrcode.value) return
  if (!currentQrcodeBlob.value) {
    const res = await downloadQrcode(currentQrcode.value.id)
    currentQrcodeBlob.value = res.data as Blob
  }
  downloadFile(currentQrcodeBlob.value, `${currentQrcode.value.short_code || currentQrcode.value.id}-transparent.png`)
}

watch(
  () => route.query.product_group,
  (group) => {
    applyProductGroup(group)
    handleSearch()
  },
)

onMounted(() => {
  applyProductGroup(route.query.product_group)
  fetchData()
})
</script>

<style lang="scss" scoped>
.top-toolbar {
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.type-toolbar {
  margin-bottom: 16px;
}

.product-info {
  display: flex;
  align-items: center;
  gap: 14px;

  .product-cover {
    width: 52px;
    height: 52px;
    border-radius: var(--radius-small);
    flex-shrink: 0;
    box-shadow: var(--shadow-light);
  }

  .image-placeholder {
    width: 52px;
    height: 52px;
    background: linear-gradient(135deg, var(--color-bg), var(--color-bg-warm));
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-placeholder);
    border-radius: var(--radius-small);
    border: 1px solid var(--color-border-light);
  }

  .product-name {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--color-text);
    letter-spacing: 0.3px;
  }

  .tag-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
}

.price {
  font-weight: 700;
  color: var(--color-accent);
  letter-spacing: 0.5px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}

.qrcode-preview {
  text-align: center;

  &__image {
    width: 240px;
    height: 240px;
    object-fit: contain;
    border: 1px solid var(--color-border-light);
    border-radius: 12px;
    background: #fff;
  }

  &__title {
    margin-top: 12px;
    font-weight: 700;
    color: var(--color-text);
  }

  &__meta {
    margin-top: 6px;
    font-size: 12px;
    color: var(--color-text-placeholder);
    word-break: break-all;
  }
}

@media (max-width: 720px) {
  .search-bar {
    width: 100%;
  }
}
</style>
