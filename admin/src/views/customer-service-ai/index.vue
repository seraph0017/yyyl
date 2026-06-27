<template>
  <div class="page-container customer-service-ai">
    <div class="page-header">
      <div>
        <h2>客服知识库</h2>
        <p>小程序智能客服与企业微信群助手共用同一套已发布知识。</p>
      </div>
      <div class="page-header__actions">
        <el-upload
          accept=".txt,.md,.pdf,.docx"
          :show-file-list="false"
          :before-upload="beforeKnowledgeUpload"
          :http-request="handleKnowledgeUpload"
        >
          <el-button :loading="uploading">
            <el-icon><Upload /></el-icon>导入文件
          </el-button>
        </el-upload>
        <el-button type="primary" @click="openArticleDialog()">
          <el-icon><Plus /></el-icon>新增知识
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="workspace-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="知识库" name="knowledge">
        <div class="toolbar">
          <el-input
            v-model.trim="articleParams.keyword"
            clearable
            placeholder="搜索标题或正文"
            style="width: 260px"
            @keyup.enter="fetchArticles"
            @clear="fetchArticles"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="articleParams.status" clearable placeholder="状态" style="width: 130px" @change="fetchArticles">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="已归档" value="archived" />
          </el-select>
          <el-button type="primary" @click="fetchArticles">查询</el-button>
          <el-button @click="resetArticleFilter">重置</el-button>
        </div>

        <el-table :data="articles" v-loading="articleLoading" stripe>
          <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
          <el-table-column label="来源" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ formatSourceType(row.source_type) }}</el-tag>
              <span class="source-name">{{ row.source_name || '手工录入' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="关键词" min-width="180">
            <template #default="{ row }">
              <div class="tag-line">
                <el-tag v-for="item in row.keywords" :key="item" size="small" type="info">{{ item }}</el-tag>
                <span v-if="!row.keywords?.length" class="muted">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ formatStatus(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-tooltip content="编辑" placement="top" :show-after="400">
                  <el-button class="action-btn action-btn--edit" circle size="small" @click="openArticleDialog(row)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top" :show-after="400">
                  <el-button class="action-btn action-btn--delete" circle size="small" @click="removeArticle(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="articleParams.page"
            v-model:page-size="articleParams.page_size"
            :total="articleTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchArticles"
            @current-change="fetchArticles"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="问答测试" name="ask">
        <div class="ask-panel">
          <div class="ask-panel__input">
            <el-input
              v-model.trim="askQuestion"
              type="textarea"
              :rows="5"
              maxlength="300"
              show-word-limit
              placeholder="输入用户可能提出的问题，系统只会基于已发布知识库回答。"
            />
            <el-button type="primary" :loading="asking" @click="submitAsk">
              <el-icon><ChatDotRound /></el-icon>测试回答
            </el-button>
          </div>
          <div class="ask-result" v-if="askResult">
            <div class="ask-result__head">
              <span>回答结果</span>
              <el-tag :type="askResult.needs_human ? 'warning' : 'success'" size="small">
                {{ askResult.needs_human ? '人工兜底' : '知识库命中' }}
              </el-tag>
            </div>
            <p>{{ askResult.answer }}</p>
            <div class="source-block">
              <span>来源引用</span>
              <div v-if="askResult.sources.length" class="tag-line">
                <el-tag v-for="source in askResult.sources" :key="source.id" type="success" effect="plain">
                  {{ source.title }}
                </el-tag>
              </div>
              <span v-else class="muted">无来源，已转人工客服确认。</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="问答日志" name="logs">
        <div class="toolbar">
          <el-select v-model="logParams.channel" clearable placeholder="渠道" style="width: 160px" @change="fetchLogs">
            <el-option label="小程序" value="miniapp" />
            <el-option label="后台测试" value="admin_preview" />
            <el-option label="企业微信" value="enterprise_wechat" />
          </el-select>
          <el-select v-model="needsHumanFilter" clearable placeholder="兜底状态" style="width: 150px" @change="handleNeedsHumanChange">
            <el-option label="人工兜底" value="true" />
            <el-option label="知识库命中" value="false" />
          </el-select>
          <el-button type="primary" @click="fetchLogs">查询</el-button>
          <el-button @click="resetLogFilter">重置</el-button>
        </div>

        <el-table :data="askLogs" v-loading="logLoading" stripe>
          <el-table-column label="问题" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.question }}</template>
          </el-table-column>
          <el-table-column label="渠道" width="110">
            <template #default="{ row }">{{ formatChannel(row.channel) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="row.needs_human ? 'warning' : 'success'" size="small">
                {{ row.needs_human ? '人工兜底' : '已命中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="来源引用" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              {{ formatSourceRefs(row.source_refs) }}
            </template>
          </el-table-column>
          <el-table-column label="反馈" width="100" align="center">
            <template #default="{ row }">
              <span>{{ row.feedback ? formatFeedback(row.feedback) : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="logParams.page"
            v-model:page-size="logParams.page_size"
            :total="logTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchLogs"
            @current-change="fetchLogs"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="articleDialogVisible" :title="editingArticle ? '编辑知识' : '新增知识'" :width="dialogWidth" @closed="resetArticleForm">
      <el-form ref="articleFormRef" :model="articleForm" :rules="articleRules" label-width="96px">
        <el-form-item label="标题" prop="title">
          <el-input v-model.trim="articleForm.title" maxlength="160" show-word-limit />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="articleForm.status">
            <el-radio-button label="draft">草稿</el-radio-button>
            <el-radio-button label="published">发布</el-radio-button>
            <el-radio-button label="archived">归档</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="关键词">
          <el-select
            v-model="articleForm.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词后回车"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="来源说明">
          <el-input v-model.trim="articleForm.source_name" placeholder="如：营地须知.md，可为空" />
        </el-form-item>
        <el-form-item label="正文" prop="content">
          <el-input v-model="articleForm.content" type="textarea" :rows="12" maxlength="12000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="articleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingArticle" @click="saveArticle">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadRequestOptions } from 'element-plus'
import { ChatDotRound, Delete, Edit, Plus, Search, Upload } from '@element-plus/icons-vue'
import {
  askCustomerServiceKnowledge,
  createKnowledgeArticle,
  deleteKnowledgeArticle,
  getCustomerServiceAskLogs,
  getKnowledgeArticles,
  updateKnowledgeArticle,
  uploadKnowledgeFile,
} from '@/api/customer-service-ai'
import type {
  CustomerServiceAskLog,
  CustomerServiceAskLogSearchParams,
  CustomerServiceAskResult,
  CustomerServiceFeedback,
  CustomerServiceKnowledgeArticle,
  CustomerServiceKnowledgePayload,
  CustomerServiceKnowledgeSource,
  CustomerServiceKnowledgeSearchParams,
  CustomerServiceKnowledgeSourceType,
  CustomerServiceKnowledgeStatus,
} from '@/types/customer-service-ai'

const activeTab = ref('knowledge')
const dialogWidth = 'min(760px, calc(100vw - 32px))'

const articles = ref<CustomerServiceKnowledgeArticle[]>([])
const articleLoading = ref(false)
const articleTotal = ref(0)
const articleParams = reactive<CustomerServiceKnowledgeSearchParams>({
  page: 1,
  page_size: 20,
  keyword: '',
  status: undefined,
})

const articleDialogVisible = ref(false)
const editingArticle = ref<CustomerServiceKnowledgeArticle | null>(null)
const savingArticle = ref(false)
const uploading = ref(false)
const articleFormRef = ref<FormInstance>()
const articleForm = reactive<CustomerServiceKnowledgePayload>({
  title: '',
  content: '',
  content_format: 'markdown',
  source_type: 'manual',
  source_name: '',
  keywords: [],
  status: 'draft',
})

const articleRules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入正文', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const askQuestion = ref('')
const asking = ref(false)
const askResult = ref<CustomerServiceAskResult | null>(null)

const askLogs = ref<CustomerServiceAskLog[]>([])
const logLoading = ref(false)
const logTotal = ref(0)
const needsHumanFilter = ref('')
const logParams = reactive<CustomerServiceAskLogSearchParams>({
  page: 1,
  page_size: 20,
  channel: undefined,
  needs_human: undefined,
})

const uploadStatus = computed<CustomerServiceKnowledgeStatus>(() => 'draft')

onMounted(() => {
  fetchArticles()
})

async function fetchArticles() {
  articleLoading.value = true
  try {
    const res = await getKnowledgeArticles(articleParams)
    articles.value = res.data.list
    articleTotal.value = res.data.pagination.total
  } finally {
    articleLoading.value = false
  }
}

function resetArticleFilter() {
  articleParams.page = 1
  articleParams.keyword = ''
  articleParams.status = undefined
  fetchArticles()
}

function openArticleDialog(row?: CustomerServiceKnowledgeArticle) {
  editingArticle.value = row || null
  if (row) {
    Object.assign(articleForm, {
      title: row.title,
      content: row.content,
      content_format: row.content_format,
      source_type: row.source_type,
      source_name: row.source_name || '',
      keywords: [...(row.keywords || [])],
      status: row.status,
    })
  } else {
    resetArticleForm()
  }
  articleDialogVisible.value = true
}

function resetArticleForm() {
  editingArticle.value = null
  Object.assign(articleForm, {
    title: '',
    content: '',
    content_format: 'markdown',
    source_type: 'manual',
    source_name: '',
    keywords: [],
    status: 'draft',
  })
  articleFormRef.value?.clearValidate()
}

async function saveArticle() {
  const valid = await articleFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingArticle.value = true
  try {
    const payload = normalizeArticlePayload()
    if (editingArticle.value) {
      await updateKnowledgeArticle(editingArticle.value.id, payload)
      ElMessage.success('知识已更新')
    } else {
      await createKnowledgeArticle(payload)
      ElMessage.success('知识已创建')
    }
    articleDialogVisible.value = false
    fetchArticles()
  } finally {
    savingArticle.value = false
  }
}

function normalizeArticlePayload(): CustomerServiceKnowledgePayload {
  return {
    title: articleForm.title,
    content: articleForm.content,
    content_format: articleForm.content_format,
    source_type: articleForm.source_type,
    source_name: articleForm.source_name || null,
    keywords: articleForm.keywords.filter(Boolean),
    status: articleForm.status,
  }
}

async function removeArticle(row: CustomerServiceKnowledgeArticle) {
  await ElMessageBox.confirm(`确认删除知识「${row.title}」？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await deleteKnowledgeArticle(row.id)
  ElMessage.success('知识已删除')
  fetchArticles()
}

async function handleKnowledgeUpload(options: UploadRequestOptions) {
  uploading.value = true
  try {
    await uploadKnowledgeFile(options.file as File, { status: uploadStatus.value })
    ElMessage.success('文件已导入知识库草稿')
    fetchArticles()
  } finally {
    uploading.value = false
  }
}

function beforeKnowledgeUpload(file: File) {
  const allowed = ['.txt', '.md', '.pdf', '.docx']
  const suffix = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!allowed.includes(suffix)) {
    ElMessage.error('知识库文件仅支持 txt/md/pdf/docx')
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('知识库文件不能超过10MB')
    return false
  }
  return true
}

async function submitAsk() {
  if (!askQuestion.value) {
    ElMessage.warning('请输入问题')
    return
  }
  asking.value = true
  try {
    const res = await askCustomerServiceKnowledge(askQuestion.value)
    askResult.value = res.data
    if (askResult.value.needs_human) {
      ElMessage.warning('未命中可靠来源，已进入人工兜底')
    }
  } finally {
    asking.value = false
  }
}

async function fetchLogs() {
  logLoading.value = true
  try {
    const res = await getCustomerServiceAskLogs(logParams)
    askLogs.value = res.data.list
    logTotal.value = res.data.pagination.total
  } finally {
    logLoading.value = false
  }
}

function handleNeedsHumanChange(value: string) {
  logParams.needs_human = value === '' ? undefined : value === 'true'
  fetchLogs()
}

function resetLogFilter() {
  logParams.page = 1
  logParams.channel = undefined
  logParams.needs_human = undefined
  needsHumanFilter.value = ''
  fetchLogs()
}

function handleTabChange(name: string | number) {
  if (name === 'logs' && askLogs.value.length === 0) fetchLogs()
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function formatStatus(status: CustomerServiceKnowledgeStatus) {
  const map = { draft: '草稿', published: '已发布', archived: '已归档' }
  return map[status] || status
}

function statusTagType(status: CustomerServiceKnowledgeStatus) {
  if (status === 'published') return 'success'
  if (status === 'archived') return 'info'
  return 'warning'
}

function formatSourceType(type: CustomerServiceKnowledgeSourceType) {
  const map = { manual: '手工', faq: 'FAQ', txt: 'TXT', md: 'Markdown', pdf: 'PDF', docx: 'DOCX' }
  return map[type] || type
}

function formatChannel(channel: string) {
  const map: Record<string, string> = { miniapp: '小程序', admin_preview: '后台测试', enterprise_wechat: '企业微信' }
  return map[channel] || channel
}

function formatFeedback(feedback: CustomerServiceFeedback) {
  return feedback === 'helpful' ? '有用' : '无用'
}

function formatSourceRefs(sources?: CustomerServiceKnowledgeSource[]) {
  return sources?.map(item => item.title).join('、') || '-'
}
</script>

<style scoped lang="scss">
.customer-service-ai {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 16px;

    h2 {
      margin: 0 0 6px;
      font-size: 22px;
      font-weight: 700;
      color: var(--color-text);
    }

    p {
      margin: 0;
      color: var(--color-text-secondary);
      font-size: 14px;
    }

    &__actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
    }
  }

  .workspace-tabs {
    background: var(--color-bg-white);
    border-radius: 8px;
    padding: 16px;
    box-shadow: var(--shadow-card);
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 16px;
  }

  .source-name {
    margin-left: 8px;
    color: var(--color-text-secondary);
  }

  .tag-line {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-width: 0;
  }

  .muted {
    color: var(--color-text-placeholder);
  }

  .ask-panel {
    display: grid;
    grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
    gap: 18px;

    &__input {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
  }

  .ask-result {
    min-height: 180px;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 18px;
    background: linear-gradient(135deg, rgba(126, 212, 160, 0.08), rgba(46, 92, 72, 0.04));

    &__head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      font-weight: 700;
    }

    p {
      margin: 0 0 16px;
      line-height: 1.8;
      white-space: pre-wrap;
    }
  }

  .source-block {
    display: flex;
    flex-direction: column;
    gap: 8px;

    > span:first-child {
      font-weight: 600;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}

@media (max-width: 900px) {
  .customer-service-ai {
    .page-header,
    .ask-panel {
      display: flex;
      flex-direction: column;
    }

    .page-header__actions {
      justify-content: flex-start;
    }
  }
}
</style>
