<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>次数卡管理</h3>
        <el-button type="primary" @click="showConfigDialog = true"><el-icon><Plus /></el-icon>新建次数卡配置</el-button>
      </div>

      <!-- 次数卡配置 -->
      <el-table :data="configs" v-loading="loading" border class="mb-20">
        <el-table-column prop="name" label="卡名称" />
        <el-table-column prop="total_times" label="总次数" width="80" align="center" />
        <el-table-column label="价格" width="100" align="right">
          <template #default="{ row }">¥{{ formatPrice(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="validity_days" label="有效天数" width="100" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="editConfig(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="消耗规则" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--inventory" circle size="small" @click="manageRules(row)">
                  <el-icon><Setting /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 激活码管理 -->
      <div class="flex-between mb-8">
        <h4>激活码管理</h4>
        <el-button size="small" type="primary" @click="showGenerateDialog = true">批量生成</el-button>
      </div>
      <el-form :inline="true" class="mb-8">
        <el-form-item>
          <el-input v-model="codeParams.batch_no" placeholder="批次号" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="codeParams.status" placeholder="状态" clearable>
            <el-option label="未使用" value="unused" />
            <el-option label="已使用" value="used" />
            <el-option label="已禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button @click="fetchCodes">查询</el-button></el-form-item>
      </el-form>
      <el-table :data="codes" border size="small">
        <el-table-column prop="code" label="激活码" width="200" />
        <el-table-column prop="batch_no" label="批次号" width="160" />
        <el-table-column prop="config_name" label="关联卡" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }"><el-tag size="small" :type="row.status === 'unused' ? 'success' : row.status === 'used' ? 'info' : 'danger'">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="使用时间" width="170">
          <template #default="{ row }">{{ row.used_at ? formatDateTime(row.used_at) : '--' }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="codeParams.page" v-model:page-size="codeParams.page_size" :total="codeTotal" layout="total, prev, pager, next" @current-change="fetchCodes" />
      </div>
    </div>

    <!-- 配置弹窗 -->
    <el-dialog v-model="showConfigDialog" title="次数卡配置" width="500px">
      <el-form :model="configForm" label-width="100px">
        <el-form-item label="卡名称" required><el-input v-model="configForm.name" /></el-form-item>
        <el-form-item label="总次数" required><el-input-number v-model="configForm.total_times" :min="1" /></el-form-item>
        <el-form-item label="价格（分）"><el-input-number v-model="configForm.price" :min="0" :step="100" style="width: 100%;" /></el-form-item>
        <el-form-item label="有效天数"><el-input-number v-model="configForm.validity_days" :min="1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfig">保存</el-button>
      </template>
    </el-dialog>

    <!-- 生成激活码弹窗 -->
    <el-dialog v-model="showGenerateDialog" title="批量生成激活码" width="400px">
      <el-form :model="genForm" label-width="100px">
        <el-form-item label="关联配置" required>
          <el-select v-model="genForm.config_id" style="width: 100%;">
            <el-option v-for="c in configs" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="生成数量" required><el-input-number v-model="genForm.count" :min="1" :max="1000" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleGenerate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getTimesCardConfigs, createTimesCardConfig, updateTimesCardConfig, getActivationCodes, generateActivationCodes } from '@/api/member'
import { formatPrice, formatDateTime } from '@/utils'
import type { TimesCardConfig, ActivationCode } from '@/types'

const loading = ref(false)
const configs = ref<TimesCardConfig[]>([])
const codes = ref<ActivationCode[]>([])
const codeTotal = ref(0)
const showConfigDialog = ref(false)
const showGenerateDialog = ref(false)
const editingConfig = ref<TimesCardConfig | null>(null)

const configForm = reactive({ name: '', total_times: 10, price: 0, validity_days: 365 })
const codeParams = reactive({ page: 1, page_size: 10, batch_no: '', status: '' })
const genForm = reactive({ config_id: 0, count: 10 })

async function fetchData() {
  loading.value = true
  try { const res = await getTimesCardConfigs(); configs.value = res.data } catch {} finally { loading.value = false }
}

async function fetchCodes() {
  try { const res = await getActivationCodes(codeParams); codes.value = res.data.list; codeTotal.value = res.data.pagination.total } catch {}
}

function editConfig(row: TimesCardConfig) {
  editingConfig.value = row; Object.assign(configForm, row); showConfigDialog.value = true
}

function manageRules(row: TimesCardConfig) {
  ElMessage.info(`次数消耗规则管理 - ${row.name}，功能开发中`)
}

async function handleSaveConfig() {
  try {
    if (editingConfig.value) { await updateTimesCardConfig(editingConfig.value.id, configForm) }
    else { await createTimesCardConfig(configForm) }
    ElMessage.success('保存成功'); showConfigDialog.value = false; fetchData()
  } catch {}
}

async function handleGenerate() {
  if (!genForm.config_id) { ElMessage.warning('请选择关联配置'); return }
  try { await generateActivationCodes(genForm); ElMessage.success('生成成功'); showGenerateDialog.value = false; fetchCodes() } catch {}
}

onMounted(() => { fetchData(); fetchCodes() })
</script>

<style lang="scss" scoped>
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
