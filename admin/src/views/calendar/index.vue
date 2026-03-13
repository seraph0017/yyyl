<template>
  <div class="page-container">
    <div class="card-box calendar-page">
      <!-- 顶部操作栏 -->
      <div class="calendar-toolbar">
        <div class="toolbar-left">
          <h3 class="page-title">
            <el-icon class="title-icon"><Calendar /></el-icon>
            营地日历
          </h3>
          <el-tag type="info" size="small" effect="plain">{{ monthLabel }}</el-tag>
        </div>
        <div class="toolbar-right">
          <el-button-group class="month-nav">
            <el-button :icon="ArrowLeft" size="small" @click="changeMonth(-1)" />
            <el-button size="small" @click="goToday">今天</el-button>
            <el-button :icon="ArrowRight" size="small" @click="changeMonth(1)" />
          </el-button-group>
          <el-date-picker
            v-model="monthValue"
            type="month"
            placeholder="选择月份"
            value-format="YYYY-MM"
            size="small"
            style="width: 140px"
            @change="fetchData"
          />
        </div>
      </div>

      <!-- 图例 -->
      <div class="calendar-legend">
        <span class="legend-item"><span class="legend-dot available" />可预订</span>
        <span class="legend-item"><span class="legend-dot low" />库存紧张 (≤3)</span>
        <span class="legend-item"><span class="legend-dot sold-out" />已售罄</span>
        <span class="legend-item"><span class="legend-dot closed" />未开放</span>
      </div>

      <!-- 日历表格 -->
      <div v-loading="loading" class="calendar-wrapper">
        <div class="calendar-grid">
          <!-- 表头 -->
          <div class="calendar-header">
            <div class="cell-fixed product-name-header">
              <span>营位名称</span>
            </div>
            <div
              v-for="date in dates"
              :key="date"
              class="cell date-header"
              :class="{ weekend: isWeekend(date), today: isToday(date) }"
            >
              <div class="date-num">{{ date.split('-')[2] }}</div>
              <div class="date-weekday">{{ getWeekday(date) }}</div>
            </div>
          </div>

          <!-- 数据行 -->
          <div
            v-for="(product, idx) in productRows"
            :key="product.product_id"
            class="calendar-row"
            :class="{ 'row-even': idx % 2 === 0 }"
          >
            <div class="cell-fixed product-name" :title="product.product_name">
              <span class="name-text">{{ product.product_name }}</span>
            </div>
            <div
              v-for="date in dates"
              :key="date"
              class="cell data-cell"
              :class="[getCellClass(product.product_id, date), { 'col-weekend': isWeekend(date), 'col-today': isToday(date) }]"
            >
              <template v-if="getCellData(product.product_id, date)">
                <div class="cell-stock">
                  <span class="stock-available">{{ getCellData(product.product_id, date)!.available_stock }}</span>
                  <span class="stock-divider">/</span>
                  <span class="stock-total">{{ getCellData(product.product_id, date)!.total_stock }}</span>
                </div>
                <div class="cell-price">¥{{ formatPrice(getCellData(product.product_id, date)!.price) }}</div>
              </template>
              <span v-else class="cell-empty">-</span>
            </div>
          </div>

          <el-empty v-if="!productRows.length && !loading" description="暂无营位数据" :image-size="120" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Calendar, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getCalendarData } from '@/api/product'
import { formatPrice } from '@/utils'
import type { CalendarItem } from '@/types'

const loading = ref(false)
const monthValue = ref(dayjs().format('YYYY-MM'))
const calendarData = ref<CalendarItem[]>([])

const monthLabel = computed(() => dayjs(monthValue.value).format('YYYY年M月'))

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

function isToday(date: string): boolean {
  return date === dayjs().format('YYYY-MM-DD')
}

function getWeekday(date: string): string {
  return ['日', '一', '二', '三', '四', '五', '六'][dayjs(date).day()]
}

function changeMonth(offset: number) {
  monthValue.value = dayjs(monthValue.value).add(offset, 'month').format('YYYY-MM')
  fetchData()
}

function goToday() {
  monthValue.value = dayjs().format('YYYY-MM')
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const start = dayjs(monthValue.value).startOf('month').format('YYYY-MM-DD')
    const end = dayjs(monthValue.value).endOf('month').format('YYYY-MM-DD')
    const res: any = await getCalendarData({ date_start: start, date_end: end })
    const raw = res.data || res
    const products: Record<number, string> = {}
    if (Array.isArray(raw.products)) {
      raw.products.forEach((p: any) => { products[p.id] = p.name })
    }
    const cells = Array.isArray(raw.cells) ? raw.cells : []
    calendarData.value = cells.map((c: any) => ({
      product_id: c.product_id,
      product_name: products[c.product_id] || '',
      date: c.date,
      date_type: c.date_type || '',
      price: c.price ?? 0,
      total_stock: c.total ?? 0,
      available_stock: c.available ?? 0,
      booked_stock: c.sold ?? 0,
      status: c.status === 'open' ? (c.available === 0 ? 'sold_out' : 'open') : (c.status || 'closed'),
    }))
  } catch {
    calendarData.value = []
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.calendar-page {
  padding: 20px 24px;
}

/* ---------- 顶部工具栏 ---------- */
.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;

  .page-title {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
    color: #1d2129;
  }

  .title-icon {
    font-size: 20px;
    color: #4080ff;
  }
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;

  .month-nav .el-button {
    padding: 5px 10px;
  }
}

