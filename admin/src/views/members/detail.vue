<template>
  <div class="page-container member-detail-page">
    <div class="card-box">
      <div class="page-header">
        <div>
          <h2>会员卡详情</h2>
          <p>聚合查看该会员持有的会员卡明细，兼容旧字段展示。</p>
        </div>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-skeleton :loading="loading" :rows="8" animated>
        <template #default>
          <el-descriptions :column="3" border class="mb-20">
            <el-descriptions-item label="昵称">{{ member.nickname }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ member.phone }}</el-descriptions-item>
            <el-descriptions-item label="会员卡数量">{{ member.membership_card_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="持卡状态">
              <el-tag :type="member.has_membership_card ? 'success' : 'info'">
                {{ member.has_membership_card ? '有会员卡' : '暂无会员卡' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="会员等级">
              <el-tag :type="member.member_level === 'annual' ? 'warning' : member.member_level === 'vip' ? 'danger' : 'info'">
                {{ { normal: '普通', annual: '年卡', vip: 'VIP' }[member.member_level as string] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="消费总额">¥{{ formatPrice(member.total_spent || 0) }}</el-descriptions-item>
            <el-descriptions-item label="订单数">{{ member.order_count }}</el-descriptions-item>
            <el-descriptions-item label="积分余额">{{ member.points_balance }}</el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ formatDateTime(member.registered_at || '') }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="membershipCards.length" class="mb-20">
            <h4 class="section-title">会员卡明细</h4>
            <el-table :data="membershipCards" border size="small">
              <el-table-column prop="config_name" label="卡种" min-width="160" />
              <el-table-column label="卡类型" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.card_kind === 'annual' ? 'warning' : 'primary'" size="small">
                    {{ row.card_kind === 'annual' ? '年卡' : '次数卡' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="使用模式" min-width="120">
                <template #default="{ row }">{{ row.use_mode }}</template>
              </el-table-column>
              <el-table-column label="有效期" min-width="200">
                <template #default="{ row }">
                  {{ row.valid_from || '-' }} ~ {{ row.valid_until || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="剩余天数" width="100" align="center">
                <template #default="{ row }">{{ row.remaining_days ?? '-' }}</template>
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
          </div>

          <div v-if="member.annual_card" class="mb-20">
            <h4 class="section-title">兼容持卡字段</h4>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="套餐名称">{{ member.annual_card.config_name }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="member.annual_card.status === 'active' ? 'success' : 'danger'">{{ member.annual_card.status }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="每日限额">{{ member.annual_card.daily_limit }}份</el-descriptions-item>
              <el-descriptions-item label="有效期">{{ member.annual_card.start_date }} ~ {{ member.annual_card.end_date }}</el-descriptions-item>
              <el-descriptions-item label="已使用天数">{{ member.annual_card.total_used_days }}天</el-descriptions-item>
            </el-descriptions>
          </div>

          <div v-if="member.times_cards?.length" class="mb-20">
            <h4 class="section-title">兼容持卡字段</h4>
            <el-table :data="member.times_cards" border size="small">
              <el-table-column prop="config_name" label="卡名称" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="次数" width="150">
                <template #default="{ row }">{{ row.remaining_times }} / {{ row.total_times }}</template>
              </el-table-column>
              <el-table-column prop="expire_date" label="过期日期" width="120" />
            </el-table>
          </div>

          <div>
            <h4 class="section-title">积分调整</h4>
            <el-form :inline="true">
              <el-form-item>
                <el-input-number v-model="pointsAdjust" :step="100" />
              </el-form-item>
              <el-form-item>
                <el-input v-model="adjustReason" placeholder="调整原因" style="width: 200px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleAdjustPoints">调整积分</el-button>
              </el-form-item>
            </el-form>
          </div>
        </template>
      </el-skeleton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMemberDetail, adjustPoints } from '@/api/member'
import { formatPrice, formatDateTime } from '@/utils'
import type { MemberInfo, MembershipCardInfo } from '@/types'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const member = ref<Partial<MemberInfo>>({})
const pointsAdjust = ref(0)
const adjustReason = ref('')

const membershipCards = computed<MembershipCardInfo[]>(() => member.value.membership_cards || [])

async function fetchData() {
  try {
    const res = await getMemberDetail(Number(route.params.id))
    member.value = res.data
  } catch {
    member.value = {}
  } finally {
    loading.value = false
  }
}

async function handleAdjustPoints() {
  if (!pointsAdjust.value || !adjustReason.value) {
    ElMessage.warning('请填写积分数和原因')
    return
  }
  try {
    await adjustPoints(Number(route.params.id), { points: pointsAdjust.value, reason: adjustReason.value })
    ElMessage.success('积分调整成功')
    fetchData()
  } catch {}
}

function formatProducts(products: string[]) {
  return products?.length ? products.join(' / ') : '全部商品'
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;

  h2 {
    margin: 0 0 6px;
    font-size: 20px;
  }

  p {
    margin: 0;
    color: var(--color-text-secondary);
  }
}

.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--color-text);
}
</style>
