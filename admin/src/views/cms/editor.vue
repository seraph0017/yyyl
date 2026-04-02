<template>
  <div class="cms-editor">
    <!-- 工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>返回
        </el-button>
        <el-divider direction="vertical" />
        <span class="page-title">{{ cmsStore.page?.title || '编辑器' }}</span>
        <el-tag v-if="cmsStore.readonly" type="warning" size="small">只读模式</el-tag>
      </div>
      <div class="toolbar-right">
        <!-- 撤销/重做 -->
        <el-tooltip content="撤销 (Ctrl+Z)">
          <el-button text :disabled="cmsStore.undoStack.length === 0 || cmsStore.readonly" aria-label="撤销" @click="cmsStore.undo()">
            <el-icon><RefreshLeft /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="重做 (Ctrl+Shift+Z)">
          <el-button text :disabled="cmsStore.redoStack.length === 0 || cmsStore.readonly" aria-label="重做" @click="cmsStore.redo()">
            <el-icon><RefreshRight /></el-icon>
          </el-button>
        </el-tooltip>

        <el-divider direction="vertical" />

        <!-- 保存草稿 -->
        <el-button :disabled="!cmsStore.isDirty || cmsStore.readonly" :loading="saving" @click="saveDraft">
          保存草稿
        </el-button>

        <!-- 预览 -->
        <el-button @click="handlePreview" :loading="previewing">预览</el-button>

        <!-- 版本管理 -->
        <el-button @click="versionVisible = true">版本</el-button>

        <!-- 发布 -->
        <el-tooltip v-if="!userStore.isSuperAdmin" content="仅超级管理员可发布页面" placement="bottom">
          <el-button type="primary" disabled>发布</el-button>
        </el-tooltip>
        <el-button v-else type="primary" :loading="publishing" :disabled="cmsStore.readonly" @click="handlePublish">
          发布
        </el-button>
      </div>
    </div>

    <!-- 三栏布局 -->
    <div v-if="pageLoading" class="editor-loading">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>加载页面数据中...</span>
    </div>
    <div v-else class="editor-body">
      <!-- 左侧组件面板 -->
      <div class="component-panel">
        <ComponentPanel @add="handleAddComponent" />
      </div>

      <!-- 中间画布 -->
      <CanvasArea
        :components="cmsStore.config.components"
        :selected-id="cmsStore.selectedComponentId"
        :page-settings="cmsStore.config.page_settings"
        :preview-mode="previewMode"
        @select="cmsStore.selectedComponentId = $event"
        @reorder="handleReorder"
      />

      <!-- 右侧属性面板 -->
      <div class="property-panel">
        <PropertyPanel
          :component="cmsStore.selectedComponent"
          :page-settings="cmsStore.config.page_settings"
          @update="handleComponentUpdate"
          @update-page-settings="handlePageSettingsUpdate"
        />
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="editor-status-bar">
      <span class="status-item">
        <template v-if="cmsStore.lastSavedAt">
          上次保存: {{ formatTime(cmsStore.lastSavedAt) }}
        </template>
        <template v-else>未保存</template>
      </span>
      <span class="status-item">
        组件: {{ cmsStore.componentCount }} / 30
        <el-tag v-if="cmsStore.componentCount >= 25" type="warning" size="small" style="margin-left: 4px">
          接近上限
        </el-tag>
      </span>
      <span class="status-item">
        <el-tag :type="cmsStore.readonly ? 'warning' : 'success'" size="small">
          {{ cmsStore.readonly ? '只读' : '编辑中' }}
        </el-tag>
      </span>
    </div>

    <!-- 版本管理弹窗 -->
    <VersionHistory
      v-model:visible="versionVisible"
      :page-id="pageId"
      :current-version-id="cmsStore.page?.current_version_id"
      @rollback="handleRollback"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, RefreshLeft, RefreshRight, Loading,
} from '@element-plus/icons-vue'
import { useCmsStore } from '@/stores/cms'
import { useUserStore } from '@/stores/user'
import {
  getCmsPageDetail, saveCmsDraft, publishCmsPage,
  acquireCmsLock, releaseCmsLock, rollbackCmsPage, createCmsPreview,
} from '@/api/cms'
import { getToken } from '@/utils/request'
import type { ComponentItem, CmsConfig } from '@/types/cms'
import ComponentPanel from '@/components/cms/ComponentPanel.vue'
import CanvasArea from '@/components/cms/CanvasArea.vue'
import PropertyPanel from '@/components/cms/PropertyPanel.vue'
import VersionHistory from '@/components/cms/VersionHistory.vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const cmsStore = useCmsStore()
const userStore = useUserStore()

const pageId = Number(route.params.id)
const previewMode = ref<'mobile' | 'desktop'>('mobile')
const saving = ref(false)
const publishing = ref(false)
const previewing = ref(false)
const versionVisible = ref(false)
const pageLoading = ref(true)

