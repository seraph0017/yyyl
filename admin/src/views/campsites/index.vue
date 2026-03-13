<template>
  <div class="page-container">
    <!-- 统计概览卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_campsites }}</div>
        <div class="stat-label">营位总数</div>
      </div>
      <div class="stat-card stat-success">
        <div class="stat-value">{{ stats.on_sale }}</div>
        <div class="stat-label">在售营位</div>
      </div>
      <div class="stat-card stat-primary">
        <div class="stat-value">{{ stats.today_inventory.available }}</div>
        <div class="stat-label">今日可预订</div>
      </div>
      <div class="stat-card stat-warning">
        <div class="stat-value">{{ stats.today_inventory.occupancy_rate }}%</div>
        <div class="stat-label">今日入住率</div>
      </div>
    </div>

    <div class="card-box">
      <!-- 搜索栏 -->
      <div class="flex-between mb-16">
        <div class="search-bar">
          <el-input v-model="searchParams.keyword" placeholder="搜索营位名称/区域/编号" clearable style="width: 240px" @clear="handleSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="searchParams.campsite_type" placeholder="营位类型" clearable style="width: 140px" @change="handleSearch">
            <el-option label="日常营位" value="daily_camping" />
            <el-option label="活动营位" value="event_camping" />
          </el-select>
          <el-select v-model="searchParams.area" placeholder="区域" clearable style="width: 120px" @change="handleSearch">
            <el-option v-for="a in areas" :key="a" :label="a" :value="a" />
          </el-select>
          <el-select v-model="searchParams.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
            <el-option label="在售" value="on_sale" />
            <el-option label="下架" value="off_sale" />
            <el-option label="草稿" value="draft" />
          </el-select>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>搜索
          </el-button>
        </div>
        <el-button type="primary" @click="router.push('/campsites/create')">
          <el-icon><Plus /></el-icon>新增营位
        </el-button>
      </div>

      <!-- 属性快捷筛选 -->
      <div class="filter-tags mb-12">
        <el-check-tag :checked="searchParams.has_electricity === true" @change="toggleFilter('has_electricity')">⚡ 有电</el-check-tag>
        <el-check-tag :checked="searchParams.has_platform === true" @change="toggleFilter('has_platform')">🪵 有平台</el-check-tag>
      </div>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="营位信息" min-width="280">
          <template #default="{ row }">
            <div class="campsite-info">
              <el-image :src="row.images?.[0]?.url" class="campsite-cover" fit="cover">
                <template #error><div class="image-placeholder"><el-icon><Place /></el-icon></div></template>
              </el-image>
              <div>
                <div class="campsite-name">{{ row.name }}</div>
                <div class="campsite-meta">
                  <el-tag size="small" :type="row.type === 'daily_camping' ? '' : 'warning'">{{ row.type_label }}</el-tag>
                  <span v-if="row.area" class="area-badge">{{ row.area }}</span>
                  <span v-if="row.position_name" class="position-badge">{{ row.position_name }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="属性" width="120" align="center">
          <template #default="{ row }">
            <div class="attr-icons">
              <el-tooltip v-if="row.has_electricity" content="有电" placement="top">
                <span class="attr-icon active">⚡</span>
              </el-tooltip>
              <el-tooltip v-if="row.has_platform" content="有木平台" placement="top">
                <span class="attr-icon active">🪵</span>
              </el-tooltip>
              <el-tooltip v-if="row.sun_exposure" :content="sunExposureLabel(row.sun_exposure)" placement="top">
                <span class="attr-icon active">{{ row.sun_exposure === 'sunny' ? '☀️' : row.sun_exposure === 'shaded' ? '🌳' : '⛅' }}</span>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="容量" width="80" align="center">
          <template #default="{ row }">
            <span>{{ row.max_persons || '-' }}人</span>
          </template>
        </el-table-column>
        <el-table-column label="基础价" width="100" align="right">
          <template #default="{ row }">
            <span class="price">¥{{ row.base_price }}</span>
          </template>
        </el-table-column>
        <el-table-column label="7天库存" width="140" align="center">
          <template #default="{ row }">
            <div class="stock-info">
              <span :class="['stock-available', row.stock_summary.available_7d <= 3 ? 'stock-low' : '']">
                {{ row.stock_summary.available_7d }}
              </span>
              <span class="stock-divider">/</span>
              <span class="stock-total">{{ row.stock_summary.total_7d }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'on_sale' ? 'success' : row.status === 'draft' ? 'info' : 'danger'" size="small">
              {{ row.status === 'on_sale' ? '在售' : row.status === 'draft' ? '草稿' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="router.push(`/campsites/${row.id}/edit`)">编辑</el-button>
            <el-button text type="primary" @click="router.push(`/campsites/${row.id}/inventory`)">库存</el-button>
            <el-button text :type="row.status === 'on_sale' ? 'warning' : 'success'" @click="handleToggleStatus(row)">
              {{ row.status === 'on_sale' ? '下架' : '上架' }}
            </el-button>
            <el-popconfirm title="确定删除该营位？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="searchParams.page"
          v-model:page-size="searchParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus, Place } from '@element-plus/icons-vue'
import { getCampsites, getCampsiteStats, updateCampsiteStatus, deleteCampsite } from '@/api/campsite'
import type { CampsiteListItem, CampsiteSearchParams, CampsiteStatsOverview } from '@/types/campsite'

const router = useRouter()
const loading = ref(false)
const tableData = ref<CampsiteListItem[]>([])
const total = ref(0)
const areas = ref<string[]>([])

const stats = ref<CampsiteStatsOverview>({
  total_campsites: 0,
  on_sale: 0,
  type_stats: {
    daily_camping: { total: 0, on_sale: 0, off_sale: 0, draft: 0 },
    event_camping: { total: 0, on_sale: 0, off_sale: 0, draft: 0 },
  },
  today_inventory: { total: 0, available: 0, sold: 0, occupancy_rate: 0 },
})

const searchParams = reactive<CampsiteSearchParams & { page: number; page_size: number }>({
  page: 1,
  page_size: 20,
  keyword: '',
  campsite_type: undefined,
  area: undefined,
  status: undefined,
  has_electricity: undefined,
  has_platform: undefined,
})

function sunExposureLabel(val: string) {
  return val === 'sunny' ? '全日照' : val === 'shaded' ? '树荫遮蔽' : '半日照'
}

function toggleFilter(field: 'has_electricity' | 'has_platform') {
  searchParams[field] = searchParams[field] === true ? undefined : true
  handleSearch()
}

async function fetchStats() {
  try {
    const res = await getCampsiteStats()
    stats.value = res.data
  } catch {}
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getCampsites(searchParams)
    tableData.value = res.data.items
    total.value = res.data.total
    areas.value = res.data.areas
  } catch {
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  searchParams.page = 1
  fetchData()
}

async function handleToggleStatus(row: CampsiteListItem) {
  const newStatus = row.status === 'on_sale' ? 'off_sale' : 'on_sale'
  try {
    await updateCampsiteStatus(row.id, newStatus)
    ElMessage.success(`已${newStatus === 'on_sale' ? '上架' : '下架'}`)
    row.status = newStatus as any
    fetchStats()
  } catch {}
}

async function handleDelete(id: number) {
  try {
    await deleteCampsite(id)
    ElMessage.success('删除成功')
    fetchData()
    fetchStats()
  } catch {}
}

onMounted(() => {
  fetchData()
  fetchStats()
})
</script>

<style lang="scss" scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;

  .stat-card {
    background: #fff;
    border-radius: 8px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #303133;
      margin-bottom: 4px;
    }

    .stat-label {
      font-size: 13px;
      color: #909399;
    }

    &.stat-success .stat-value { color: #67C23A; }
    &.stat-primary .stat-value { color: #409EFF; }
    &.stat-warning .stat-value { color: #E6A23C; }
  }
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-tags {
  display: flex;
  gap: 8px;
}

.campsite-info {
  display: flex;
  align-items: center;
  gap: 12px;

  .campsite-cover {
    width: 48px;
    height: 48px;
    border-radius: 6px;
    flex-shrink: 0;
  }

  .image-placeholder {
    width: 48px;
    height: 48px;
    background: #e8f5e9;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #4CAF50;
    border-radius: 6px;
    font-size: 20px;
  }

  .campsite-name {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 4px;
    color: #303133;
  }

  .campsite-meta {
    display: flex;
    align-items: center;
    gap: 6px;

    .area-badge, .position-badge {
      font-size: 12px;
      color: #909399;
      background: #f5f7fa;
      padding: 1px 6px;
      border-radius: 3px;
    }
  }
}

.attr-icons {
  display: flex;
  gap: 4px;
  justify-content: center;

  .attr-icon {
    font-size: 16px;
    opacity: 0.4;
    &.active { opacity: 1; }
  }
}

.price {
  font-weight: 600;
  color: #F44336;
}

.stock-info {
  .stock-available {
    font-weight: 600;
    color: #67C23A;
    &.stock-low { color: #E6A23C; }
  }
  .stock-divider { color: #c0c4cc; margin: 0 2px; }
  .stock-total { color: #909399; }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
