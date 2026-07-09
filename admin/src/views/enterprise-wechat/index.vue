<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>企业微信群机器人</h3>
        <el-button type="primary" @click="openRobotDialog()">
          <el-icon><Plus /></el-icon>新增机器人
        </el-button>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="机器人配置" name="robots">
          <el-alert
            class="mb-16"
            type="info"
            :closable="false"
            show-icon
            title="Webhook 和 Secret 按敏感信息加密保存，页面不会回显明文。"
          />

          <el-table :data="robots" v-loading="loading" stripe>
            <el-table-column prop="name" label="机器人名称" min-width="180" show-overflow-tooltip />
            <el-table-column label="Webhook" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.has_webhook_url ? 'success' : 'danger'" size="small">
                  {{ row.has_webhook_url ? '已配置' : '未配置' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Secret" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.has_secret ? 'success' : 'info'" size="small">
                  {{ row.has_secret ? '已配置' : '未配置' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                  {{ row.status === 'active' ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="170">
              <template #default="{ row }">{{ row.updated_at ? formatDateTime(row.updated_at) : '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="210" fixed="right" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-tooltip content="测试发送" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--approve" circle size="small" data-api="test-send" @click="openTestDialog(row)">
                      <el-icon><Promotion /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="发送日志" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--view" circle size="small" @click="openLogs(row)">
                      <el-icon><Tickets /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="知识库问答发送" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--info" circle size="small" data-api="knowledge-ask-send" @click="openKnowledgeAskDialog(row)">
                      <el-icon><ChatDotRound /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="编辑" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--edit" circle size="small" @click="openRobotDialog(row)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip :content="row.status === 'active' ? '停用' : '启用'" placement="top" :show-after="400">
                    <el-button
                      class="action-btn"
                      :class="row.status === 'active' ? 'action-btn--offline' : 'action-btn--online'"
                      circle
                      size="small"
                      @click="toggleRobotStatus(row)"
                    >
                      <el-icon><TurnOff v-if="row.status === 'active'" /><Open v-else /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="发送日志" name="logs">
          <div class="filter-bar mb-16">
            <el-select v-model="selectedRobotId" placeholder="选择机器人" style="width: 240px" @change="handleRobotChange">
              <el-option v-for="robot in robots" :key="robot.id" :label="robot.name" :value="robot.id" />
            </el-select>
            <el-select v-model="logParams.send_status" placeholder="发送状态" clearable style="width: 130px" @change="fetchLogs">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-button type="primary" @click="fetchLogs">
              <el-icon><Search /></el-icon>查询
            </el-button>
            <el-button @click="resetLogFilter">重置</el-button>
          </div>

          <el-table :data="logs" v-loading="logLoading" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="message_type" label="消息类型" width="110" />
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.send_status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.send_status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="response_code" label="响应码" width="100" align="center" />
            <el-table-column prop="error_message" label="失败原因" min-width="180" show-overflow-tooltip />
            <el-table-column label="发送时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="详情" width="80" fixed="right" align="center">
              <template #default="{ row }">
                <el-tooltip content="查看" placement="top" :show-after="400">
                  <el-button class="action-btn action-btn--view" circle size="small" @click="showLogDetail(row)">
                    <el-icon><View /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
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
    </div>

    <el-dialog v-model="robotDialogVisible" :title="editingRobot ? '编辑机器人' : '新增机器人'" :width="dialogWidth" @closed="resetRobotForm">
      <el-form ref="robotFormRef" :model="robotForm" :rules="robotRules" label-width="112px">
        <el-form-item label="机器人名称" prop="name">
          <el-input v-model.trim="robotForm.name" placeholder="如 运营告警群" />
        </el-form-item>
        <el-form-item label="webhook_url" prop="webhook_url">
          <el-input
            v-model.trim="robotForm.webhook_url"
            type="password"
            show-password
            :placeholder="editingRobot ? '留空则不修改' : '企业微信群机器人 webhook 地址'"
          />
        </el-form-item>
        <el-form-item label="secret">
          <el-input
            v-model.trim="robotForm.secret"
            type="password"
            show-password
            :disabled="clearSecret"
            placeholder="可选；留空则不修改或不设置"
          />
          <el-checkbox v-if="editingRobot" v-model="clearSecret" class="secret-clear-check">
            清空已配置 Secret
          </el-checkbox>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="robotForm.status">
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="inactive">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="robotDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingRobot" @click="saveRobot">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialogVisible" title="测试发送" :width="dialogWidth" @closed="resetTestForm">
      <el-form label-width="112px">
        <el-form-item label="机器人">
          <el-input :model-value="testingRobot?.name || '-'" disabled />
        </el-form-item>
        <el-form-item label="消息内容">
          <el-input v-model="testForm.content" type="textarea" :rows="4" maxlength="800" show-word-limit />
        </el-form-item>
        <el-form-item label="@手机号">
          <el-select
            v-model="testForm.mentioned_mobile_list"
            multiple
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            placeholder="输入手机号后回车，可为空"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="testDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="sendingTest" @click="sendTestMessage">发送</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="knowledgeAskDialogVisible" title="知识库问答发送" :width="dialogWidth" @closed="resetKnowledgeAskForm">
      <el-form label-width="112px">
        <el-form-item label="机器人">
          <el-input :model-value="knowledgeAskRobot?.name || '-'" disabled />
        </el-form-item>
        <el-form-item label="群内问题">
          <el-input v-model="knowledgeAskForm.question" type="textarea" :rows="4" maxlength="300" show-word-limit />
        </el-form-item>
        <el-form-item label="@手机号">
          <el-select
            v-model="knowledgeAskForm.mentioned_mobile_list"
            multiple
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            placeholder="输入手机号后回车，可为空"
          />
        </el-form-item>
      </el-form>
      <el-alert
        v-if="knowledgeAskPreview"
        class="mt-16"
        :type="knowledgeAskPreview.needs_human ? 'warning' : 'success'"
        :closable="false"
        show-icon
        :title="knowledgeAskPreview.needs_human ? '人工兜底' : '知识库命中'"
      />
      <div v-if="knowledgeAskPreview" class="knowledge-preview">
        <h4>最终答案</h4>
        <p>{{ knowledgeAskPreview.answer }}</p>
        <h4>来源引用</h4>
        <div v-if="knowledgeAskPreview.sources.length" class="source-tags">
          <el-tag v-for="source in knowledgeAskPreview.sources" :key="source.id" size="small" effect="plain">
            {{ source.title }}
          </el-tag>
        </div>
        <span v-else class="muted">无来源，发送内容将提示人工兜底。</span>
      </div>
      <template #footer>
        <el-button @click="knowledgeAskDialogVisible = false">取消</el-button>
        <el-button :loading="previewingKnowledgeAsk" @click="previewEnterpriseWechatKnowledgeAnswer">预览答案</el-button>
        <el-button type="primary" :loading="sendingKnowledgeAsk" :disabled="!knowledgeAskPreview" @click="sendKnowledgeAskMessage">确认发送</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="logDetailVisible" title="发送日志详情" :width="logDialogWidth">
      <el-descriptions :column="2" border v-if="detailLog">
        <el-descriptions-item label="日志ID">{{ detailLog.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ detailLog.send_status === 'success' ? '成功' : '失败' }}</el-descriptions-item>
        <el-descriptions-item label="响应码">{{ detailLog.response_code ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="发送时间">{{ formatDateTime(detailLog.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="失败原因" :span="2">{{ detailLog.error_message || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="detailLog" class="mt-16">
        <h4 class="mb-8">请求体</h4>
        <pre class="json-block">{{ formatSafeJson(detailLog.request_payload) }}</pre>
      </div>
      <div v-if="detailLog" class="mt-16">
        <h4 class="mb-8">响应体</h4>
        <pre class="json-block">{{ formatSafeJson(detailLog.response_body || {}) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { ChatDotRound, Edit, Open, Plus, Promotion, Search, Tickets, TurnOff, View } from '@element-plus/icons-vue'
import {
  askCustomerServiceKnowledge,
} from '@/api/customer-service-ai'
import {
  askSendEnterpriseWechatRobotKnowledge,
  createEnterpriseWechatRobot,
  getEnterpriseWechatRobotLogs,
  getEnterpriseWechatRobots,
  testSendEnterpriseWechatRobot,
  updateEnterpriseWechatRobot,
} from '@/api/enterprise-wechat'
import { formatDateTime } from '@/utils'
import type {
  EnterpriseWechatRobot,
  EnterpriseWechatRobotLog,
  EnterpriseWechatRobotPayload,
} from '@/types/enterprise-wechat'

const activeTab = ref('robots')
const dialogWidth = 'min(560px, calc(100vw - 32px))'
const logDialogWidth = 'min(680px, calc(100vw - 32px))'
const loading = ref(false)
const robots = ref<EnterpriseWechatRobot[]>([])

const robotDialogVisible = ref(false)
const savingRobot = ref(false)
const editingRobot = ref<EnterpriseWechatRobot | null>(null)
const robotFormRef = ref<FormInstance>()
const robotForm = reactive<EnterpriseWechatRobotPayload>({
  name: '',
  webhook_url: '',
  secret: '',
  status: 'active',
})
const clearSecret = ref(false)

const testDialogVisible = ref(false)
const sendingTest = ref(false)
const testingRobot = ref<EnterpriseWechatRobot | null>(null)
const testForm = reactive({
  content: '一月一露企业微信群机器人测试消息',
  mentioned_mobile_list: [] as string[],
})

const knowledgeAskDialogVisible = ref(false)
const sendingKnowledgeAsk = ref(false)
const previewingKnowledgeAsk = ref(false)
const knowledgeAskRobot = ref<EnterpriseWechatRobot | null>(null)
const knowledgeAskPreview = ref<{
  question: string
  answer: string
  sources: Array<{ id: number; title: string }>
  needs_human: boolean
} | null>(null)
const knowledgeAskForm = reactive({
  question: '',
  mentioned_mobile_list: [] as string[],
})

const selectedRobotId = ref<number | undefined>()
const logLoading = ref(false)
const logs = ref<EnterpriseWechatRobotLog[]>([])
const logTotal = ref(0)
const logParams = reactive({
  page: 1,
  page_size: 20,
  send_status: undefined as EnterpriseWechatRobotLog['send_status'] | undefined,
})
const logDetailVisible = ref(false)
const detailLog = ref<EnterpriseWechatRobotLog | null>(null)

const robotRules: FormRules = {
  name: [{ required: true, message: '请输入机器人名称', trigger: 'blur' }],
  webhook_url: [
    {
      validator: (_rule, value, callback) => {
        if (!editingRobot.value && !value) callback(new Error('请输入 webhook_url'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const sensitiveKeys = ['webhook', 'webhook_url', 'secret', 'sign', 'key', 'token', 'authorization', 'password']

function redactSensitive(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(item => redactSensitive(item))
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => {
        const lowerKey = key.toLowerCase()
        const shouldRedact = sensitiveKeys.some(sensitiveKey => lowerKey.includes(sensitiveKey))
        return [key, shouldRedact ? '***' : redactSensitive(item)]
      }),
    )
  }
  return value
}

function formatSafeJson(value: unknown) {
  return JSON.stringify(redactSensitive(value), null, 2)
}

async function fetchRobots() {
  loading.value = true
  try {
    const res = await getEnterpriseWechatRobots()
    robots.value = res.data
    const firstRobot = robots.value[0]
    if (!selectedRobotId.value && firstRobot) {
      selectedRobotId.value = firstRobot.id
    }
  } finally {
    loading.value = false
  }
}

function resetRobotForm() {
  editingRobot.value = null
  clearSecret.value = false
  Object.assign(robotForm, {
    name: '',
    webhook_url: '',
    secret: '',
    status: 'active',
  })
  robotFormRef.value?.clearValidate()
}

function openRobotDialog(row?: EnterpriseWechatRobot) {
  if (row) {
    editingRobot.value = row
    Object.assign(robotForm, {
      name: row.name,
      webhook_url: '',
      secret: '',
      status: row.status,
    })
  }
  robotDialogVisible.value = true
}

function buildRobotPayload() {
  const payload: Partial<EnterpriseWechatRobotPayload> = {
    name: robotForm.name,
    status: robotForm.status,
  }
  if (robotForm.webhook_url) payload.webhook_url = robotForm.webhook_url
  if (clearSecret.value) payload.secret = ''
  else if (robotForm.secret) payload.secret = robotForm.secret
  return payload
}

async function saveRobot() {
  const valid = await robotFormRef.value?.validate().catch(() => false)
  if (!valid) return
  const payload = buildRobotPayload()
  savingRobot.value = true
  try {
    if (editingRobot.value) {
      await updateEnterpriseWechatRobot(editingRobot.value.id, payload)
    } else {
      await createEnterpriseWechatRobot(payload as EnterpriseWechatRobotPayload)
    }
    ElMessage.success('企业微信群机器人已保存')
    robotDialogVisible.value = false
    fetchRobots()
  } finally {
    savingRobot.value = false
  }
}

async function toggleRobotStatus(row: EnterpriseWechatRobot) {
  const status = row.status === 'active' ? 'inactive' : 'active'
  const actionText = status === 'active' ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(
      `确定${actionText}企业微信群机器人「${row.name}」吗？`,
      `${actionText}机器人确认`,
      { type: status === 'active' ? 'success' : 'warning' },
    )
  } catch {
    return
  }
  await updateEnterpriseWechatRobot(row.id, { status })
  ElMessage.success(status === 'active' ? '机器人已启用' : '机器人已停用')
  fetchRobots()
}

function resetTestForm() {
  testingRobot.value = null
  testForm.content = '一月一露企业微信群机器人测试消息'
  testForm.mentioned_mobile_list = []
}

function openTestDialog(row: EnterpriseWechatRobot) {
  testingRobot.value = row
  testDialogVisible.value = true
}

async function sendTestMessage() {
  if (!testingRobot.value) return
  if (!testForm.content.trim()) {
    ElMessage.error('请输入消息内容')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认发送测试消息到企业微信群机器人「${testingRobot.value.name}」？消息内容：${testForm.content.trim()}；@ 手机号数量：${testForm.mentioned_mobile_list.length}`,
      '确认发送测试消息',
      { type: 'warning', confirmButtonText: '确认发送', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const payload = {
    content: testForm.content.trim(),
    mentioned_mobile_list: testForm.mentioned_mobile_list,
  }
  sendingTest.value = true
  try {
    const res = await testSendEnterpriseWechatRobot(testingRobot.value.id, payload)
    ElMessage.success(`测试消息已发送，日志ID：${res.data.log_id}`)
    testDialogVisible.value = false
    selectedRobotId.value = testingRobot.value.id
    activeTab.value = 'logs'
    fetchLogs()
  } finally {
    sendingTest.value = false
  }
}

function resetKnowledgeAskForm() {
  knowledgeAskRobot.value = null
  knowledgeAskPreview.value = null
  knowledgeAskForm.question = ''
  knowledgeAskForm.mentioned_mobile_list = []
}

function openKnowledgeAskDialog(row: EnterpriseWechatRobot) {
  knowledgeAskRobot.value = row
  knowledgeAskPreview.value = null
  knowledgeAskDialogVisible.value = true
}

async function previewEnterpriseWechatKnowledgeAnswer() {
  const question = knowledgeAskForm.question.trim()
  if (!question) {
    ElMessage.error('请输入群内问题')
    return
  }
  previewingKnowledgeAsk.value = true
  try {
    const res = await askCustomerServiceKnowledge(question)
    knowledgeAskPreview.value = {
      question,
      answer: res.data.answer,
      sources: res.data.sources,
      needs_human: res.data.needs_human,
    }
  } finally {
    previewingKnowledgeAsk.value = false
  }
}

async function sendKnowledgeAskMessage() {
  if (!knowledgeAskRobot.value) return
  const question = knowledgeAskForm.question.trim()
  if (!question) {
    ElMessage.error('请输入群内问题')
    return
  }
  if (!knowledgeAskPreview.value) {
    await previewEnterpriseWechatKnowledgeAnswer()
    if (!knowledgeAskPreview.value) return
  }
  if (knowledgeAskPreview.value.question !== question) {
    knowledgeAskPreview.value = null
    ElMessage.warning('群内问题已修改，请重新预览答案')
    return
  }
  const payload = {
    question,
    mentioned_mobile_list: knowledgeAskForm.mentioned_mobile_list,
  }
  const sourceText = knowledgeAskPreview.value.sources.map(item => item.title).join('、') || '人工兜底'
  try {
    await ElMessageBox.confirm(
      `确认将知识库问答发送到企业微信群机器人「${knowledgeAskRobot.value.name}」？\n问题：${question}\n最终答案：${knowledgeAskPreview.value.answer}\n来源引用：${sourceText}\n状态：${knowledgeAskPreview.value.needs_human ? '人工兜底' : '知识库命中'}\n@手机号数量：${knowledgeAskForm.mentioned_mobile_list.length}`,
      '知识库问答发送',
      { type: 'warning', confirmButtonText: '确认发送', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  sendingKnowledgeAsk.value = true
  try {
    const res = await askSendEnterpriseWechatRobotKnowledge(knowledgeAskRobot.value.id, payload)
    ElMessage.success(`知识库问答已发送，日志ID：${res.data.robot_log_id}`)
    knowledgeAskDialogVisible.value = false
    selectedRobotId.value = knowledgeAskRobot.value.id
    activeTab.value = 'logs'
    fetchLogs()
  } finally {
    sendingKnowledgeAsk.value = false
  }
}

function openLogs(row: EnterpriseWechatRobot) {
  selectedRobotId.value = row.id
  activeTab.value = 'logs'
  fetchLogs()
}

function handleRobotChange() {
  logParams.page = 1
  fetchLogs()
}

function resetLogFilter() {
  logParams.send_status = undefined
  logParams.page = 1
  fetchLogs()
}

async function fetchLogs() {
  if (!selectedRobotId.value) {
    logs.value = []
    logTotal.value = 0
    return
  }
  logLoading.value = true
  try {
    const res = await getEnterpriseWechatRobotLogs(selectedRobotId.value, logParams)
    logs.value = res.data.list
    logTotal.value = res.data.pagination.total
  } finally {
    logLoading.value = false
  }
}

function showLogDetail(row: EnterpriseWechatRobotLog) {
  detailLog.value = row
  logDetailVisible.value = true
}

onMounted(async () => {
  await fetchRobots()
  await fetchLogs()
})
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}

.json-block {
  max-height: 220px;
  overflow-y: auto;
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-small);
  background: var(--color-bg-warm);
  font-size: 12px;
  line-height: 1.6;
}

.secret-clear-check {
  margin-top: 8px;
}

.knowledge-preview {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-small);
  background: var(--color-bg-warm);

  h4 {
    margin: 0 0 8px;
    font-size: 13px;
    color: var(--color-text);
  }

  p {
    margin: 0 0 12px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted {
  color: var(--color-text-secondary);
}
</style>
