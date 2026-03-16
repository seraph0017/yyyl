<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>年卡管理</h3>
        <el-button type="primary" @click="showConfigDialog = true"><el-icon><Plus /></el-icon>新建年卡配置</el-button>
      </div>

      <!-- 年卡配置列表 -->
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

      <!-- 积分兑换活动 -->
      <div class="flex-between mb-8">
        <h4>积分兑换活动</h4>
        <el-button size="small" type="primary" @click="showExchangeDialog = true">新建活动</el-button>
      </div>
      <el-table :data="exchangeConfigs" border>
        <el-table-column prop="name" label="活动名称" />
        <el-table-column prop="required_points" label="所需积分" width="100" align="center" />
        <el-table-column label="库存/已兑" width="100" align="center">
          <template #default="{ row }">{{ row.exchanged_count }}/{{ row.stock }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '进行中' : '已关闭' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="editExchange(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 年卡配置弹窗 -->
    <el-dialog v-model="showConfigDialog" :title="editingConfig ? '编辑年卡配置' : '新建年卡配置'" width="500px">
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

    <!-- 积分兑换弹窗 -->
    <el-dialog v-model="showExchangeDialog" title="积分兑换活动" width="500px">
      <el-form :model="exchangeForm" label-width="100px">
        <el-form-item label="活动名称" required><el-input v-model="exchangeForm.name" /></el-form-item>
        <el-form-item label="所需积分" required><el-input-number v-model="exchangeForm.required_points" :min="1" style="width: 100%;" /></el-form-item>
        <el-form-item label="库存"><el-input-number v-model="exchangeForm.stock" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExchangeDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveExchange">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit } from '@element-plus/icons-vue'
import { getAnnualCardConfigs, createAnnualCardConfig, updateAnnualCardConfig, getPointsExchangeConfigs, createPointsExchangeConfig, updatePointsExchangeConfig } from '@/api/member'
import { formatPrice } from '@/utils'
import type { AnnualCardConfig, PointsExchangeConfig } from '@/types'

const loading = ref(false)
const configs = ref<AnnualCardConfig[]>([])
const exchangeConfigs = ref<PointsExchangeConfig[]>([])
const showConfigDialog = ref(false)
const showExchangeDialog = ref(false)
const editingConfig = ref<AnnualCardConfig | null>(null)
const editingExchange = ref<PointsExchangeConfig | null>(null)

const configForm = reactive({ name: '', price: 0, duration_days: 365, daily_limit: 1, max_consecutive_days: 3, gap_days: 1, description: '' })
const exchangeForm = reactive({ name: '', required_points: 100, stock: 0 })

async function fetchData() {
  loading.value = true
  try {
    const [c, e] = await Promise.all([getAnnualCardConfigs(), getPointsExchangeConfigs()])
    configs.value = c.data
    exchangeConfigs.value = e.data
  } catch {} finally { loading.value = false }
}

function editConfig(row: AnnualCardConfig) {
  editingConfig.value = row
  Object.assign(configForm, row)
  showConfigDialog.value = true
}

function editExchange(row: PointsExchangeConfig) {
  editingExchange.value = row
  Object.assign(exchangeForm, row)
  showExchangeDialog.value = true
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

async function handleSaveExchange() {
  try {
    if (editingExchange.value) {
      await updatePointsExchangeConfig(editingExchange.value.id, exchangeForm)
    } else {
      await createPointsExchangeConfig(exchangeForm)
    }
    ElMessage.success('保存成功')
    showExchangeDialog.value = false
    fetchData()
  } catch {}
}

onMounted(fetchData)
</script>
