<template>
  <el-dialog
    :model-value="visible"
    title="版本管理"
    width="640px"
    aria-label="版本管理"
    @update:model-value="emit('update:visible', $event)"
    @close="emit('update:visible', false)"
  >
    <el-table :data="versionList" v-loading="loading" stripe>
      <el-table-column label="版本号" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_current ? 'success' : 'info'" size="small">
            V{{ row.version_number }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="170">
        <template #default="{ row }">
          {{ formatTime(row.published_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="150">
        <template #default="{ row }">
          {{ row.remark || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_current" type="success" size="small">当前版本</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.is_current"
            type="warning"
            link
            size="small"
            @click="handleRollback(row)"
          >
            回滚
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <template v-if="!loading && versionList.length === 0">
      <el-empty description="暂无版本记录" />
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getCmsVersions } from '@/api/cms'
import type { CmsPageVersion } from '@/types/cms'
import dayjs from 'dayjs'

const props = defineProps<{
  visible: boolean
  pageId: number
  currentVersionId?: number
}>()

const emit = defineEmits<{
  (e: 'rollback', versionId: number): void
  (e: 'update:visible', value: boolean): void
}>()

const loading = ref(false)
const versionList = ref<CmsPageVersion[]>([])

function formatTime(str: string) {
  return dayjs(str).format('YYYY-MM-DD HH:mm:ss')
}

// 打开时加载版本列表
watch(() => props.visible, (val) => {
  if (val && props.pageId) {
    fetchVersions()
  }
})

async function fetchVersions() {
  loading.value = true
  try {
    const res = await getCmsVersions(props.pageId)
    versionList.value = res.data || []
  } catch {
    // 错误由拦截器处理
  } finally {
    loading.value = false
  }
}

async function handleRollback(version: CmsPageVersion) {
  try {
    await ElMessageBox.confirm(
      `确定回滚到 V${version.version_number}？当前草稿将被覆盖`,
      '确认回滚',
      { type: 'warning', confirmButtonText: '确定回滚', cancelButtonText: '取消' }
    )
    emit('rollback', version.id)
  } catch {
    // 取消
  }
}
</script>
