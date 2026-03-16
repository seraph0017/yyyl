<template>
  <div class="page-container">
    <div class="card-box">
      <h3 class="mb-16">页面编辑</h3>
      <el-table :data="pageConfigs" v-loading="loading" stripe>
        <el-table-column prop="page_key" label="页面标识" width="160" />
        <el-table-column prop="page_name" label="页面名称" width="160" />
        <el-table-column label="配置项数" width="100" align="center">
          <template #default="{ row }">{{ Object.keys(row.config || {}).length }}项</template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="editPage(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDialog" :title="`编辑页面：${editingPage?.page_name}`" width="600px">
      <el-form label-width="100px">
        <el-form-item label="配置内容">
          <el-input v-model="configJson" type="textarea" :rows="15" placeholder="JSON格式配置" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import { getPageConfigs, updatePageConfig } from '@/api/system'
import { formatDateTime } from '@/utils'
import type { PageConfig } from '@/types'

const loading = ref(false)
const pageConfigs = ref<PageConfig[]>([])
const showDialog = ref(false)
const editingPage = ref<PageConfig | null>(null)
const configJson = ref('')

async function fetchData() {
  loading.value = true
  try { const res = await getPageConfigs(); pageConfigs.value = res.data } catch {} finally { loading.value = false }
}

function editPage(row: PageConfig) {
  editingPage.value = row
  configJson.value = JSON.stringify(row.config, null, 2)
  showDialog.value = true
}

async function handleSave() {
  if (!editingPage.value) return
  try {
    const config = JSON.parse(configJson.value)
    await updatePageConfig(editingPage.value.page_key, config)
    ElMessage.success('保存成功')
    showDialog.value = false
    fetchData()
  } catch (e: any) {
    ElMessage.error(e.message?.includes('JSON') ? 'JSON格式错误' : '保存失败')
  }
}

onMounted(fetchData)
</script>
