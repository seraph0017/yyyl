<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>绩效管理</h3>
        <div class="header-actions">
          <el-button type="primary" plain @click="handleTriggerCalculation">
            <el-icon><Refresh /></el-icon>触发计算
          </el-button>
          <el-button type="success" plain @click="handleExport">
            <el-icon><Download /></el-icon>导出
          </el-button>
        </div>
      </div>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 绩效系数配置 -->
        <el-tab-pane label="绩效系数配置" name="config">
          <el-table :data="configList" v-loading="configLoading" stripe>
            <el-table-column prop="income_type" label="收入类型" width="180" />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column label="绩效系数" width="180">
              <template #default="{ row }">
                <template v-if="editingConfigId === row.id">
                  <el-input-number
                    v-model="editingCoefficient"
                    :min="0"
                    :max="10"
                    :step="0.01"
                    :precision="2"
                    size="small"
                    style="width: 120px"
                  />
                </template>
                <template v-else>
                  <span class="coefficient">{{ row.coefficient }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <template v-if="editingConfigId === row.id">
                    <el-tooltip content="保存" placement="top" :show-after="400">
                      <el-button class="action-btn action-btn--save" circle size="small" @click="saveConfig(row)">
                        <el-icon><Check /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="取消" placement="top" :show-after="400">
                      <el-button class="action-btn action-btn--cancel" circle size="small" @click="cancelEditConfig">
                        <el-icon><Close /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </template>
                  <template v-else>
                    <el-tooltip content="编辑" placement="top" :show-after="400">
                      <el-button class="action-btn action-btn--edit" circle size="small" @click="startEditConfig(row)">
                        <el-icon><Edit /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </template>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 绩效记录 -->
        <el-tab-pane label="绩效记录" name="records">
          <el-form :inline="true" class="mb-16">
            <el-form-item>
              <el-input v-model="recordParams.keyword" placeholder="员工姓名" clearable style="width: 160px" @keyup.enter="handleRecordSearch" />
            </el-form-item>
            <el-form-item>
              <el-select v-model="recordParams.period_type" placeholder="周期类型" clearable @change="handleRecordSearch">
                <el-option label="日结" value="daily" />
                <el-option label="月结" value="monthly" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-date-picker v-model="recordDateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" @change="handleRecordDateChange" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRecordSearch"><el-icon><Search /></el-icon>搜索</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="recordList" v-loading="recordLoading" stripe>
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="detail-expand">
                  <el-table :data="row.details" size="small" border>
                    <el-table-column prop="income_type" label="收入类型" width="150" />
                    <el-table-column label="收入金额" width="140" align="right">
                      <template #default="{ row: detail }">¥{{ formatPrice(detail.income_amount) }}</template>
                    </el-table-column>
                    <el-table-column label="绩效金额" width="140" align="right">
                      <template #default="{ row: detail }">
                        <span class="performance-value">¥{{ formatPrice(detail.performance_amount) }}</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="staff_name" label="员工" width="120" />
            <el-table-column label="周期" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.period_type === 'daily' ? '' : 'success'" size="small">
                  {{ row.period_type === 'daily' ? '日结' : '月结' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="周期范围" width="220">
              <template #default="{ row }">
                {{ formatDate(row.period_start) }} ~ {{ formatDate(row.period_end) }}
              </template>
            </el-table-column>
            <el-table-column label="总收入" width="140" align="right">
              <template #default="{ row }">¥{{ formatPrice(row.total_income) }}</template>
            </el-table-column>
            <el-table-column label="总绩效" width="140" align="right">
              <template #default="{ row }">
                <span class="performance-value">¥{{ formatPrice(row.total_performance) }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="recordParams.page"
              v-model:page-size="recordParams.page_size"
              :total="recordTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchRecords"
              @current-change="fetchRecords"
            />
          </div>
        </el-tab-pane>

        <!-- 绩效排名 -->
        <el-tab-pane label="绩效排名" name="ranking">
          <el-form :inline="true" class="mb-16">
            <el-form-item label="周期类型">
              <el-select v-model="rankingParams.period_type" @change="fetchRanking">
                <el-option label="日结" value="daily" />
                <el-option label="月结" value="monthly" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期">
              <el-date-picker v-model="rankingParams.period_start" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" @change="fetchRanking" />
            </el-form-item>
          </el-form>

          <el-table :data="rankingList" v-loading="rankingLoading" stripe>
            <el-table-column label="排名" width="100" align="center">
              <template #default="{ row }">
                <span v-if="row.rank === 1" class="rank-medal">🥇</span>
                <span v-else-if="row.rank === 2" class="rank-medal">🥈</span>
                <span v-else-if="row.rank === 3" class="rank-medal">🥉</span>
                <span v-else class="rank-number">{{ row.rank }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="staff_name" label="员工姓名" width="150" />
            <el-table-column label="总收入" width="160" align="right">
              <template #default="{ row }">¥{{ formatPrice(row.total_income) }}</template>
            </el-table-column>
            <el-table-column label="总绩效" width="160" align="right">
              <template #default="{ row }">
                <span class="performance-value">¥{{ formatPrice(row.total_performance) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="绩效占比" min-width="200">
              <template #default="{ row }">
                <el-progress
                  :percentage="maxPerformance ? (row.total_performance / maxPerformance) * 100 : 0"
                  :stroke-width="12"
                  :show-text="false"
                  :color="row.rank <= 3 ? '#E6A23C' : '#409EFF'"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 触发计算弹窗 -->
    <el-dialog v-model="calcDialogVisible" title="触发绩效计算" width="400px" destroy-on-close>
      <el-form :model="calcForm" label-width="80px">
        <el-form-item label="计算类型">
          <el-select v-model="calcForm.period_type" style="width: 100%">
            <el-option label="日结" value="daily" />
            <el-option label="月结" value="monthly" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="calcForm.period_start" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="calcForm.period_end" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="calcDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="calcLoading" @click="submitCalculation">确认计算</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Download, Edit, Check, Close } from '@element-plus/icons-vue'
import {
  getPerformanceConfigs, updatePerformanceConfigs,
  getPerformanceRecords, getPerformanceRanking,
  triggerCalculation, exportPerformance,
} from '@/api/performance'
import { formatPrice, formatDate } from '@/utils'
import type { PerformanceConfig, PerformanceRecord, PerformanceRanking } from '@/types'

const activeTab = ref('config')

// ========== 配置 Tab ==========
const configLoading = ref(false)
const configList = ref<PerformanceConfig[]>([])
const editingConfigId = ref<number | null>(null)
const editingCoefficient = ref(0)

async function fetchConfigs() {
  configLoading.value = true
  try {
    const res = await getPerformanceConfigs()
    configList.value = res.data
  } catch {
    configList.value = []
  } finally {
    configLoading.value = false
  }
}

function startEditConfig(row: PerformanceConfig) {
  editingConfigId.value = row.id
  editingCoefficient.value = row.coefficient
}

function cancelEditConfig() {
  editingConfigId.value = null
}

async function saveConfig(row: PerformanceConfig) {
  try {
    await updatePerformanceConfigs({
      configs: [{ id: row.id, coefficient: editingCoefficient.value } as Partial<PerformanceConfig>],
    })
    row.coefficient = editingCoefficient.value
    editingConfigId.value = null
    ElMessage.success('保存成功')
  } catch { /* ignore */ }
}

// ========== 记录 Tab ==========
const recordLoading = ref(false)
const recordList = ref<PerformanceRecord[]>([])
const recordTotal = ref(0)
const recordDateRange = ref<[string, string] | null>(null)

const recordParams = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  period_type: undefined as string | undefined,
  start_date: undefined as string | undefined,
  end_date: undefined as string | undefined,
})

async function fetchRecords() {
  recordLoading.value = true
  try {
    const res = await getPerformanceRecords(recordParams)
    recordList.value = res.data.list
    recordTotal.value = res.data.pagination.total
  } catch {
    recordList.value = []
  } finally {
    recordLoading.value = false
  }
}

function handleRecordSearch() {
  recordParams.page = 1
  fetchRecords()
}

function handleRecordDateChange(val: [string, string] | null) {
  if (val) {
    recordParams.start_date = val[0]
    recordParams.end_date = val[1]
  } else {
    recordParams.start_date = undefined
    recordParams.end_date = undefined
  }
  handleRecordSearch()
}

// ========== 排名 Tab ==========
const rankingLoading = ref(false)
const rankingList = ref<PerformanceRanking[]>([])

const rankingParams = reactive({
  period_type: 'monthly',
  period_start: formatDate(new Date()),
})

const maxPerformance = computed(() => {
  if (!rankingList.value.length) return 0
  return Math.max(...rankingList.value.map(r => r.total_performance))
})

async function fetchRanking() {
  rankingLoading.value = true
  try {
    const res = await getPerformanceRanking(rankingParams)
    rankingList.value = res.data
  } catch {
    rankingList.value = []
  } finally {
    rankingLoading.value = false
  }
}

// ========== 触发计算 ==========
const calcDialogVisible = ref(false)
const calcLoading = ref(false)
const calcForm = reactive({
  period_type: 'daily',
  period_start: formatDate(new Date()),
  period_end: formatDate(new Date()),
})

function handleTriggerCalculation() {
  calcDialogVisible.value = true
}

async function submitCalculation() {
  calcLoading.value = true
  try {
    await triggerCalculation(calcForm)
    ElMessage.success('计算任务已触发')
    calcDialogVisible.value = false
    // 刷新当前 Tab
    handleTabChange(activeTab.value)
  } finally {
    calcLoading.value = false
  }
}

// ========== 导出 ==========
async function handleExport() {
  await ElMessageBox.confirm('确认导出绩效数据？', '导出确认', { type: 'info' })
  try {
    const res = await exportPerformance({
      period_type: activeTab.value === 'ranking' ? rankingParams.period_type : recordParams.period_type || 'monthly',
      date: activeTab.value === 'ranking' ? rankingParams.date : recordParams.start_date || formatDate(new Date()),
    })
    downloadFile(res as unknown as Blob, `绩效数据_${formatDate(new Date())}.xlsx`)
    ElMessage.success('导出成功')
  } catch { /* ignore */ }
}

// ========== Tab 切换 ==========
function handleTabChange(tab: string | number) {
  if (tab === 'config') fetchConfigs()
  else if (tab === 'records') fetchRecords()
  else if (tab === 'ranking') fetchRanking()
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style lang="scss" scoped>
.header-actions {
  display: flex;
  gap: 8px;
}

.coefficient {
  font-size: 16px;
  font-weight: 600;
  color: #409EFF;
}

.performance-value {
  font-weight: 600;
  color: #67C23A;
}

.detail-expand {
  padding: 8px 16px 8px 48px;
}

.rank-medal {
  font-size: 24px;
}

.rank-number {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-placeholder);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
