<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>会员管理</h3>
        <div>
          <el-button @click="router.push('/annual-cards')"><el-icon><Ticket /></el-icon>年卡管理</el-button>
          <el-button @click="router.push('/times-cards')"><el-icon><Ticket /></el-icon>次数卡管理</el-button>
        </div>
      </div>

      <el-form :inline="true" class="mb-16">
        <el-form-item>
          <el-input v-model="params.keyword" placeholder="搜索昵称/手机号" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-select v-model="params.member_level" placeholder="会员等级" clearable @change="handleSearch">
            <el-option label="普通会员" value="normal" />
            <el-option label="年卡会员" value="annual" />
            <el-option label="VIP" value="vip" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column label="用户信息" min-width="200">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <el-avatar :size="36" :src="row.avatar">{{ row.nickname?.charAt(0) }}</el-avatar>
              <div>
                <div>{{ row.nickname }}</div>
                <div style="font-size: 12px; color: #909399;">{{ row.phone }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="会员等级" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.member_level === 'annual' ? 'warning' : row.member_level === 'vip' ? 'danger' : 'info'" size="small">
              {{ { normal: '普通', annual: '年卡', vip: 'VIP' }[row.member_level as string] || row.member_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="消费总额" width="120" align="right">
          <template #default="{ row }">¥{{ formatPrice(row.total_spent) }}</template>
        </el-table-column>
        <el-table-column prop="order_count" label="订单数" width="80" align="center" />
        <el-table-column label="积分余额" width="100" align="right">
          <template #default="{ row }">{{ row.points_balance }}</template>
        </el-table-column>
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.registered_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="router.push(`/members/${row.user_id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="params.page" v-model:page-size="params.page_size" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchData" @current-change="fetchData" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Ticket } from '@element-plus/icons-vue'
import { getMembers } from '@/api/member'
import { formatPrice, formatDateTime } from '@/utils'
import type { MemberInfo, MemberSearchParams } from '@/types'

const router = useRouter()
const loading = ref(false)
const tableData = ref<MemberInfo[]>([])
const total = ref(0)
const params = reactive<MemberSearchParams>({ page: 1, page_size: 20, keyword: '' })

async function fetchData() {
  loading.value = true
  try { const res = await getMembers(params); tableData.value = res.data.items; total.value = res.data.total }
  catch { tableData.value = [] }
  finally { loading.value = false }
}

function handleSearch() { params.page = 1; fetchData() }
onMounted(fetchData)
</script>

<style lang="scss" scoped>
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
