<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>订单详情</h3>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-skeleton :loading="loading" :rows="10" animated>
        <template #default>
          <!-- 基本信息 -->
          <el-descriptions :column="3" border class="mb-20">
            <el-descriptions-item label="订单号">{{ order.order_no }}</el-descriptions-item>
            <el-descriptions-item label="订单状态">
              <el-tag :type="(orderStatusMap[order.status]?.type as any)" size="small">
                {{ orderStatusMap[order.status]?.label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="支付状态">
              <el-tag :type="(paymentStatusMap[order.payment_status]?.type as any)" size="small">
                {{ paymentStatusMap[order.payment_status]?.label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="用户昵称">{{ order.user_nickname }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ order.user_phone }}</el-descriptions-item>
            <el-descriptions-item label="支付方式">{{ order.payment_method }}</el-descriptions-item>
            <el-descriptions-item label="订单金额"><span class="price">¥{{ formatPrice(order.total_amount) }}</span></el-descriptions-item>
            <el-descriptions-item label="实付金额">¥{{ formatPrice(order.paid_amount) }}</el-descriptions-item>
            <el-descriptions-item label="退款金额">¥{{ formatPrice(order.refund_amount) }}</el-descriptions-item>
            <el-descriptions-item label="下单时间">{{ formatDateTime(order.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="支付时间">{{ order.paid_at ? formatDateTime(order.paid_at) : '--' }}</el-descriptions-item>
            <el-descriptions-item label="过期时间">{{ formatDateTime(order.expire_at) }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="3">{{ order.remark || '无' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 商品列表 -->
          <h4 class="mb-16">商品明细</h4>
          <el-table :data="order.items" border class="mb-20">
            <el-table-column prop="product_name" label="商品名称" />
            <el-table-column label="品类" width="100">
              <template #default="{ row }">{{ getCategoryName(row.product_category) }}</template>
            </el-table-column>
            <el-table-column prop="sku_name" label="规格" width="120" />
            <el-table-column prop="quantity" label="数量" width="80" align="center" />
            <el-table-column label="单价" width="100" align="right">
              <template #default="{ row }">¥{{ formatPrice(row.unit_price) }}</template>
            </el-table-column>
            <el-table-column label="实际价" width="100" align="right">
              <template #default="{ row }"><span class="price">¥{{ formatPrice(row.actual_price) }}</span></template>
            </el-table-column>
            <el-table-column label="日期" width="120">
              <template #default="{ row }">{{ row.date || '--' }}</template>
            </el-table-column>
            <el-table-column label="票务状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.ticket_status" size="small" :type="row.ticket_status === 'used' ? 'success' : row.ticket_status === 'unused' ? 'warning' : 'info'">
                  {{ { unused: '未使用', used: '已使用', expired: '已过期', refunded: '已退票' }[row.ticket_status] }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-skeleton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getOrderDetail } from '@/api/order'
import { formatPrice, formatDateTime, getCategoryName, orderStatusMap, paymentStatusMap } from '@/utils'
import type { Order } from '@/types'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const order = ref<Partial<Order>>({ items: [] })

async function fetchOrder() {
  const id = Number(route.params.id)
  try {
    const res = await getOrderDetail(id)
    order.value = res.data
  } catch {} finally {
    loading.value = false
  }
}

onMounted(fetchOrder)
</script>

<style lang="scss" scoped>
.price { font-weight: 700; color: var(--color-accent); letter-spacing: 0.5px; }
</style>
