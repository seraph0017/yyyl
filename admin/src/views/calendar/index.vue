<template>
  <div class="page-container">
    <div class="card-box calendar-page">
      <div class="calendar-toolbar">
        <div class="toolbar-left">
          <h3 class="page-title">
            <el-icon class="title-icon"><Calendar /></el-icon>
            商品日历
          </h3>
          <el-tag type="info" size="small" effect="plain">{{ monthLabel }}</el-tag>
        </div>
        <div class="toolbar-right">
          <el-select
            v-model="calendarProductType"
            size="small"
            style="width: 132px"
            @change="handleTypeChange"
          >
            <el-option
              v-for="item in calendarTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
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
          <el-button type="primary" size="small" @click="openBatchDialog">
            <el-icon><Plus /></el-icon>批量调整
          </el-button>
        </div>
      </div>

      <div class="calendar-legend">
        <span class="legend-item"><span class="legend-dot available" />可预订</span>
        <span class="legend-item"><span class="legend-dot low" />库存紧张 (≤3)</span>
        <span class="legend-item"><span class="legend-dot sold-out" />已售罄</span>
        <span class="legend-item"><span class="legend-dot closed" />未开放</span>
        <span class="legend-item"><span class="legend-dot shared" />共享库存</span>
      </div>

      <div v-loading="loading" class="calendar-wrapper">
        <div class="calendar-grid">
          <div class="calendar-header">
            <div class="cell-fixed product-name-header">
              <span>{{ selectedTypeLabel }}名称</span>
            </div>
            <div
              v-for="date in dates"
              :key="date"
              class="cell date-header"
              :class="{ weekend: isWeekend(date), today: isToday(date) }"
            >
              <div class="date-num">{{ date.split('-')[2] }}</div>
              <div class="date-weekday">{{ isToday(date) ? '今天' : getWeekday(date) }}</div>
            </div>
          </div>

          <div
            v-for="(product, idx) in productRows"
            :key="product.row_key"
            class="calendar-row"
            :class="{ 'row-even': idx % 2 === 0 }"
          >
            <div class="cell-fixed product-name" :title="product.product_name">
              <span class="name-text">{{ product.product_name }}</span>
              <span class="name-sub">{{ formatRowSub(product) }}</span>
            </div>
            <button
              v-for="date in dates"
              :key="date"
              type="button"
              class="cell data-cell"
              :class="[getCellClass(product, date), { 'col-weekend': isWeekend(date), 'col-today': isToday(date) }]"
              @click="openCellDialog(product, date)"
            >
              <template v-if="getCellData(product, date)">
                <div class="cell-stock">
                  <span class="stock-available">{{ getCellData(product, date)!.available }}</span>
                  <span class="stock-divider">/</span>
                  <span class="stock-total">{{ getCellData(product, date)!.total }}</span>
                </div>
                <div class="cell-price">¥{{ formatYuanAmount(getCellData(product, date)!.price) }}</div>
                <div class="cell-source" v-if="getCellData(product, date)!.inventory_source === 'inventory_pool'">共享</div>
              </template>
              <span v-else class="cell-empty">-</span>
            </button>
          </div>

          <el-empty v-if="!productRows.length && !loading" :description="emptyDescription" :image-size="120" />
        </div>
      </div>
    </div>

    <el-dialog v-model="cellDialogVisible" title="商品日历" width="520px" @closed="resetCellForm">
      <template v-if="selectedCell">
        <el-descriptions :column="2" border class="mb-16">
          <el-descriptions-item :label="selectedTypeLabel">{{ selectedCell.product_name }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ selectedCell.date }}</el-descriptions-item>
          <el-descriptions-item label="可用 / 总量">{{ selectedCell.available }} / {{ selectedCell.total }}</el-descriptions-item>
          <el-descriptions-item label="已售 / 锁定">{{ selectedCell.sold }} / {{ selectedCell.locked }}</el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="selectedCell.inventory_source === 'inventory_pool'"
          type="warning"
          :closable="false"
          show-icon
          :title="`该${selectedTypeLabel}绑定共享库存池，请到共享库存页调整库存池。`"
          class="mb-16"
        />

        <el-form label-width="92px">
          <el-form-item label="总库存">
            <el-input-number
              v-model="cellForm.total"
              :min="selectedCell.locked + selectedCell.sold"
              controls-position="right"
              :disabled="!selectedCell.editable"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-radio-group v-model="cellForm.status" :disabled="!selectedCell.editable">
              <el-radio-button label="open">开放</el-radio-button>
              <el-radio-button label="closed">关闭</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model.trim="cellForm.remark" maxlength="120" clearable :disabled="!selectedCell.editable" />
          </el-form-item>
        </el-form>
      </template>

      <template #footer>
        <el-button @click="openOrdersDialog">查看当天订单</el-button>
        <el-button @click="cellDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingCell" :disabled="!selectedCell?.editable" @click="saveCell">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" :title="`批量调整${selectedTypeLabel}`" width="560px" @closed="resetBatchForm">
      <el-form label-width="104px">
        <el-form-item :label="selectedTypeLabel">
          <el-select v-model="batchForm.row_keys" multiple collapse-tags collapse-tags-tooltip filterable :placeholder="`请选择${selectedTypeLabel}`" style="width: 100%">
            <el-option
              v-for="row in productRows"
              :key="row.row_key"
              :label="formatBatchTargetLabel(row)"
              :value="row.row_key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-radio-group v-model="batchDateMode" class="date-mode-toggle">
            <el-radio-button label="range">日期范围</el-radio-button>
            <el-radio-button label="dates">多选日期</el-radio-button>
          </el-radio-group>
          <el-date-picker
            v-if="batchDateMode === 'range'"
            v-model="batchDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            :shortcuts="batchDateShortcuts"
          />
          <el-date-picker
            v-else
            v-model="batchSelectedDates"
            type="dates"
            placeholder="请选择一个或多个日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="batchDateMode === 'range'" label="星期">
          <el-checkbox-group v-model="batchForm.weekdays">
            <el-checkbox-button v-for="item in weekdayOptions" :key="item.value" :label="item.value">{{ item.label }}</el-checkbox-button>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="调整内容">
          <el-radio-group v-model="batchForm.content">
            <el-radio-button label="inventory">库存</el-radio-button>
            <el-radio-button label="price">价格</el-radio-button>
            <el-radio-button label="both">库存+价格</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="batchForm.content !== 'price'">
          <el-form-item label="库存模式">
            <el-radio-group v-model="batchForm.mode">
              <el-radio-button label="set_total">设总量</el-radio-button>
              <el-radio-button label="adjust_total">增减</el-radio-button>
              <el-radio-button label="open">开放</el-radio-button>
              <el-radio-button label="close">关闭</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.mode === 'set_total'" label="总库存">
            <el-input-number v-model="batchForm.total" :min="0" controls-position="right" />
          </el-form-item>
          <el-form-item v-if="batchForm.mode === 'adjust_total'" label="调整量">
            <el-input-number v-model="batchForm.delta" controls-position="right" />
          </el-form-item>
        </template>
        <template v-if="batchForm.content !== 'inventory'">
          <el-form-item label="价格模式">
            <el-radio-group v-model="batchForm.price_mode">
              <el-radio-button label="set_total">总价</el-radio-button>
              <el-radio-button label="adjust_total">增减</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.price_mode === 'set_total'" label="目标总价">
            <el-input-number v-model="batchForm.price_total" :min="0" :precision="2" controls-position="right" />
          </el-form-item>
          <el-form-item v-if="batchForm.price_mode === 'adjust_total'" label="价格增减">
            <el-input-number v-model="batchForm.price_delta" :precision="2" controls-position="right" />
          </el-form-item>
        </template>
        <el-form-item label="备注">
          <el-input v-model.trim="batchForm.remark" type="textarea" :rows="3" maxlength="120" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingBatch" @click="saveBatch">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ordersDialogVisible" title="当天订单" width="860px">
      <el-table :data="orders" v-loading="ordersLoading" stripe>
        <el-table-column prop="order_no" label="订单号" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="router.push(`/orders/${row.id}`)">{{ row.order_no }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="用户" width="150">
          <template #default="{ row }">
            <div>{{ row.user_nickname || row.user_name || `用户#${row.user_id}` }}</div>
            <div class="text-secondary">{{ row.user_phone_masked || row.user_phone || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="110" align="right">
          <template #default="{ row }">¥{{ formatYuanAmount(row.actual_amount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'verified' ? 'success' : row.status === 'paid' ? 'primary' : 'info'">
              {{ orderStatusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="详细数量" min-width="160">
          <template #default="{ row }">{{ getOrderDetailCount(row) }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar, ArrowLeft, ArrowRight, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { batchUpdateInventory, getInventoryCalendarData, updateInventory } from '@/api/product'
import { getOrders } from '@/api/order'
import { orderStatusMap } from '@/utils'
import type { Order } from '@/types'
import type { InventoryBatchContent, InventoryBatchPayload, InventoryCalendarCell } from '@/types/inventory-pool'

interface CalendarRow {
  row_key: string
  product_id: number
  product_name: string
  sku_id?: number | null
  sku_code?: string | null
  sku_name?: string | null
  time_slot?: string | null
  inventory_source: string
  cells: Record<string, InventoryCalendarCell>
}

const router = useRouter()
const loading = ref(false)
const monthValue = ref(dayjs().format('YYYY-MM'))
const calendarProductType = ref('daily_camping')
const cells = ref<InventoryCalendarCell[]>([])
const cellDialogVisible = ref(false)
const selectedCell = ref<InventoryCalendarCell | null>(null)
const savingCell = ref(false)
const cellForm = reactive({ total: 0, status: 'open' as 'open' | 'closed', remark: '' })
const batchDialogVisible = ref(false)
const savingBatch = ref(false)
const batchDateMode = ref<'range' | 'dates'>('range')
const batchDateRange = ref<[string, string] | null>(null)
const batchSelectedDates = ref<string[]>([])
const batchForm = reactive({
  row_keys: [] as string[],
  content: 'inventory' as InventoryBatchContent,
  mode: 'set_total' as 'set_total' | 'adjust_total' | 'open' | 'close',
  total: 0,
  delta: 0,
  price_mode: 'set_total' as 'set_total' | 'adjust_total',
  price_total: 0,
  price_delta: 0,
  weekdays: [] as number[],
  remark: '',
})
const ordersDialogVisible = ref(false)
const ordersLoading = ref(false)
const orders = ref<Order[]>([])

const weekdayOptions = [
  { label: '一', value: 0 },
  { label: '二', value: 1 },
  { label: '三', value: 2 },
  { label: '四', value: 3 },
  { label: '五', value: 4 },
  { label: '六', value: 5 },
  { label: '日', value: 6 },
]

const calendarTypeOptions = [
  { label: '日常营位', value: 'daily_camping' },
  { label: '活动营位', value: 'event_camping' },
  { label: '日常活动', value: 'daily_activity' },
  { label: '特定活动', value: 'special_activity' },
  { label: '租赁', value: 'rental' },
]

const monthLabel = computed(() => dayjs(monthValue.value).format('YYYY年M月'))
const selectedTypeLabel = computed(() => calendarTypeOptions.find(item => item.value === calendarProductType.value)?.label || '商品')
const emptyDescription = computed(() => `暂无${selectedTypeLabel.value}数据`)

const batchDateShortcuts = [
  { text: '最近一个月', value: () => buildRecentRange(1, 'month') },
  { text: '最近三个月', value: () => buildRecentRange(3, 'month') },
  { text: '最近半年', value: () => buildRecentRange(6, 'month') },
  { text: '最近一年', value: () => buildRecentRange(1, 'year') },
]

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

const productRows = computed<CalendarRow[]>(() => {
  const rows = new Map<string, CalendarRow>()
  cells.value.forEach(cell => {
    const rowKey = `${cell.product_id}:${cell.sku_id || 0}:${cell.time_slot || ''}:${cell.inventory_source}`
    if (!rows.has(rowKey)) {
      rows.set(rowKey, {
        row_key: rowKey,
        product_id: cell.product_id,
        product_name: cell.product_name,
        sku_id: cell.sku_id,
        sku_code: cell.sku_code,
        sku_name: cell.sku_name,
        time_slot: cell.time_slot || null,
        inventory_source: cell.inventory_source,
        cells: {},
      })
    }
    rows.get(rowKey)!.cells[cell.date] = cell
  })
  return Array.from(rows.values())
})

function getCellData(row: CalendarRow, date: string): InventoryCalendarCell | undefined {
  return row.cells[date]
}

function formatRowSub(row: CalendarRow): string {
  const parts = [row.sku_name || row.sku_code, row.time_slot ? `场次 ${row.time_slot}` : ''].filter(Boolean)
  return parts.join(' · ') || '商品库存'
}

function formatBatchTargetLabel(row: CalendarRow): string {
  const suffix = formatRowSub(row)
  return `${row.product_name} #${row.product_id}${suffix ? ` · ${suffix}` : ''}`
}

function getCellClass(row: CalendarRow, date: string): string {
  const data = getCellData(row, date)
  if (!data || data.status === 'closed') return 'closed'
  if (data.available === 0) return 'sold-out'
  if (data.available <= 3) return 'low'
  if (data.inventory_source === 'inventory_pool') return 'shared'
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
  return ['日', '一', '二', '三', '四', '五', '六'][dayjs(date).day()] || ''
}

function buildRecentRange(amount: number, unit: 'month' | 'year'): [Date, Date] {
  const start = dayjs().startOf('day')
  return [start.toDate(), start.add(amount, unit).subtract(1, 'day').toDate()]
}

function changeMonth(offset: number) {
  monthValue.value = dayjs(monthValue.value).add(offset, 'month').format('YYYY-MM')
  fetchData()
}

function goToday() {
  monthValue.value = dayjs().format('YYYY-MM')
  fetchData()
}

function handleTypeChange() {
  cells.value = []
  selectedCell.value = null
  batchForm.row_keys = []
  fetchData()
}

function formatYuanAmount(value: number | string | null | undefined): string {
  const amount = Number(value || 0)
  return Number.isFinite(amount) ? amount.toFixed(2) : '0.00'
}

async function fetchData() {
  loading.value = true
  try {
    const start = dayjs(monthValue.value).startOf('month').format('YYYY-MM-DD')
    const end = dayjs(monthValue.value).endOf('month').format('YYYY-MM-DD')
    const res = await getInventoryCalendarData({
      date_start: start,
      date_end: end,
      product_type: calendarProductType.value,
      inventory_source: 'all',
      include_missing: true,
    })
    cells.value = res.data.cells
  } catch {
    cells.value = []
  } finally {
    loading.value = false
  }
}

function openCellDialog(row: CalendarRow, date: string) {
  const cell = getCellData(row, date)
  if (!cell) return
  selectedCell.value = cell
  Object.assign(cellForm, {
    total: cell.total,
    status: cell.status,
    remark: '',
  })
  cellDialogVisible.value = true
}

function resetCellForm() {
  selectedCell.value = null
  Object.assign(cellForm, { total: 0, status: 'open', remark: '' })
}

async function saveCell() {
  if (!selectedCell.value) return
  const cell = selectedCell.value
  const payload = {
    total: cellForm.total,
    status: cellForm.status,
    remark: cellForm.remark?.trim() || undefined,
  }
  try {
    await ElMessageBox.confirm(
      `确认调整「${cell.product_name}」${cell.date} 的库存？`,
      '商品日历调整确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  savingCell.value = true
  try {
    if (cell.inventory_id) {
      await updateInventory(cell.inventory_id, payload as any)
    } else {
      await batchUpdateInventory({
        product_ids: [cell.product_id],
        sku_ids: cell.sku_id ? [cell.sku_id] : undefined,
        time_slot: cell.time_slot || undefined,
        dates: [cell.date],
        mode: 'set_total',
        total: payload.total,
        status: payload.status,
        create_missing: true,
        remark: payload.remark,
      })
    }
    ElMessage.success('库存已更新')
    cellDialogVisible.value = false
    fetchData()
  } finally {
    savingCell.value = false
  }
}

function openBatchDialog() {
  batchDateMode.value = 'range'
  batchSelectedDates.value = []
  batchDateRange.value = [
    dayjs(monthValue.value).startOf('month').format('YYYY-MM-DD'),
    dayjs(monthValue.value).endOf('month').format('YYYY-MM-DD'),
  ]
  batchDialogVisible.value = true
}

function resetBatchForm() {
  Object.assign(batchForm, {
    row_keys: [],
    content: 'inventory',
    mode: 'set_total',
    total: 0,
    delta: 0,
    price_mode: 'set_total',
    price_total: 0,
    price_delta: 0,
    weekdays: [],
    remark: '',
  })
  batchDateMode.value = 'range'
  batchDateRange.value = null
  batchSelectedDates.value = []
}

function buildBatchPayload(): InventoryBatchPayload | null {
  const selectedTargets = productRows.value.filter(row => batchForm.row_keys.includes(row.row_key))
  if (!selectedTargets.length) {
    ElMessage.error(`请选择${selectedTypeLabel.value}`)
    return null
  }
  if (batchDateMode.value === 'range' && (!batchDateRange.value?.[0] || !batchDateRange.value?.[1])) {
    ElMessage.error('请选择日期范围')
    return null
  }
  if (batchDateMode.value === 'dates' && batchSelectedDates.value.length === 0) {
    ElMessage.error('请选择需要调整的日期')
    return null
  }
  const hasSharedTargets = selectedTargets.some(row => row.inventory_source === 'inventory_pool')
  if (batchForm.content !== 'price' && hasSharedTargets) {
    ElMessage.error('共享库存行请在库存池中调整库存；如需批量改价请选择“价格”')
    return null
  }
  const skuIds = selectedTargets.map(row => row.sku_id).filter((id): id is number => !!id)
  const hasSkuTargets = skuIds.length > 0
  const hasProductLevelTargets = selectedTargets.some(row => !row.sku_id)
  if (hasSkuTargets && hasProductLevelTargets) {
    ElMessage.error('商品级行和 SKU 行不能混选，请分开批量调整')
    return null
  }
  if (batchForm.content !== 'inventory' && hasSkuTargets) {
    ElMessage.error('SKU 价格优先，批量调价请选择商品级行')
    return null
  }
  const timeSlots = Array.from(new Set(selectedTargets.map(row => row.time_slot || '').filter(Boolean)))
  if (timeSlots.length > 1) {
    ElMessage.error('多选批量调整暂不支持混合多个活动场次')
    return null
  }
  const payload: InventoryBatchPayload = {
    product_ids: Array.from(new Set(selectedTargets.map(row => row.product_id))),
    sku_ids: hasSkuTargets ? skuIds : undefined,
    time_slot: timeSlots[0] || undefined,
    mode: batchForm.content === 'price' ? 'open' : batchForm.mode,
    adjust_inventory: batchForm.content !== 'price',
    create_missing: true,
  }
  if (batchDateMode.value === 'dates') {
    payload.dates = [...batchSelectedDates.value]
  } else if (batchDateRange.value) {
    payload.date_start = batchDateRange.value[0]
    payload.date_end = batchDateRange.value[1]
  }
  if (batchDateMode.value === 'range' && batchForm.weekdays.length) payload.weekdays = [...batchForm.weekdays]
  if (batchForm.remark.trim()) payload.remark = batchForm.remark.trim()
  if (batchForm.content !== 'price') {
    if (batchForm.mode === 'set_total') {
      payload.total = batchForm.total || 0
      payload.status = 'open'
    } else if (batchForm.mode === 'adjust_total') {
      payload.delta = batchForm.delta || 0
    } else if (batchForm.mode === 'open') {
      payload.status = 'open'
    } else if (batchForm.mode === 'close') {
      payload.status = 'closed'
    }
  }
  if (batchForm.content !== 'inventory') {
    payload.price_mode = batchForm.price_mode
    if (batchForm.price_mode === 'set_total') payload.price_total = batchForm.price_total || 0
    else payload.price_delta = batchForm.price_delta || 0
  }
  return payload
}

function getBatchDateSummary(): string {
  if (batchDateMode.value === 'dates') {
    const sortedDates = [...batchSelectedDates.value].sort()
    if (sortedDates.length <= 3) return sortedDates.join('、')
    return `${sortedDates.slice(0, 3).join('、')} 等 ${sortedDates.length} 天`
  }
  return batchDateRange.value ? `${batchDateRange.value[0]} 至 ${batchDateRange.value[1]}` : ''
}

async function saveBatch() {
  const payload = buildBatchPayload()
  if (!payload) return
  try {
    await ElMessageBox.confirm(
      `确认批量调整 ${getBatchDateSummary()} 的${selectedTypeLabel.value}？`,
      '商品日历批量调整确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  savingBatch.value = true
  try {
    const res = await batchUpdateInventory(payload)
    const priceText = res.data.price_created_count || res.data.price_updated_count ? `，价格新增 ${res.data.price_created_count || 0} 条、更新 ${res.data.price_updated_count || 0} 条` : ''
    ElMessage.success(`库存创建 ${res.data.created_count} 条、更新 ${res.data.updated_count} 条${priceText}`)
    batchDialogVisible.value = false
    fetchData()
  } finally {
    savingBatch.value = false
  }
}

async function openOrdersDialog() {
  if (!selectedCell.value) return
  ordersDialogVisible.value = true
  ordersLoading.value = true
  try {
    const res = await getOrders({
      page: 1,
      page_size: 50,
      product_id: selectedCell.value.product_id,
      sku_id: selectedCell.value.sku_id || undefined,
      product_type: calendarProductType.value,
      booking_date_start: selectedCell.value.date,
      booking_date_end: selectedCell.value.date,
      time_slot: selectedCell.value.time_slot || undefined,
    })
    orders.value = res.data.list
  } finally {
    ordersLoading.value = false
  }
}

function getOrderDetailCount(order: Order): string {
  const cell = selectedCell.value
  const items = (order.items || []).filter(item => {
    if (!cell) return true
    if (item.product_id !== cell.product_id) return false
    if (cell.sku_id && item.sku_id !== cell.sku_id) return false
    if (cell.date && item.date !== cell.date) return false
    if (cell.time_slot && item.time_slot !== cell.time_slot) return false
    return true
  })
  const persons = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  const dates = new Set(items.map(item => item.date).filter(Boolean))
  if (dates.size > 0) {
    return `${persons}人${dates.size}晚`
  }
  return `${items.length || order.item_count || 0}单`
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.calendar-page {
  padding: 20px 24px;
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
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
  flex-wrap: wrap;
}

.calendar-legend {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  font-size: 12px;
  color: #86909c;
  flex-wrap: wrap;

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
      background: #d4f5e9;
      border: 1px solid #52c41a;
    }

    &.low {
      background: #fff1d6;
      border: 1px solid #faad14;
    }

    &.sold-out {
      background: #ffe1e1;
      border: 1px solid #f5222d;
    }

    &.closed {
      background: #f2f3f5;
      border: 1px solid #e5e6eb;
    }

    &.shared {
      background: #fdf2d7;
      border: 1px solid #c8a872;
    }
  }
}

.calendar-wrapper {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  overflow: hidden;
}

.calendar-grid {
  overflow-x: auto;
  overflow-y: visible;
}

.calendar-header,
.calendar-row {
  display: flex;
  min-width: fit-content;
}

.cell-fixed {
  min-width: 180px;
  max-width: 180px;
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
  flex-direction: column;
  justify-content: center;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid #f2f3f5;
  border-right: 2px solid #e5e6eb;

  .name-text {
    font-size: 13px;
    font-weight: 600;
    color: #1d2129;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
  }

  .name-sub {
    color: #86909c;
    font-size: 11px;
    margin-top: 3px;
  }
}

.row-even .product-name {
  background: #fafbfc;
}

.cell {
  min-width: 88px;
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

    .date-num,
    .date-weekday {
      color: #d46b08;
    }
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

    .date-weekday {
      color: #4080ff;
      font-weight: 600;
    }
  }
}

.data-cell {
  appearance: none;
  border: 0;
  padding: 8px 4px;
  border-bottom: 1px solid #f2f3f5;
  border-right: 1px solid #f2f3f5;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 64px;

  &:hover {
    transform: scale(1.02);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    z-index: 1;
    position: relative;
  }

  &.available {
    background: #f0faf4;

    .stock-available {
      color: #0b8235;
    }
  }

  &.shared {
    background: #fdf8ea;

    .stock-available {
      color: #9b6a00;
    }
  }

  &.low {
    background: #fffcf0;

    .stock-available {
      color: #d46b08;
      font-weight: 700;
    }
  }

  &.sold-out {
    background: #fff2f0;

    .stock-available {
      color: #cf1322;
      font-weight: 700;
    }
  }

  &.closed {
    background: #f7f8fa;

    .cell-stock,
    .cell-price {
      color: #c9cdd4;
    }
  }

  &.col-today {
    border-left: 2px solid #4080ff;
  }
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

.cell-price,
.cell-source {
  font-size: 11px;
  color: #86909c;
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}

.cell-empty {
  color: #e5e6eb;
  font-size: 16px;
}

.mb-16 {
  margin-bottom: 16px;
}

@media (max-width: 720px) {
  .calendar-page {
    padding: 16px;
  }

  .cell-fixed {
    min-width: 150px;
    max-width: 150px;
  }
}
</style>
