<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-16">
        <h3>营地日历</h3>
        <el-date-picker v-model="monthValue" type="month" placeholder="选择月份" value-format="YYYY-MM" @change="fetchData" />
      </div>

      <div v-loading="loading" class="calendar-grid">
        <!-- 表头：日期 -->
        <div class="calendar-header">
          <div class="calendar-cell product-name-header">商品 / 日期</div>
          <div v-for="date in dates" :key="date" class="calendar-cell date-header" :class="{ weekend: isWeekend(date) }">
            <div class="date-num">{{ date.split('-')[2] }}</div>
            <div class="date-weekday">{{ getWeekday(date) }}</div>
          </div>
        </div>

        <!-- 数据行 -->
        <div v-for="product in productRows" :key="product.product_id" class="calendar-row">
          <div class="calendar-cell product-name">{{ product.product_name }}</div>
          <div
            v-for="date in dates"
            :key="date"
            class="calendar-cell data-cell"
            :class="getCellClass(product.product_id, date)"
          >
            <template v-if="getCellData(product.product_id, date)">
              <div class="cell-stock">{{ getCellData(product.product_id, date)!.available_stock }}/{{ getCellData(product.product_id, date)!.total_stock }}</div>
              <div class="cell-price">¥{{ formatPrice(getCellData(product.product_id, date)!.price) }}</div>
            </template>
            <span v-else class="cell-empty">—</span>
          </div>
        </div>

        <el-empty v-if="!productRows.length && !loading" description="暂无数据" />
      </div>

      <div class="calendar-legend mt-16">
        <span class="legend-item"><span class="legend-dot available" /> 可预订</span>
        <span class="legend-item"><span class="legend-dot low" /> 库存紧张</span>
        <span class="legend-item"><span class="legend-dot sold-out" /> 已售罄</span>
        <span class="legend-item"><span class="legend-dot closed" /> 未开放</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { getCalendarData } from '@/api/product'
import { formatPrice } from '@/utils'
import type { CalendarItem } from '@/types'

const loading = ref(false)
const monthValue = ref(dayjs().format('YYYY-MM'))
const calendarData = ref<CalendarItem[]>([])

const dates = computed(() => {
  const start = dayjs(monthValue.value).startOf('month')
  const end = dayjs(monthValue.value).endOf('month')
  const result: string[] = []
  let current = start
  while (current.isBefore(end) || current.isSame(end, 'day')) {
    result.push(current.format('YYYY-MM-DD'))
    current = current.add(1, 'day')
  }
  return result
})

const productRows = computed(() => {
  const map = new Map<number, { product_id: number; product_name: string }>()
  calendarData.value.forEach(item => {
    if (!map.has(item.product_id)) {
      map.set(item.product_id, { product_id: item.product_id, product_name: item.product_name })
    }
  })
  return Array.from(map.values())
})

function getCellData(productId: number, date: string): CalendarItem | undefined {
  return calendarData.value.find(item => item.product_id === productId && item.date === date)
}

function getCellClass(productId: number, date: string): string {
  const data = getCellData(productId, date)
  if (!data) return 'closed'
  if (data.status === 'closed') return 'closed'
  if (data.status === 'sold_out' || data.available_stock === 0) return 'sold-out'
  if (data.available_stock <= 3) return 'low'
  return 'available'
}

function isWeekend(date: string): boolean {
  const d = dayjs(date).day()
  return d === 0 || d === 6
}

function getWeekday(date: string): string {
  return ['日', '一', '二', '三', '四', '五', '六'][dayjs(date).day()]
}

async function fetchData() {
  loading.value = true
  try {
    const start = dayjs(monthValue.value).startOf('month').format('YYYY-MM-DD')
    const end = dayjs(monthValue.value).endOf('month').format('YYYY-MM-DD')
    const res = await getCalendarData({ date_start: start, date_end: end })
    calendarData.value = res.data
  } catch {
    calendarData.value = []
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.calendar-grid {
  overflow-x: auto;
}

.calendar-header, .calendar-row {
  display: flex;
  min-width: fit-content;
}

.calendar-cell {
  min-width: 72px;
  padding: 6px 4px;
  text-align: center;
  border: 1px solid #ebeef5;
  font-size: 12px;
}

.product-name-header, .product-name {
  min-width: 140px;
  max-width: 140px;
  text-align: left;
  padding: 8px;
  font-weight: 500;
  background: #fafafa;
  position: sticky;
  left: 0;
  z-index: 1;
}

.date-header {
  background: #f5f7fa;
  &.weekend { background: #fff3e0; }
  .date-num { font-weight: 600; font-size: 14px; }
  .date-weekday { font-size: 11px; color: #909399; }
}

.data-cell {
  cursor: pointer;
  transition: background 0.2s;
  &:hover { filter: brightness(0.95); }

  &.available { background: #e8f5e9; }
  &.low { background: #fff3e0; }
  &.sold-out { background: #ffebee; }
  &.closed { background: #f5f5f5; color: #c0c4cc; }

  .cell-stock { font-weight: 600; font-size: 13px; }
  .cell-price { color: #909399; font-size: 11px; }
  .cell-empty { color: #dcdfe6; }
}

.calendar-legend {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #606266;

  .legend-item { display: flex; align-items: center; gap: 6px; }
  .legend-dot {
    width: 12px; height: 12px; border-radius: 2px;
    &.available { background: #e8f5e9; border: 1px solid #4CAF50; }
    &.low { background: #fff3e0; border: 1px solid #FF9800; }
    &.sold-out { background: #ffebee; border: 1px solid #F44336; }
    &.closed { background: #f5f5f5; border: 1px solid #dcdfe6; }
  }
}
</style>
