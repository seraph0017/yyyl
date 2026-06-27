<template>
  <div class="page-container membership-page">
    <div class="card-box">
      <div class="page-header">
        <div>
          <h2>会员卡</h2>
          <p>统一管理会员卡总览、年卡配置、次数卡配置与持卡明细。</p>
        </div>
        <div class="page-header__actions">
          <el-button @click="$router.push('/annual-cards')">
            <el-icon><Ticket /></el-icon>年卡配置
          </el-button>
          <el-button @click="$router.push('/times-cards')">
            <el-icon><Ticket /></el-icon>次数卡配置
          </el-button>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="workspace-tabs">
        <el-tab-pane label="会员卡总览" name="overview">
          <div class="toolbar">
            <el-input
              v-model.trim="params.keyword"
              placeholder="搜索昵称/手机号"
              clearable
              style="width: 240px"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select v-model="params.has_membership_card" clearable placeholder="是否持卡" style="width: 130px" @change="handleSearch">
              <el-option label="有会员卡" :value="true" />
              <el-option label="无会员卡" :value="false" />
            </el-select>
            <el-select v-model="params.member_level" clearable placeholder="会员等级" style="width: 130px" @change="handleSearch">
              <el-option label="普通会员" value="normal" />
              <el-option label="年卡会员" value="annual" />
              <el-option label="VIP" value="vip" />
            </el-select>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </div>

          <el-table :data="tableData" v-loading="loading" stripe>
            <el-table-column prop="user_id" label="用户ID" width="90" />
            <el-table-column label="用户信息" min-width="220">
              <template #default="{ row }">
                <div class="member-cell">
                  <el-avatar :size="36" :src="row.avatar">{{ row.nickname?.charAt(0) }}</el-avatar>
                  <div class="member-cell__meta">
                    <div class="member-cell__name">{{ row.nickname }}</div>
                    <div class="member-cell__phone">{{ row.phone }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="会员卡" min-width="220">
              <template #default="{ row }">
                <div class="card-summary">
                  <el-tag :type="row.has_membership_card ? 'success' : 'info'" size="small">
                    {{ row.has_membership_card ? '持卡' : '未持卡' }}
                  </el-tag>
                  <span>{{ row.membership_card_count || 0 }} 张</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="卡种" min-width="240">
              <template #default="{ row }">
                <div class="tag-line">
                  <el-tag
                    v-for="card in row.membership_cards || []"
                    :key="card.id"
                    :type="card.card_kind === 'annual' ? 'warning' : 'primary'"
                    effect="plain"
                    size="small"
                  >
                    {{ card.config_name }} · {{ card.card_kind === 'annual' ? '年卡' : '次数卡' }}
                  </el-tag>
                  <span v-if="!row.membership_cards?.length" class="muted">-</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="消费总额" width="120" align="right">
              <template #default="{ row }">¥{{ formatPrice(row.total_spent) }}</template>
            </el-table-column>
            <el-table-column prop="order_count" label="订单数" width="80" align="center" />
            <el-table-column label="注册时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.registered_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-tooltip content="详情" placement="top" :show-after="400">
                    <el-button class="action-btn action-btn--view" circle size="small" @click="$router.push(`/members/${row.user_id}`)">
                      <el-icon><View /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="params.page"
              v-model:page-size="params.page_size"
              :total="total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @size-change="fetchData"
              @current-change="fetchData"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="年卡" name="annual">
          <div class="toolbar">
            <el-button type="primary" @click="$router.push('/annual-cards')">进入年卡配置</el-button>
          </div>
          <el-table :data="annualCards" v-loading="cardLoading" stripe>
            <el-table-column prop="config_name" label="卡种" min-width="180" />
            <el-table-column label="使用模式" min-width="130">
              <template #default>按天无限次</template>
            </el-table-column>
            <el-table-column label="有效期" min-width="210">
              <template #default="{ row }">{{ row.valid_from || '-' }} ~ {{ row.valid_until || '-' }}</template>
            </el-table-column>
            <el-table-column label="剩余天数" width="100" align="center">
              <template #default="{ row }">{{ row.remaining_days ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="适用商品" min-width="220">
              <template #default="{ row }">{{ formatProducts(row.applicable_products) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : row.status === 'expired' ? 'info' : 'warning'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="次数卡" name="times">
          <div class="toolbar">
            <el-button type="primary" @click="$router.push('/times-cards')">进入次数卡配置</el-button>
          </div>
          <el-table :data="timesCards" v-loading="cardLoading" stripe>
            <el-table-column prop="config_name" label="卡种" min-width="180" />
            <el-table-column label="使用模式" min-width="130">
              <template #default>按次扣减</template>
            </el-table-column>
            <el-table-column label="有效期" min-width="210">
              <template #default="{ row }">{{ row.valid_from || '-' }} ~ {{ row.valid_until || '-' }}</template>
            </el-table-column>
            <el-table-column label="剩余次数" width="100" align="center">
              <template #default="{ row }">{{ row.remaining_times ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="适用商品" min-width="220">
              <template #default="{ row }">{{ formatProducts(row.applicable_products) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : row.status === 'expired' ? 'info' : 'warning'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Ticket, View } from '@element-plus/icons-vue'
import { getMembers, getMembershipCards } from '@/api/member'
import { formatPrice, formatDateTime } from '@/utils'
import type { MemberInfo, MemberSearchParams, MembershipCardInfo } from '@/types'

const router = useRouter()
const activeTab = ref('overview')
const loading = ref(false)
const cardLoading = ref(false)
const tableData = ref<MemberInfo[]>([])
const annualCards = ref<MembershipCardInfo[]>([])
const timesCards = ref<MembershipCardInfo[]>([])
const total = ref(0)
const params = reactive<MemberSearchParams>({ page: 1, page_size: 20, keyword: '', has_membership_card: undefined })

async function fetchData() {
  loading.value = true
  try {
    const res = await getMembers(params)
    tableData.value = res.data.list
    total.value = res.data.pagination.total
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

async function fetchCards() {
  cardLoading.value = true
  try {
    const res = await getMembershipCards({ page: 1, page_size: 200 })
    const cards = res.data.list || []
    annualCards.value = cards.filter(card => card.card_kind === 'annual')
    timesCards.value = cards.filter(card => card.card_kind === 'times')
  } catch {
    annualCards.value = []
    timesCards.value = []
  } finally {
    cardLoading.value = false
  }
}

function handleSearch() {
  params.page = 1
  fetchData()
}

function resetFilter() {
  params.keyword = ''
  params.member_level = undefined
  params.has_membership_card = undefined
  handleSearch()
}

function formatProducts(products: string[]) {
  return products?.length ? products.join(' / ') : '全部商品'
}

onMounted(() => {
  fetchData()
  fetchCards()
})
</script>

<style lang="scss" scoped>
.membership-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
    margin-bottom: 16px;

    h2 {
      margin: 0 0 6px;
      font-size: 20px;
      color: var(--color-text);
    }

    p {
      margin: 0;
      color: var(--color-text-secondary);
    }
  }

  .page-header__actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
}

.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.member-cell {
  display: flex;
  align-items: center;
  gap: 10px;

  &__name {
    font-weight: 600;
  }

  &__phone {
    font-size: 12px;
    color: var(--color-text-placeholder);
  }
}

.card-summary {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tag-line {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}
</style>