let autoSaveTimer: ReturnType<typeof setInterval> | null = null
let heartbeatTimer: ReturnType<typeof setInterval> | null = null

// 时间格式化
function formatTime(str: string) {
  return dayjs(str).format('HH:mm:ss')
}

// ---- 返回列表 ----
function goBack() {
  if (cmsStore.isDirty) {
    ElMessageBox.confirm('有未保存的更改，确定离开？', '提示', {
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑',
      type: 'warning',
    }).then(() => {
      router.push({ name: 'CmsPages' })
    }).catch(() => {})
  } else {
    router.push({ name: 'CmsPages' })
  }
}

// ---- 添加组件 ----
function handleAddComponent(componentType: string) {
  if (cmsStore.readonly) return
  // 从 ComponentPanel 的分组定义查找默认属性
  const allGroups = [
    { type: 'banner', defaultProps: { images: [], interval: 5, indicator_style: 'dot', autoplay: true, border_radius: 0 } },
    { type: 'image', defaultProps: { url: '', link: { type: 'none', target: '', title: '' }, mode: 'widthFix', width: '100%' } },
    { type: 'image_text', defaultProps: { layout: 'left-right', image_url: '', title: '标题文字', description: '描述文字', link: { type: 'none', target: '', title: '' }, title_color: '#333333', desc_color: '#999999' } },
    { type: 'notice', defaultProps: { texts: ['欢迎来到一月一露营地'], speed: 50, background_color: '#FFF9E6', text_color: '#FF6600', icon: '' } },
    { type: 'nav', defaultProps: { items: [], columns: 4, show_label: true } },
    { type: 'video', defaultProps: { url: '', poster: '', autoplay: false, loop: false } },
    { type: 'product_list', defaultProps: { source: 'manual', product_ids: [], count: 6, layout: 'grid', columns: 2 } },
    { type: 'coupon', defaultProps: { coupon_ids: [], layout: 'horizontal' } },
    { type: 'rich_text', defaultProps: { content: '<p>请输入内容</p>' } },
    { type: 'spacer', defaultProps: { height: 20 } },
    { type: 'divider', defaultProps: { style: 'solid', color: '#EEEEEE', margin: 16 } },
  ]
  const def = allGroups.find(g => g.type === componentType)
  if (def) {
    cmsStore.addComponent(componentType, def.defaultProps)
  }
}

// ---- 重排序 ----
function handleReorder(newList: ComponentItem[]) {
  if (cmsStore.readonly) return
  cmsStore.pushSnapshot()
  cmsStore.config.components = newList
}

// ---- 组件属性更新 ----
function handleComponentUpdate(componentId: string, updates: Partial<ComponentItem>) {
  if (cmsStore.readonly) return
  if (updates.props) {
    cmsStore.updateComponentProps(componentId, updates.props)
  }
  if (updates.style) {
    cmsStore.updateComponentStyle(componentId, updates.style)
  }
}

// ---- 页面设置更新 ----
function handlePageSettingsUpdate(settings: Partial<CmsConfig['page_settings']>) {
  if (cmsStore.readonly) return
  cmsStore.pushSnapshot()
  cmsStore.config.page_settings = { ...cmsStore.config.page_settings, ...settings }
}

// ---- 保存草稿 ----
async function saveDraftAction() {
  if (!cmsStore.isDirty || !cmsStore.page || cmsStore.readonly) return
  saving.value = true
  try {
    const res = await saveCmsDraft(cmsStore.page.id, {
      config: cmsStore.config,
      draft_updated_at: cmsStore.page.draft_updated_at,
    })
    // 更新乐观锁时间戳为服务端返回值
    cmsStore.page!.draft_updated_at = res.data.draft_updated_at
    cmsStore.isDirty = false
    cmsStore.lastSavedAt = new Date().toISOString()
    ElMessage.success('草稿已保存')
  } catch (err: any) {
    if (err.response?.status === 409) {
      ElMessageBox.alert('页面已被他人修改，请刷新后重试', '保存冲突')
    }
  } finally {
    saving.value = false
  }
}

async function saveDraft() {
  await saveDraftAction()
}

// ---- 发布 ----
async function handlePublish() {
  if (cmsStore.readonly) return
  try {
    const { value: remark } = await ElMessageBox.prompt('请输入发布备注（可选）', '发布确认', {
      confirmButtonText: '发布',
      cancelButtonText: '取消',
      inputPlaceholder: '版本备注',
    })
    // 先保存草稿
    if (cmsStore.isDirty) {
      await saveDraftAction()
    }
    publishing.value = true
    const res = await publishCmsPage(pageId, { remark: remark || undefined })
    ElMessage.success(`发布成功，版本号 V${res.data.version_number}`)
    // 刷新页面数据
    loadPageData()
  } catch {
    // 取消或错误
  } finally {
    publishing.value = false
  }
}

// ---- 预览 ----
async function handlePreview() {
  previewing.value = true
  try {
    const res = await createCmsPreview(pageId)
    window.open(res.data.preview_url, '_blank')
  } catch {
    // 错误由拦截器处理
  } finally {
    previewing.value = false
  }
}

