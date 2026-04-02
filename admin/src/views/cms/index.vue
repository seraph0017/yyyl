<template>
  <div class="cms-page-list">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-bar__left">
        <el-select v-model="filterType" placeholder="页面类型" clearable style="width: 140px">
          <el-option label="首页" value="home" />
          <el-option label="活动" value="activity" />
          <el-option label="促销" value="promotion" />
          <el-option label="自定义" value="custom" />
          <el-option label="宣传页" value="landing" />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="搜索页面标题/标识"
          clearable
          style="width: 220px"
          @keyup.enter="fetchList"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>新建页面
      </el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="pageList" v-loading="loading" stripe>
      <template #empty>
        <el-empty description="暂无页面数据">
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>新建页面
          </el-button>
        </el-empty>
      </template>
      <el-table-column prop="page_code" label="页面标识" width="150" />
      <el-table-column prop="title" label="页面标题" min-width="180" />
      <el-table-column label="页面类型" width="110">
        <template #default="{ row }">
          <el-tag :type="pageTypeTag(row.page_type).type" size="small">
            {{ pageTypeTag(row.page_type).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发布状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.current_version_id ? 'success' : 'info'" size="small">
            {{ row.current_version_id ? '已发布' : '未发布' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="草稿更新" width="170">
        <template #default="{ row }">
          {{ row.draft_updated_at ? formatTime(row.draft_updated_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="goEditor(row.id)">
            <el-icon><Edit /></el-icon>编辑
          </el-button>
          <el-button type="success" link size="small" @click="showLinkDialog(row)">
            <el-icon><Link /></el-icon>链接
          </el-button>
          <el-button type="warning" link size="small" @click="openSettingDialog(row)">
            <el-icon><Setting /></el-icon>设置
          </el-button>
          <el-button
            v-if="row.current_version_id || row.draft_config"
            type="info"
            link
            size="small"
            @click="handleReset(row)"
          >
            <el-icon><RefreshLeft /></el-icon>重置
          </el-button>
          <el-button
            v-if="row.page_type === 'custom'"
            type="danger"
            link
            size="small"
            @click="handleDelete(row)"
          >
            <el-icon><Delete /></el-icon>删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @size-change="fetchList"
        @current-change="fetchList"
      />
    </div>

    <!-- 新建页面弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建页面" width="480px" aria-label="新建页面" @closed="resetCreateForm">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="页面标识" prop="page_code">
          <el-input v-model="createForm.page_code" placeholder="英文标识，如 home / promo_001" />
        </el-form-item>
        <el-form-item label="页面类型" prop="page_type">
          <el-select v-model="createForm.page_type" style="width: 100%">
            <el-option label="首页" value="home" />
            <el-option label="活动" value="activity" />
            <el-option label="促销" value="promotion" />
            <el-option label="自定义" value="custom" />
            <el-option label="宣传页" value="landing" />
          </el-select>
        </el-form-item>
        <el-form-item label="页面标题" prop="title">
          <el-input v-model="createForm.title" placeholder="页面标题" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="页面描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 设置弹窗 -->
    <el-dialog v-model="showSettingDialog" title="页面设置" width="480px" aria-label="页面设置">
      <el-form ref="settingFormRef" :model="settingForm" :rules="settingRules" label-width="90px">
        <el-form-item label="页面标题" prop="title">
          <el-input v-model="settingForm.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="settingForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="settingForm.status"
            active-value="active"
            inactive-value="inactive"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="settingForm.sort_order" :min="0" :max="9999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettingDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleUpdateSetting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 链接弹窗 -->
    <el-dialog v-model="linkDialogVisible" title="页面链接" width="560px" aria-label="页面链接">
      <div class="link-info" v-if="linkTarget">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="页面标识">
            <el-tag size="small">{{ linkTarget.page_code }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="小程序页面路径">
            <div class="link-row">
              <code class="link-path">{{ miniappPath }}</code>
              <el-button type="primary" size="small" @click="copyText(miniappPath)">
                <el-icon><CopyDocument /></el-icon>复制
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="C端 API 地址">
            <div class="link-row">
              <code class="link-path">{{ cEndApiUrl }}</code>
              <el-button type="primary" size="small" @click="copyText(cEndApiUrl)">
                <el-icon><CopyDocument /></el-icon>复制
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="linkTarget.current_version_id ? 'success' : 'warning'" size="small">
              {{ linkTarget.current_version_id ? '已发布 — 小程序可访问' : '未发布 — 小程序将显示默认页面' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="linkTarget.page_code === 'home'"
          type="info"
          :closable="false"
          style="margin-top: 12px"
        >
          <template #title>
            <strong>首页说明：</strong>小程序首页自动读取 page_code 为 <code>home</code> 的配置。
            发布后小程序刷新即可看到变化。未发布时显示默认硬编码首页。
          </template>
        </el-alert>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus, Edit, Setting, Delete, Link, RefreshLeft, CopyDocument } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { getCmsPages, createCmsPage, updateCmsPage, deleteCmsPage, resetCmsPage } from '@/api/cms'
import type { CmsPage } from '@/types/cms'
import dayjs from 'dayjs'

const router = useRouter()

// ---- 列表数据 ----
const loading = ref(false)
const pageList = ref<CmsPage[]>([])
const filterType = ref('')
const keyword = ref('')
const pagination = reactive({ page: 1, page_size: 10, total: 0 })

// ---- 页面类型标签映射 ----
function pageTypeTag(type: string) {
  const map: Record<string, { label: string; type: '' | 'success' | 'warning' | 'danger' | 'info' }> = {
    home: { label: '首页', type: 'success' },
    activity: { label: '活动', type: 'warning' },
    promotion: { label: '促销', type: 'danger' },
    custom: { label: '自定义', type: 'info' },
    landing: { label: '宣传页', type: '' },
  }
  return map[type] || { label: type, type: 'info' }
}

// ---- 时间格式化 ----
function formatTime(str: string) {
  return dayjs(str).format('YYYY-MM-DD HH:mm')
}

// ---- 获取列表 ----
async function fetchList() {
  loading.value = true
  try {
    const res = await getCmsPages({
      page: pagination.page,
      page_size: pagination.page_size,
      page_type: filterType.value || undefined,
    })
    pageList.value = res.data.list
    pagination.total = res.data.pagination.total
  } catch {
    // 错误由拦截器处理
  } finally {
    loading.value = false
  }
}

// ---- 跳转编辑器 ----
function goEditor(id: number) {
  router.push({ name: 'CmsEditor', params: { id } })
}

// ---- 新建页面 ----
const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive({
  page_code: '',
  page_type: 'custom',
  title: '',
  description: '',
})
const createRules: FormRules = {
  page_code: [{ required: true, message: '请输入页面标识', trigger: 'blur' }],
  page_type: [{ required: true, message: '请选择页面类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入页面标题', trigger: 'blur' }],
}

function resetCreateForm() {
  createForm.page_code = ''
  createForm.page_type = 'custom'
  createForm.title = ''
  createForm.description = ''
  createFormRef.value?.clearValidate()
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await createCmsPage({
      page_code: createForm.page_code,
      page_type: createForm.page_type,
      title: createForm.title,
      description: createForm.description || undefined,
    })
    ElMessage.success('页面创建成功')
    showCreateDialog.value = false
    fetchList()
  } catch {
    // 错误由拦截器处理
  } finally {
    creating.value = false
  }
}

// ---- 设置弹窗 ----
const showSettingDialog = ref(false)
const saving = ref(false)
const settingFormRef = ref<FormInstance>()
const settingPageId = ref(0)
const settingForm = reactive({
  title: '',
  description: '',
  status: 'active' as string,
  sort_order: 0,
})
const settingRules: FormRules = {
  title: [{ required: true, message: '请输入页面标题', trigger: 'blur' }],
}

function openSettingDialog(page: CmsPage) {
  settingPageId.value = page.id
  settingForm.title = page.title
  settingForm.description = page.description || ''
  settingForm.status = page.status
  settingForm.sort_order = page.sort_order
  showSettingDialog.value = true
}

async function handleUpdateSetting() {
  const valid = await settingFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await updateCmsPage(settingPageId.value, {
      title: settingForm.title,
      description: settingForm.description || undefined,
      status: settingForm.status as CmsPage['status'],
      sort_order: settingForm.sort_order,
    })
    ElMessage.success('设置已保存')
    showSettingDialog.value = false
    fetchList()
  } catch {
    // 错误由拦截器处理
  } finally {
    saving.value = false
  }
}

// ---- 链接弹窗 ----
const linkDialogVisible = ref(false)
const linkTarget = ref<CmsPage | null>(null)

const miniappPath = computed(() => {
  if (!linkTarget.value) return ''
  const code = linkTarget.value.page_code
  if (code === 'home') return '/pages/index/index'
  return `/pages/cms-page/index?page_code=${code}`
})

const cEndApiUrl = computed(() => {
  if (!linkTarget.value) return ''
  return `/api/v1/cms/pages/${linkTarget.value.page_code}`
})

function showLinkDialog(page: CmsPage) {
  linkTarget.value = page
  linkDialogVisible.value = true
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

// ---- 重置为默认 ----
async function handleReset(page: CmsPage) {
  try {
    await ElMessageBox.confirm(
      `确定将「${page.title}」重置为默认？\n\n这会清空草稿配置并取消当前发布版本，小程序端将显示默认硬编码首页。`,
      '重置确认',
      {
        type: 'warning',
        confirmButtonText: '确定重置',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
    await resetCmsPage(page.id)
    ElMessage.success('页面已重置为默认')
    fetchList()
  } catch {
    // 取消或接口错误
  }
}

// ---- 删除 ----
async function handleDelete(page: CmsPage) {
  try {
    await ElMessageBox.confirm(`确定删除页面「${page.title}」？此操作不可恢复`, '确认删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await deleteCmsPage(page.id)
    ElMessage.success('页面已删除')
    fetchList()
  } catch {
    // 取消或接口错误
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style lang="scss" scoped>
.cms-page-list {
  padding: 20px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  &__left {
    display: flex;
    gap: 12px;
  }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.link-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.link-path {
  flex: 1;
  padding: 4px 8px;
  background: var(--el-fill-color-lighter, #f5f7fa);
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  word-break: break-all;
}
</style>
