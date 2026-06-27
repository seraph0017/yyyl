<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <div>
          <h3>会员卡配置 - 年卡</h3>
          <p class="sub-title">兼容入口，仍保留原有年卡配置管理能力。</p>
        </div>
        <el-button type="primary" @click="showConfigDialog = true"><el-icon><Plus /></el-icon>新建年卡配置</el-button>
      </div>

      <el-alert class="mb-16" type="info" :closable="false" show-icon title="这里是旧年卡管理入口的兼容页，主入口请使用“会员卡”总览。" />

      <h4 class="mb-8">年卡配置</h4>
      <el-table :data="configs" v-loading="loading" border class="mb-20">
        <el-table-column prop="name" label="配置名称" />
        <el-table-column label="价格" width="120" align="right">
          <template #default="{ row }">¥{{ formatPrice(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="duration_days" label="有效天数" width="100" align="center" />
        <el-table-column prop="daily_limit" label="每日限额" width="100" align="center" />
        <el-table-column label="滑动窗口" width="160">
          <template #default="{ row }">连续{{ row.max_consecutive_days }}天 + 间隔{{ row.gap_days }}天</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="primary" @click="editConfig(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="compat-link">
        <el-button @click="router.push('/members')">返回会员卡总览</el-button>
        <el-button type="primary" plain @click="router.push('/times-cards')">查看次数卡配置</el-button>
      </div>
    </div>

    <el-dialog v-model="showConfigDialog" title="年卡配置" width="500px">
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="配置名称" required><el-input v-model="configForm.name" /></el-form-item>
        <el-form-item label="价格（分）" required><el-input-number v-model="configForm.price" :min="0" :step="100" style="width: 100%;" /></el-form-item>
        <el-form-item label="有效天数" required><el-input-number v-model="configForm.duration_days" :min="1" /></el-form-item>
        <el-form-item label="每日限额"><el-input-number v-model="configForm.daily_limit" :min="1" :max="10" /></el-form-item>
        <el-form-item label="最大连续天数"><el-input-number v-model="configForm.max_consecutive_days" :min="1" /></el-form-item>
        <el-form-item label="间隔天数"><el-input-number v-model="configForm.gap_days" :min="0" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="configForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getAnnualCardConfigs, createAnnualCardConfig, updateAnnualCardConfig } from '@/api/member'
import { formatPrice } from '@/utils'
import type { AnnualCardConfig } from '@/types'

const router = useRouter()
const loading = ref(false)
const configs = ref<AnnualCardConfig[]>([])
const showConfigDialog = ref(false)
const editingConfig = ref<AnnualCardConfig | null>(null)

const configForm = reactive({ name: '', price: 0, duration_days: 365, daily_limit: 1, max_consecutive_days: 3, gap_days: 1, description: '' })

async function fetchData() {
  loading.value = true
  try {
    const res = await getAnnualCardConfigs()
    configs.value = res.data
  } catch {
    configs.value = []
  } finally {
    loading.value = false
  }
}

function editConfig(row: AnnualCardConfig) {
  editingConfig.value = row
  Object.assign(configForm, row)
  showConfigDialog.value = true
}

async function handleSaveConfig() {
  try {
    if (editingConfig.value) {
      await updateAnnualCardConfig(editingConfig.value.id, configForm)
    } else {
      await createAnnualCardConfig(configForm)
    }
    ElMessage.success('保存成功')
    showConfigDialog.value = false
    fetchData()
  } catch {}
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.sub-title {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
}

.compat-link {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