// ---- 版本回滚 ----
async function handleRollback(versionId: number) {
  try {
    await rollbackCmsPage(pageId, { version_id: versionId })
    ElMessage.success('回滚成功')
    versionVisible.value = false
    loadPageData()
  } catch {
    // 错误由拦截器处理
  }
}

// ---- 加载页面数据 ----
async function loadPageData() {
  pageLoading.value = true
  try {
    const res = await getCmsPageDetail(pageId)
    cmsStore.initFromPage(res.data)
    // 根据页面类型设置预览模式
    if (res.data.page_type === 'landing') {
      previewMode.value = 'desktop'
    }
  } catch {
    ElMessage.error('加载页面数据失败')
    router.push({ name: 'CmsPages' })
  } finally {
    pageLoading.value = false
  }
}

// ---- 快捷键 ----
function handleKeydown(e: KeyboardEvent) {
  if (cmsStore.readonly) return

  if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
    e.preventDefault()
    cmsStore.undo()
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
    e.preventDefault()
    cmsStore.redo()
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    saveDraft()
  }
  // 复制选中组件到剪贴板
  if ((e.ctrlKey || e.metaKey) && e.key === 'c' && cmsStore.selectedComponentId) {
    e.preventDefault()
    cmsStore.copyToClipboard(cmsStore.selectedComponentId)
  }
  // 粘贴剪贴板中的组件
  if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
    e.preventDefault()
    cmsStore.pasteFromClipboard()
  }
  if (e.key === 'Delete' && cmsStore.selectedComponentId) {
    cmsStore.removeComponent(cmsStore.selectedComponentId)
  }
}

// ---- 编辑锁释放（页面关闭/刷新时） ----
function handleBeforeUnload() {
  const url = `/api/v1/admin/cms/pages/${pageId}/lock`
  const token = getToken()
  const siteId = cmsStore.page?.site_id || 1
  fetch(url, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}`, 'X-Site-Id': String(siteId) },
    keepalive: true,
  }).catch(() => {})
}

// ---- 生命周期 ----
onMounted(async () => {
  // 获取编辑锁
  try {
    await acquireCmsLock(pageId)
  } catch (err: any) {
    if (err.response?.status === 423) {
      const lockInfo = err.response.data.detail?.data
      try {
        await ElMessageBox.confirm(
          `该页面正在被 ${lockInfo?.admin_name || '其他管理员'} 编辑中`,
          '编辑锁冲突',
          { confirmButtonText: '只读查看', cancelButtonText: '返回列表', type: 'warning' }
        )
        // 用户选择只读查看
        cmsStore.readonly = true
      } catch {
        // 用户选择返回列表
        router.back()
        return
      }
    }
  }

  // 加载页面数据
  await loadPageData()

  // 自动保存（60秒）
  autoSaveTimer = setInterval(saveDraftAction, 60000)

  // 心跳续期（2分钟）
  if (!cmsStore.readonly) {
    heartbeatTimer = setInterval(async () => {
      try {
        await acquireCmsLock(pageId)
      } catch { /* 静默失败 */ }
    }, 120000)
  }

  // 键盘事件
  document.addEventListener('keydown', handleKeydown)

  // 页面关闭事件
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(async () => {
  if (autoSaveTimer) clearInterval(autoSaveTimer)
  if (heartbeatTimer) clearInterval(heartbeatTimer)

  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('beforeunload', handleBeforeUnload)

  // 释放编辑锁
  if (!cmsStore.readonly) {
    try {
      await releaseCmsLock(pageId)
    } catch { /* 静默 */ }
  }

  cmsStore.$reset()
})
</script>

<style lang="scss" scoped>
.cms-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-color-page, #f0f2f5);
}

// 工具栏
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 52px;
  padding: 0 16px;
  background: var(--bg-color, #fff);
  border-bottom: 1px solid var(--border-color, #ebeef5);
  flex-shrink: 0;
  z-index: 10;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

// 三栏布局
.editor-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

// 加载状态
.editor-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 12px;
  color: var(--color-text-secondary, #909399);
  font-size: 14px;
}

// 左侧组件面板
.component-panel {
  width: 240px;
  background: var(--bg-color, #fff);
  border-right: 1px solid var(--border-color, #ebeef5);
  overflow-y: auto;
  flex-shrink: 0;
}

// 右侧属性面板
.property-panel {
  width: 320px;
  background: var(--bg-color, #fff);
  border-left: 1px solid var(--border-color, #ebeef5);
  overflow-y: auto;
  flex-shrink: 0;
}

// 底部状态栏
.editor-status-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 32px;
  padding: 0 16px;
  background: var(--bg-color, #fff);
  border-top: 1px solid var(--border-color, #ebeef5);
  flex-shrink: 0;
}

.status-item {
  font-size: 12px;
  color: var(--color-text-secondary, #909399);
}
</style>
