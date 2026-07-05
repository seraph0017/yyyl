<template>
  <div class="page-container">
    <div class="card-box cloud-files">
      <div class="cloud-files__header">
        <div>
          <h3>云文件</h3>
          <p>集中管理图库、二维码源文件和导出数据；图片 URL 可复制后用于外网引用。</p>
        </div>
        <div class="cloud-files__actions">
          <el-upload
            accept="image/*"
            :show-file-list="false"
            :before-upload="beforeImageUpload"
            :http-request="handleImageUpload"
          >
            <el-button type="primary" :loading="uploading">上传图片</el-button>
          </el-upload>
          <el-button @click="exportCampsiteInfo">导出营位信息</el-button>
          <el-button @click="fetchData">刷新</el-button>
        </div>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="图库" name="images">
          <div v-loading="assetLoading" class="asset-grid">
            <div v-for="asset in assets" :key="asset.id" class="asset-card">
              <el-image :src="asset.file_url" fit="cover" class="asset-card__image" :preview-src-list="[asset.file_url]" />
              <div class="asset-card__body">
                <div class="asset-card__name" :title="asset.file_name">{{ asset.file_name }}</div>
                <div class="asset-card__meta">{{ formatFileSize(asset.file_size) }}</div>
                <el-input :model-value="asset.file_url" readonly size="small" />
                <div class="asset-card__actions">
                  <el-button link type="primary" @click="copyUrl(asset.file_url)">复制 URL</el-button>
                  <el-button link @click="downloadByUrl(asset.file_url, asset.file_name)">下载源文件</el-button>
                  <el-popconfirm title="确认删除该云文件？" @confirm="handleDeleteAsset(asset.id)">
                    <template #reference>
                      <el-button link type="danger">删除</el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </div>
            <el-empty v-if="!assetLoading && assets.length === 0" description="暂无图片" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="二维码源文件" name="qrcodes">
          <el-table :data="qrcodeAssets" v-loading="qrcodeLoading" stripe>
            <el-table-column prop="file_name" label="文件名" min-width="180" />
            <el-table-column prop="file_url" label="源文件 URL" min-width="220" show-overflow-tooltip />
            <el-table-column prop="created_at" label="归档时间" width="180" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="copyUrl(row.file_url || '')">复制 URL</el-button>
                <el-button link @click="downloadByUrl(row.file_url, row.file_name)">下载 PNG</el-button>
                <el-popconfirm title="确认删除该二维码源文件？" @confirm="handleDeleteAsset(row.id, 'qrcode')">
                  <template #reference>
                    <el-button link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!qrcodeLoading && qrcodeAssets.length === 0" description="暂无二维码源文件" />
        </el-tab-pane>

        <el-tab-pane label="导出数据" name="exports">
          <el-alert
            title="当前支持导出营位商品基础信息。后续订单/运营导出文件也会集中显示在这里。"
            type="info"
            show-icon
            :closable="false"
          />
          <div class="export-actions">
            <el-button type="primary" :loading="exporting" @click="exportCampsiteInfo">导出营位信息 CSV</el-button>
          </div>
          <el-table :data="exportAssets" v-loading="exportLoading" stripe class="export-table">
            <el-table-column prop="file_name" label="文件名" min-width="220" />
            <el-table-column prop="file_url" label="文件 URL" min-width="260" show-overflow-tooltip />
            <el-table-column prop="created_at" label="导出时间" width="180" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="copyUrl(row.file_url)">复制 URL</el-button>
                <el-button link @click="downloadByUrl(row.file_url, row.file_name)">下载 CSV</el-button>
                <el-popconfirm title="确认删除该导出文件？" @confirm="handleDeleteAsset(row.id, 'export')">
                  <template #reference>
                    <el-button link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!exportLoading && exportAssets.length === 0" description="暂无导出文件" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { getCmsAssets, uploadCmsAsset, deleteCmsAsset, exportCampsiteInfoAsset } from '@/api/cms'
import { createUploadRequestError, formatFileSize } from '@/utils'
import type { CmsAsset } from '@/types/cms'

const activeTab = ref('images')
const assets = ref<CmsAsset[]>([])
const qrcodeAssets = ref<CmsAsset[]>([])
const exportAssets = ref<CmsAsset[]>([])
const assetLoading = ref(false)
const qrcodeLoading = ref(false)
const exportLoading = ref(false)
const uploading = ref(false)
const exporting = ref(false)

function beforeImageUpload(file: File) {
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请上传图片文件')
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 10MB')
    return false
  }
  return true
}

async function fetchAssets() {
  assetLoading.value = true
  try {
    const res = await getCmsAssets({ page: 1, page_size: 100, file_type: 'image' })
    assets.value = res.data.list || []
  } finally {
    assetLoading.value = false
  }
}

async function fetchQrcodes() {
  qrcodeLoading.value = true
  try {
    const res = await getCmsAssets({ page: 1, page_size: 100, file_type: 'qrcode' })
    qrcodeAssets.value = res.data.list || []
  } finally {
    qrcodeLoading.value = false
  }
}

async function fetchExports() {
  exportLoading.value = true
  try {
    const res = await getCmsAssets({ page: 1, page_size: 100, file_type: 'export' })
    exportAssets.value = res.data.list || []
  } finally {
    exportLoading.value = false
  }
}

async function fetchData() {
  await Promise.all([fetchAssets(), fetchQrcodes(), fetchExports()])
}

async function handleImageUpload(options: UploadRequestOptions) {
  uploading.value = true
  try {
    const res = await uploadCmsAsset(options.file as File)
    options.onSuccess?.(res.data)
    ElMessage.success('图片已上传到云文件')
    await fetchAssets()
  } catch (error) {
    options.onError?.(createUploadRequestError(error, options))
    throw error
  } finally {
    uploading.value = false
  }
}

async function copyUrl(url: string) {
  if (!url) {
    ElMessage.warning('暂无 URL')
    return
  }
  const absoluteUrl = new URL(url, window.location.origin).href
  await navigator.clipboard.writeText(absoluteUrl)
  ElMessage.success('URL 已复制')
}

function downloadByUrl(url: string, filename: string) {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

async function handleDeleteAsset(id: number, fileType: 'image' | 'qrcode' | 'export' = 'image') {
  await deleteCmsAsset(id)
  ElMessage.success('已删除')
  if (fileType === 'qrcode') {
    await fetchQrcodes()
  } else if (fileType === 'export') {
    await fetchExports()
  } else {
    await fetchAssets()
  }
}

async function exportCampsiteInfo() {
  exporting.value = true
  try {
    const res = await exportCampsiteInfoAsset()
    ElMessage.success('营位信息已导出到云文件')
    await fetchExports()
    if (res.data?.file_url) {
      downloadByUrl(res.data.file_url, res.data.file_name)
    }
  } finally {
    exporting.value = false
  }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.cloud-files {
  &__header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    margin-bottom: 18px;

    h3 {
      margin: 0 0 6px;
    }

    p {
      margin: 0;
      color: var(--color-text-secondary);
      font-size: 13px;
    }
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  min-height: 220px;
}

.asset-card {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;

  &__image {
    width: 100%;
    height: 150px;
    background: var(--color-bg-warm);
  }

  &__body {
    padding: 12px;
  }

  &__name {
    font-weight: 600;
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__meta {
    margin: 4px 0 8px;
    color: var(--color-text-placeholder);
    font-size: 12px;
  }

  &__actions {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
  }
}

.export-actions {
  margin-top: 18px;
}

@media (max-width: 720px) {
  .cloud-files__header {
    flex-direction: column;
  }
}
</style>
