<template>
  <div class="page-container">
    <!-- 统计概览 -->
    <el-row :gutter="16" class="mb-20">
      <el-col :span="8">
        <div class="card-box" style="text-align: center;">
          <div style="font-size: 32px; font-weight: 700; color: #2E7D32;">{{ stats.total_sent || 0 }}</div>
          <div style="color: #909399; margin-top: 4px;">总发送数</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box" style="text-align: center;">
          <div style="font-size: 32px; font-weight: 700; color: #4CAF50;">{{ ((stats.success_rate || 0) * 100).toFixed(1) }}%</div>
          <div style="color: #909399; margin-top: 4px;">发送成功率</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card-box" style="text-align: center;">
          <div style="font-size: 32px; font-weight: 700; color: #FF9800;">{{ (stats.template_stats || []).length }}</div>
          <div style="color: #909399; margin-top: 4px;">模板数量</div>
        </div>
      </el-col>
    </el-row>

    <!-- 通知模板 -->
    <div class="card-box mb-20">
      <h3 class="mb-16">通知模板管理</h3>
      <el-table :data="templates" v-loading="loadingTemplates" stripe>
        <el-table-column prop="name" label="模板名称" min-width="200" />
        <el-table-column prop="template_key" label="模板标识" width="200" />
        <el-table-column label="渠道" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ { wechat: '微信', sms: '短信', site: '站内' }[row.channel as string] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggleTemplate(row)" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 发送记录 -->
    <div class="card-box">
      <h3 class="mb-16">发送记录</h3>
      <el-table :data="records" v-loading="loadingRecords" stripe>
        <el-table-column prop="user_nickname" label="用户" width="120" />
        <el-table-column prop="template_name" label="模板" min-width="150" />
        <el-table-column prop="channel" label="渠道" width="80" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'sent' ? 'success' : row.status === 'failed' ? 'danger' : 'info'">
              {{ { pending: '待发送', sent: '已发送', failed: '失败' }[row.status as string] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.send_at || row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="recordParams.page" :total="recordTotal" :page-size="20" layout="total, prev, pager, next" @current-change="fetchRecords" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getNotificationTemplates, updateNotificationTemplate, getNotificationRecords, getNotificationStats } from '@/api/system'
import { formatDateTime } from '@/utils'
import type { NotificationTemplate, NotificationRecord, NotificationStats } from '@/types'

const loadingTemplates = ref(false)
const loadingRecords = ref(false)
const templates = ref<NotificationTemplate[]>([])
const records = ref<NotificationRecord[]>([])
const recordTotal = ref(0)
const stats = ref<Partial<NotificationStats>>({})
const recordParams = reactive({ page: 1, page_size: 20 })

async function fetchTemplates() {
  loadingTemplates.value = true
  try { const res = await getNotificationTemplates(); templates.value = res.data } catch {} finally { loadingTemplates.value = false }
}

async function fetchRecords() {
  loadingRecords.value = true
  try { const res = await getNotificationRecords(recordParams); records.value = res.data.items; recordTotal.value = res.data.total } catch {} finally { loadingRecords.value = false }
}

async function fetchStats() {
  try { const res = await getNotificationStats(); stats.value = res.data } catch {}
}

async function handleToggleTemplate(row: NotificationTemplate) {
  try { await updateNotificationTemplate(row.id, { enabled: row.enabled }); ElMessage.success('更新成功') } catch { row.enabled = !row.enabled }
}

onMounted(() => { fetchTemplates(); fetchRecords(); fetchStats() })
</script>

<style lang="scss" scoped>
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