/* ---------- 图例 ---------- */
.calendar-legend {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  font-size: 12px;
  color: #86909c;

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    width: 14px;
    height: 14px;
    border-radius: 3px;

    &.available {
      background: linear-gradient(135deg, #d4f5e9, #b8ebdb);
      border: 1px solid #52c41a;
    }
    &.low {
      background: linear-gradient(135deg, #fff1d6, #ffe4a8);
      border: 1px solid #faad14;
    }
    &.sold-out {
      background: linear-gradient(135deg, #ffe1e1, #ffc6c6);
      border: 1px solid #f5222d;
    }
    &.closed {
      background: #f2f3f5;
      border: 1px solid #e5e6eb;
    }
  }
}

/* ---------- 日历主体 ---------- */
.calendar-wrapper {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  overflow: hidden;
}

.calendar-grid {
  overflow-x: auto;
  overflow-y: visible;

  /* 美化滚动条 */
  &::-webkit-scrollbar {
    height: 6px;
  }
  &::-webkit-scrollbar-track {
    background: #f7f8fa;
  }
  &::-webkit-scrollbar-thumb {
    background: #c9cdd4;
    border-radius: 3px;
    &:hover { background: #86909c; }
  }
}

.calendar-header,
.calendar-row {
  display: flex;
  min-width: fit-content;
}

/* ---------- 固定列（营位名称） ---------- */
.cell-fixed {
  min-width: 160px;
  max-width: 160px;
  flex-shrink: 0;
  position: sticky;
  left: 0;
  z-index: 2;
}

.product-name-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f7f8fa;
  font-size: 13px;
  font-weight: 600;
  color: #4e5969;
  border-bottom: 2px solid #e5e6eb;
  border-right: 2px solid #e5e6eb;
}

.product-name {
  display: flex;
  align-items: center;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid #f2f3f5;
  border-right: 2px solid #e5e6eb;

  .name-text {
    font-size: 13px;
    font-weight: 500;
    color: #1d2129;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
  }
}

/* 斑马行背景 */
.row-even .product-name {
  background: #fafbfc;
}

/* ---------- 日期列 ---------- */
.cell {
  min-width: 80px;
  flex-shrink: 0;
  text-align: center;
}

.date-header {
  padding: 8px 4px 10px;
  background: #f7f8fa;
  border-bottom: 2px solid #e5e6eb;
  border-right: 1px solid #f2f3f5;

  .date-num {
    font-weight: 700;
    font-size: 16px;
    color: #1d2129;
    line-height: 1.4;
  }
  .date-weekday {
    font-size: 11px;
    color: #86909c;
    margin-top: 1px;
  }

  &.weekend {
    background: #fef7ed;
    .date-num { color: #d46b08; }
    .date-weekday { color: #d46b08; }
  }

  &.today {
    background: #e8f3ff;
    border-bottom-color: #4080ff;

    .date-num {
      color: #fff;
      background: #4080ff;
      border-radius: 50%;
      width: 26px;
      height: 26px;
      line-height: 26px;
      display: inline-block;
    }
    .date-weekday { color: #4080ff; font-weight: 600; }
  }
}

/* ---------- 数据单元格 ---------- */
.data-cell {
  padding: 8px 4px;
  border-bottom: 1px solid #f2f3f5;
  border-right: 1px solid #f2f3f5;
  cursor: default;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 56px;

  &:hover {
    transform: scale(1.02);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    z-index: 1;
    position: relative;
  }

  /* 状态配色 */
  &.available {
    background: #f0faf4;
    .stock-available { color: #0b8235; }
    .cell-price { color: #52c41a; }
  }

  &.low {
    background: #fffcf0;
    .stock-available { color: #d46b08; font-weight: 700; }
    .cell-price { color: #faad14; }
  }

  &.sold-out {
    background: #fff2f0;
    .stock-available { color: #cf1322; font-weight: 700; }
    .cell-price { color: #f5222d; }
  }

  &.closed {
    background: #f7f8fa;
    .cell-stock, .cell-price { color: #c9cdd4; }
  }

  /* 周末列加一层微淡色 */
  &.col-weekend {
    &.available { background: #eaf7ef; }
    &.low { background: #fef9e8; }
  }

  /* 今天列加蓝色左边框 */
  &.col-today {
    border-left: 2px solid #4080ff;
  }

  /* 斑马行 */
  .row-even & {
    &.available { background: #edf8f1; }
    &.closed { background: #f5f6f8; }
  }

  .cell-stock {
    font-size: 14px;
    line-height: 1.5;

    .stock-available {
      font-weight: 700;
      font-size: 15px;
    }
    .stock-divider {
      color: #c9cdd4;
      margin: 0 1px;
      font-weight: 400;
    }
    .stock-total {
      color: #86909c;
      font-size: 12px;
      font-weight: 400;
    }
  }

  .cell-price {
    font-size: 11px;
    color: #86909c;
    margin-top: 2px;
    font-variant-numeric: tabular-nums;
  }

  .cell-empty {
    color: #e5e6eb;
    font-size: 16px;
  }
}
</style>
