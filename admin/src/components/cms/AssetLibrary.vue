<template>
  <el-dialog
    :model-value="visible"
    title="素材库"
    width="720px"
    aria-label="素材库"
    @update:model-value="emit('update:visible', $event)"
    @close="emit('update:visible', false)"
  >
    <!-- 顶部操作栏 -->
    <div class="asset-toolbar">
      <el-upload
        :show-file-list="false"
        :before-upload="handleBeforeUpload"
        :http-request="handleUpload"
        :accept="acceptType"
      >
        <el-button type="primary" :loading="uploading">
          <el-icon><Upload /></el-icon>上传{{ fileTypeLabel }}
        </el-button>
      </el-upload>

      <el-select v-model="filterFileType" placeholder="全部类型" clearable style="width: 120px" @change="fetchAssets">
        <el-option label="图片" value="image" />
        <el-option label="视频" value="video" />
      </el-select>
    </div>

    <!-- 素材网格 -->
    <div v-loading="loading" class="asset-grid">
      <div
        v-for="asset in assetList"
        :key="asset.id"
        class="asset-item"
        :class="{ 'is-selected': selectedIds.has(asset.id) }"
        @click="toggleSelect(asset)"
      >
        <!-- 图片缩略图 -->
        <template v-if="asset.file_type === 'image'">
          <img :src="asset.file_url" :alt="asset.file_name" class="asset-thumb" @error="onImageError" />
        </template>
        <!-- 视频缩略图 -->
        <template v-else>
          <div class="video-thumb">
            <el-icon :size="28"><VideoCamera /></el-icon>
          </div>
        </template>

        <!-- 文件名 -->
        <div class="asset-name" :title="asset.file_name">{{ asset.file_name }}</div>

        <!-- 选中标记 -->
        <div v-if="selectedIds.has(asset.id)" class="select-badge">
          <el-icon><Check /></el-icon>
        </div>

        <!-- 删除按钮 -->
        <div class="asset-delete" role="button" aria-label="删除素材" @click.stop="handleDeleteAsset(asset)">
          <el-icon><Delete /></el-icon>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && assetList.length === 0" class="asset-empty">
        <el-empty description="暂无素材，请上传" :image-size="80" />
      </div>
    </div>

    <!-- 分页 -->
    <div class="asset-pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        small
        background
        @current-change="fetchAssets"
      />
    </div>

    <template #footer>
      <span class="selected-count">已选 {{ selectedIds.size }} 个</span>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :disabled="selectedIds.size === 0" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Upload, VideoCamera, Check, Delete } from '@element-plus/icons-vue'
import { getCmsAssets, uploadCmsAsset, deleteCmsAsset } from '@/api/cms'
import type { CmsAsset } from '@/types/cms'

const props = defineProps<{
  visible: boolean
  fileType?: 'image' | 'video'
  multiple?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', assets: CmsAsset[]): void
  (e: 'update:visible', value: boolean): void
}>()

// ---- 数据 ----
const loading = ref(false)
const uploading = ref(false)
const assetList = ref<CmsAsset[]>([])
const page = ref(1)
const pageSize = 12
const total = ref(0)
const filterFileType = ref(props.fileType || '')
const selectedIds = ref<Set<number>>(new Set())
const selectedAssets = ref<CmsAsset[]>([])

// 文件类型相关
const fileTypeLabel = computed(() => {
  if (filterFileType.value === 'image' || props.fileType === 'image') return '图片'
  if (filterFileType.value === 'video' || props.fileType === 'video') return '视频'
  return '文件'
})

const acceptType = computed(() => {
  if (props.fileType === 'image') return 'image/*'
  if (props.fileType === 'video') return 'video/*'
  return 'image/*,video/*'
})

// 打开弹窗时加载数据
watch(() => props.visible, (val) => {
  if (val) {
    filterFileType.value = props.fileType || ''
    selectedIds.value = new Set()
    selectedAssets.value = []
    page.value = 1
    fetchAssets()
  }
})

// 获取素材列表
async function fetchAssets() {
  loading.value = true
  try {
    const res = await getCmsAssets({
      page: page.value,
      page_size: pageSize,
      file_type: filterFileType.value || undefined,
    })
    assetList.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    // 错误由拦截器处理
  } finally {
    loading.value = false
  }
}

// 选中/取消
function toggleSelect(asset: CmsAsset) {
  if (props.multiple) {
    if (selectedIds.value.has(asset.id)) {
      selectedIds.value.delete(asset.id)
      selectedAssets.value = selectedAssets.value.filter(a => a.id !== asset.id)
    } else {
      selectedIds.value.add(asset.id)
      selectedAssets.value.push(asset)
    }
  } else {
    // 单选
    selectedIds.value = new Set([asset.id])
    selectedAssets.value = [asset]
  }
}

// 上传前校验
function handleBeforeUpload(file: File) {
  const isImage = file.type.startsWith('image/')
  const isVideo = file.type.startsWith('video/')

  if (props.fileType === 'image' && !isImage) {
    ElMessage.error('请上传图片文件')
    return false
  }
  if (props.fileType === 'video' && !isVideo) {
    ElMessage.error('请上传视频文件')
    return false
  }

  // 图片 10MB 限制
  if (isImage && file.size > 10 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 10MB')
    return false
  }
  // 视频 100MB 限制
  if (isVideo && file.size > 100 * 1024 * 1024) {
    ElMessage.error('视频大小不能超过 100MB')
    return false
  }

  return true
}

// 上传素材
async function handleUpload({ file }: { file: File }) {
  uploading.value = true
  try {
    await uploadCmsAsset(file)
    ElMessage.success('上传成功')
    fetchAssets()
  } catch {
    // 错误由拦截器处理
  } finally {
    uploading.value = false
  }
}

// 删除素材
async function handleDeleteAsset(asset: CmsAsset) {
  try {
    await ElMessageBox.confirm(`确定删除素材「${asset.file_name}」？`, '确认删除', {
      type: 'warning',
    })
    await deleteCmsAsset(asset.id)
    ElMessage.success('删除成功')
    fetchAssets()
  } catch {
    // 取消或错误
  }
}

// 确认选择
function handleConfirm() {
  emit('select', [...selectedAssets.value])
  emit('update:visible', false)
}

// 图片加载失败处理
function onImageError(e: Event) {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
  // 显示一个占位背景
  const parent = img.parentElement
  if (parent) {
    parent.style.background = '#f5f7fa'
    parent.style.display = 'flex'
    parent.style.alignItems = 'center'
    parent.style.justifyContent = 'center'
  }
}
</script>

<style lang="scss" scoped>
.asset-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  min-height: 200px;
}

.asset-item {
  position: relative;
  border: 2px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  aspect-ratio: 1;

  &:hover {
    border-color: var(--color-primary, #2d4a3e);
  }

  &.is-selected {
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 1px var(--el-color-primary);
  }
}

.asset-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-thumb {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
}

.asset-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px 6px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.select-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.asset-delete {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
  cursor: pointer;

  .asset-item:hover & {
    opacity: 1;
  }

  &:hover {
    background: var(--el-color-danger);
  }
}

.asset-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 0;
  color: #c0c4cc;
  font-size: 14px;
}

.asset-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.selected-count {
  float: left;
  line-height: 32px;
  color: #909399;
  font-size: 13px;
}
</style>
