<template>
  <div class="page-container">
    <div class="card-box">
      <h3 class="mb-16">操作日志</h3>

      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-input v-model="params.module" placeholder="模块" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="params.action" placeholder="操作类型" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" @change="handleDateChange" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="admin_name" label="操作人" width="100" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="action" label="操作" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="140" />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="详情" width="80" align="center">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="params.page" v-model:page-size="params.page_size" :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" @size-change="fetchData" @current-change="fetchData" />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="操作详情" width="600px">
      <el-descriptions :column="2" border v-if="detailLog">
        <el-descriptions-item label="操作人">{{ detailLog.admin_name }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ detailLog.module }}</el-descriptions-item>
        <el-descriptions-item label="操作" :span="2">{{ detailLog.action }}</el-descriptions-item>
        <el-descriptions-item label="IP">{{ detailLog.ip }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatDateTime(detailLog.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="detailLog?.before_data" class="mt-16">
        <h4>变更前</h4>
        <pre class="json-block">{{ JSON.stringify(detailLog.before_data, null, 2) }}</pre>
      </div>
      <div v-if="detailLog?.after_data" class="mt-16">
        <h4>变更后</h4>
        <pre class="json-block">{{ JSON.stringify(detailLog.after_data, null, 2) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getOperationLogs } from '@/api/system'
import { formatDateTime } from '@/utils'
import type { OperationLog, OperationLogSearchParams } from '@/types'

const loading = ref(false)
const logs = ref<OperationLog[]>([])
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)
const detailVisible = ref(false)
const detailLog = ref<OperationLog | null>(null)
const params = reactive<OperationLogSearchParams>({ page: 1, page_size: 20 })

async function fetchData() {
  loading.value = true
  try { const res = await getOperationLogs(params); logs.value = res.data.list; total.value = res.data.pagination.total }
  catch {} finally { loading.value = false }
}

function handleSearch() { params.page = 1; fetchData() }
function handleReset() { params.module = undefined; params.action = undefined; params.start_date = undefined; params.end_date = undefined; dateRange.value = null; handleSearch() }
function handleDateChange(val: [string, string] | null) { params.start_date = val?.[0]; params.end_date = val?.[1]; handleSearch() }
function showDetail(row: OperationLog) { detailLog.value = row; detailVisible.value = true }

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
.json-block { background: #f5f7fa; padding: 12px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto; }
</style>
