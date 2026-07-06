<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <div class="filter-bar">
          <el-select v-model="searchParams.target_type" placeholder="目标类型" clearable style="width: 160px" @change="handleSearch">
            <el-option v-for="(label, key) in targetTypeMap" :key="key" :label="label" :value="key" />
          </el-select>
          <el-select v-model="searchParams.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
          <el-input v-model="keyword" placeholder="标题 / 短码 / scene" clearable style="width: 240px" @keyup.enter="handleSearch" />
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>搜索
          </el-button>
        </div>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>生成二维码
        </el-button>
      </div>

      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column label="目标" min-width="180">
          <template #default="{ row }">
            <div>{{ targetTypeMap[row.target_type] }}</div>
            <div class="text-secondary">{{ row.target_key }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="channel" label="渠道" width="120" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="扫码次数" width="100" align="center">
          <template #default="{ row }">{{ row.usage_count }}</template>
        </el-table-column>
        <el-table-column label="最近扫码" width="170">
          <template #default="{ row }">{{ row.last_used_at ? formatDateTime(row.last_used_at) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="预览" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--view" circle size="small" @click="handlePreview(row)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="下载" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--download" circle size="small" @click="handleDownload(row)">
                  <el-icon><Download /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="row.status === 'active' ? '停用' : '启用'" placement="top" :show-after="400">
                <el-button
                  class="action-btn"
                  :class="row.status === 'active' ? 'action-btn--offline' : 'action-btn--online'"
                  circle size="small"
                  @click="handleToggleStatus(row)"
                >
                  <el-icon>
                    <TurnOff v-if="row.status === 'active'" />
                    <Open v-else />
                  </el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="重新生成" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--warning" circle size="small" @click="handleRegenerate(row)">
                  <el-icon><Refresh /></el-icon>
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

    <el-dialog v-model="showCreateDialog" title="生成二维码" width="520px" @closed="resetCreateForm">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="96px">
        <el-form-item label="目标类型" prop="target_type">
          <el-select v-model="createForm.target_type" style="width: 100%">
            <el-option v-for="(label, key) in targetTypeMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标标识" prop="target_key">
          <el-input v-model="createForm.target_key" placeholder="商品ID / 分类key / page_code" />
        </el-form-item>
        <el-form-item label="二维码标题" prop="title">
          <el-input v-model="createForm.title" placeholder="用于管理后台识别" />
        </el-form-item>
        <el-form-item label="渠道">
          <el-input v-model="createForm.channel" placeholder="default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" title="二维码预览" width="420px" destroy-on-close @closed="closePreview">
      <div class="qrcode-preview" v-if="previewQrcode">
        <img v-if="previewUrl" :src="previewUrl" alt="二维码" class="qrcode-preview__image" />
        <el-skeleton v-else animated :rows="4" />
        <div class="qrcode-preview__title">{{ previewQrcode.title }}</div>
        <div class="qrcode-preview__meta">路径：{{ previewQrcode.path }}</div>
        <div class="qrcode-preview__meta">scene：{{ previewQrcode.scene }}</div>
        <div class="qrcode-preview__meta">短码：{{ previewQrcode.short_code }}</div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!previewQrcode" @click="downloadPreviewQrcode">下载透明底 PNG</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Download, Open, Plus, Refresh, Search, TurnOff, View } from '@element-plus/icons-vue'
import { createQrcode, downloadQrcode, getQrcodes, regenerateQrcode, updateQrcodeStatus } from '@/api/qrcode'
import type { Qrcode, QrcodeSearchParams, QrcodeCreateRequest } from '@/types/qrcode'
import { downloadFile, formatDateTime } from '@/utils'

const loading = ref(false)
const tableData = ref<Qrcode[]>([])
const total = ref(0)
const keyword = ref('')
const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()
const previewVisible = ref(false)
const previewQrcode = ref<Qrcode | null>(null)
const previewBlob = ref<Blob | null>(null)
const previewUrl = ref('')

const targetTypeMap: Record<string, string> = {
  product: '商品',
  category: '分类',
  activity_product: '活动商品',
  activity_page: '活动页面',
  custom_page: '自定义页面',
}

const searchParams = reactive<QrcodeSearchParams>({
  page: 1,
  page_size: 20,
  target_type: undefined,
  channel: undefined,
  status: undefined,
})

const createForm = reactive<QrcodeCreateRequest>({
  target_type: 'product',
  target_key: '',
  title: '',
  channel: 'default',
})

const createRules: FormRules = {
  target_type: [{ required: true, message: '请选择目标类型', trigger: 'change' }],
  target_key: [{ required: true, message: '请输入目标标识', trigger: 'blur' }],
  title: [{ required: true, message: '请输入二维码标题', trigger: 'blur' }],
}

const searchKeyword = computed({
  get: () => keyword.value,
  set: (value: string) => { keyword.value = value },
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getQrcodes({
      page: searchParams.page,
      page_size: searchParams.page_size,
      target_type: searchParams.target_type,
      channel: searchParams.channel,
      status: searchParams.status,
    })
    const items = res.data.list || []
    const q = searchKeyword.value.trim().toLowerCase()
    tableData.value = q
      ? items.filter((item) =>
          [item.title, item.short_code, item.scene, item.target_key, item.channel]
            .filter(Boolean)
            .some((field) => String(field).toLowerCase().includes(q)),
        )
      : items
    total.value = res.data.pagination.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

function resetCreateForm() {
  createForm.target_type = 'product'
  createForm.target_key = ''
  createForm.title = ''
  createForm.channel = 'default'
  createFormRef.value?.clearValidate()
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    const res = await createQrcode(createForm)
    ElMessage.success('二维码已生成')
    showCreateDialog.value = false
    await openPreview(res.data)
    fetchData()
  } finally {
    creating.value = false
  }
}

async function handleToggleStatus(row: Qrcode) {
  const nextStatus = row.status === 'active' ? 'inactive' : 'active'
  await updateQrcodeStatus(row.id, nextStatus)
  row.status = nextStatus
  ElMessage.success(nextStatus === 'active' ? '已启用' : '已停用')
}

async function handleRegenerate(row: Qrcode) {
  await ElMessageBox.confirm(`确认重新生成二维码「${row.title}」？`, '重新生成', { type: 'warning' })
  const res = await regenerateQrcode(row.id)
  ElMessage.success('已重新生成')
  await openPreview(res.data)
  fetchData()
}

async function handleDownload(row: Qrcode) {
  const res = await downloadQrcode(row.id)
  downloadFile(res.data as Blob, `${row.short_code}.png`)
}

async function handlePreview(row: Qrcode) {
  await openPreview(row)
}

async function openPreview(row: Qrcode) {
  closePreview()
  previewQrcode.value = row
  previewVisible.value = true
  previewUrl.value = buildQrcodePreviewUrl(row)
}

function closePreview() {
  if (previewUrl.value.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  previewBlob.value = null
  previewQrcode.value = null
}

function buildQrcodePreviewUrl(qrcode: Qrcode): string {
  if (!qrcode.image_url) return ''
  const version = encodeURIComponent(qrcode.generated_at || qrcode.updated_at || qrcode.short_code || String(qrcode.id))
  const separator = qrcode.image_url.includes('?') ? '&' : '?'
  return `${qrcode.image_url}${separator}v=${version}`
}

async function downloadPreviewQrcode() {
  if (!previewQrcode.value) return
  if (!previewBlob.value) {
    const res = await downloadQrcode(previewQrcode.value.id)
    previewBlob.value = res.data as Blob
  }
  downloadFile(previewBlob.value, `${previewQrcode.value.short_code || previewQrcode.value.id}-transparent.png`)
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.text-secondary {
  font-size: 12px;
  color: var(--color-text-placeholder);
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
</style>
