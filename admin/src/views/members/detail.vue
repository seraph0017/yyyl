<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>会员详情</h3>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-skeleton :loading="loading" :rows="8" animated>
        <template #default>
          <el-descriptions :column="3" border class="mb-20">
            <el-descriptions-item label="昵称">{{ member.nickname }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ member.phone }}</el-descriptions-item>
            <el-descriptions-item label="会员等级">
              <el-tag :type="member.member_level === 'annual' ? 'warning' : 'info'">
                {{ { normal: '普通', annual: '年卡', vip: 'VIP' }[member.member_level as string] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="消费总额">¥{{ formatPrice(member.total_spent || 0) }}</el-descriptions-item>
            <el-descriptions-item label="订单数">{{ member.order_count }}</el-descriptions-item>
            <el-descriptions-item label="积分余额">{{ member.points_balance }}</el-descriptions-item>
          </el-descriptions>

          <!-- 年卡信息 -->
          <div v-if="member.annual_card" class="mb-20">
            <h4 class="mb-8">年卡信息</h4>
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

          <!-- 次数卡信息 -->
          <div v-if="member.times_cards?.length" class="mb-20">
            <h4 class="mb-8">次数卡</h4>
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

          <!-- 积分操作 -->
          <div>
            <h4 class="mb-8">积分调整</h4>
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
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMemberDetail, adjustPoints } from '@/api/member'
import { formatPrice } from '@/utils'
import type { MemberInfo } from '@/types'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const member = ref<Partial<MemberInfo>>({})
const pointsAdjust = ref(0)
const adjustReason = ref('')

async function fetchData() {
  try {
    const res = await getMemberDetail(Number(route.params.id))
    member.value = res.data
  } catch {} finally { loading.value = false }
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

onMounted(fetchData)
</script>
