<template>
  <view class="page-staff">
    <view class="staff-hero">
      <view class="staff-hero__main">
        <text class="staff-hero__title">员工核销</text>
        <text class="staff-hero__subtitle">今日现场订单与票券</text>
      </view>
      <view class="staff-scan-btn" @tap="onScanVerify">
        <text class="staff-scan-btn__icon">⌗</text>
        <text>扫码</text>
      </view>
    </view>

    <view class="staff-stats">
      <view class="staff-stat">
        <text class="staff-stat__num">{{ todayStats.orders }}</text>
        <text class="staff-stat__label">今日订单</text>
      </view>
      <view class="staff-stat">
        <text class="staff-stat__num">{{ todayStats.pending }}</text>
        <text class="staff-stat__label">待核销</text>
      </view>
      <view class="staff-stat">
        <text class="staff-stat__num">{{ todayStats.verified }}</text>
        <text class="staff-stat__label">已核销</text>
      </view>
      <view class="staff-stat">
        <text class="staff-stat__num">¥{{ formatMoney(todayStats.revenue) }}</text>
        <text class="staff-stat__label">今日金额</text>
      </view>
    </view>

    <view class="staff-tabs">
      <view
        v-for="(tab, index) in tabs"
        :key="tab.key"
        :class="['staff-tab', activeTab === index ? 'staff-tab--active' : '']"
        @tap="onTabChange(index)"
      >
        <text>{{ tab.name }}</text>
      </view>
    </view>

    <view class="staff-content">
      <view v-if="loading" class="staff-loading">
        <text>加载中...</text>
      </view>

      <block v-else-if="activeTab === 0">
        <view v-if="pendingTickets.length > 0">
          <view
            class="staff-card staff-card--ticket"
            v-for="ticket in pendingTickets"
            :key="ticket.ticket_id"
            @tap="openOrderDetail(ticket.order_id)"
          >
            <view class="staff-card__top">
              <view class="staff-card__title">
                <text class="staff-card__name text-ellipsis">{{ ticket.product_name || '待核销票券' }}</text>
                <text class="staff-card__meta">{{ formatDateOnly(ticket.verify_date || ticket.date) }} {{ ticket.time_slot || '' }}</text>
              </view>
              <text class="staff-badge staff-badge--pending">待核销</text>
            </view>
            <view class="staff-card__grid">
              <view><text>订单</text><text>{{ ticket.order_no }}</text></view>
              <view><text>票号</text><text>{{ ticket.ticket_no }}</text></view>
              <view><text>用户</text><text>{{ ticket.user_nickname || '微信用户' }}</text></view>
              <view><text>手机</text><text>{{ ticket.user_phone_masked || '-' }}</text></view>
            </view>
            <view class="staff-card__remark" v-if="ticket.remark">
              <text>{{ ticket.remark }}</text>
            </view>
          </view>
        </view>
        <view v-else class="staff-empty">
          <text class="staff-empty__title">暂无待核销票券</text>
          <text class="staff-empty__desc">现场扫码或切换到今日订单查看详情</text>
        </view>
      </block>

      <block v-else-if="activeTab === 1">
        <view v-if="todayOrders.length > 0">
          <view
            class="staff-card"
            v-for="order in todayOrders"
            :key="`${order.order_id}-${order.order_item_id}`"
            @tap="openOrderDetail(order.order_id)"
          >
            <view class="staff-card__top">
              <view class="staff-card__title">
                <text class="staff-card__name text-ellipsis">{{ order.product_name || '现场订单' }}</text>
                <text class="staff-card__meta">{{ formatDateOnly(order.date) }} {{ order.time_slot || '' }}</text>
              </view>
              <text :class="['staff-badge', order.can_verify ? 'staff-badge--pending' : 'staff-badge--done']">
                {{ getVerifyStatusText(order.verify_status) }}
              </text>
            </view>
            <view class="staff-card__grid">
              <view><text>订单</text><text>{{ order.order_no }}</text></view>
              <view><text>数量</text><text>×{{ order.quantity }}</text></view>
              <view><text>用户</text><text>{{ order.user_nickname || '微信用户' }}</text></view>
              <view><text>手机</text><text>{{ order.user_phone_masked || '-' }}</text></view>
            </view>
            <view class="staff-card__bottom">
              <text>实付 ¥{{ formatMoney(order.actual_amount) }}</text>
              <text v-if="order.remark">备注：{{ order.remark }}</text>
            </view>
          </view>
        </view>
        <view v-else class="staff-empty">
          <text class="staff-empty__title">今日暂无订单</text>
          <text class="staff-empty__desc">有支付成功订单后会显示在这里</text>
        </view>
      </block>

      <block v-else-if="activeTab === 2">
        <view class="onsite-panel">
          <view class="onsite-segment">
            <view
              :class="['onsite-segment__item', onsiteForm.payment_flow === 'customer_scan_qr' ? 'onsite-segment__item--active' : '']"
              @tap="onsiteForm.payment_flow = 'customer_scan_qr'"
            >
              <text>顾客扫码</text>
            </view>
            <view
              :class="['onsite-segment__item', onsiteForm.payment_flow === 'merchant_scan_code' ? 'onsite-segment__item--active' : '']"
              @tap="onsiteForm.payment_flow = 'merchant_scan_code'"
            >
              <text>扫付款码</text>
            </view>
          </view>

          <view class="onsite-segment onsite-segment--light">
            <view
              :class="['onsite-segment__item', onsiteForm.mode === 'custom_amount' ? 'onsite-segment__item--active' : '']"
              @tap="onsiteForm.mode = 'custom_amount'"
            >
              <text>自定义金额</text>
            </view>
            <view
              :class="['onsite-segment__item', onsiteForm.mode === 'product' ? 'onsite-segment__item--active' : '']"
              @tap="onsiteForm.mode = 'product'"
            >
              <text>商品临时单</text>
            </view>
          </view>

          <view v-if="onsiteForm.mode === 'product'" class="onsite-form">
            <view class="onsite-field">
              <text>商品ID</text>
              <input v-model="onsiteForm.product_id" type="number" placeholder="输入商品ID" />
            </view>
            <view class="onsite-field">
              <text>SKU ID</text>
              <input v-model="onsiteForm.sku_id" type="number" placeholder="选填" />
            </view>
            <view class="onsite-field">
              <text>数量</text>
              <input v-model="onsiteForm.quantity" type="number" placeholder="1" />
            </view>
            <view class="onsite-field">
              <text>预约日期</text>
              <input v-model="onsiteForm.booking_date" placeholder="YYYY-MM-DD，营位商品必填" />
            </view>
            <view class="onsite-field">
              <text>场次</text>
              <input v-model="onsiteForm.time_slot" placeholder="选填" />
            </view>
          </view>

          <view v-else class="onsite-form">
            <view class="onsite-field">
              <text>收款项</text>
              <input v-model="onsiteForm.item_name" placeholder="如 现场补差价" />
            </view>
            <view class="onsite-field">
              <text>金额</text>
              <input v-model="onsiteForm.amount" type="digit" placeholder="0.00" />
            </view>
          </view>

          <view v-if="onsiteForm.payment_flow === 'merchant_scan_code'" class="onsite-field">
            <text>付款码</text>
            <view class="onsite-auth-code">
              <input v-model="onsiteForm.auth_code" placeholder="auth_code" />
              <view class="onsite-mini-btn" @tap="scanPaymentAuthCode"><text>扫码</text></view>
            </view>
          </view>

          <view class="onsite-field">
            <text>备注</text>
            <textarea v-model="onsiteForm.remark" placeholder="现场收款原因、商品说明或顾客信息" maxlength="200" />
          </view>

          <view class="onsite-actions">
            <view class="onsite-action onsite-action--ghost" @tap="resetOnsiteForm"><text>重置</text></view>
            <view class="onsite-action onsite-action--primary" @tap="submitOnsiteOrder">
              <text>{{ onsiteSubmitting ? '提交中...' : '提交' }}</text>
            </view>
          </view>

          <view v-if="onsiteSession" class="onsite-result">
            <text class="onsite-result__title">{{ onsiteSession.miniapp_path ? '临时收款码' : '付款码收款已提交' }}</text>
            <view class="onsite-result__row"><text>会话号</text><text>{{ onsiteSession.session_no }}</text></view>
            <view class="onsite-result__row"><text>状态</text><text>{{ onsiteSession.status }}</text></view>
            <view class="onsite-result__row" v-if="onsiteCodePayState"><text>微信状态</text><text>{{ onsiteCodePayState }}</text></view>
            <view
              v-if="onsiteResultRequiresQuery"
              class="onsite-query-btn"
              @tap="queryOnsiteCodePayResult"
            >
              <text>{{ onsiteQuerying ? '查询中...' : '查询付款结果' }}</text>
            </view>
            <view class="onsite-result__qrcode" v-if="onsiteSession.qrcode_image_url">
              <image
                v-if="!onsiteQrcodeLoadFailed"
                :src="resolveImageUrl(onsiteSession.qrcode_image_url)"
                mode="aspectFit"
                @error="onOnsiteQrcodeError"
              />
              <text v-else>小程序码加载失败，请复制路径或重新生成</text>
            </view>
            <view class="onsite-result__path" v-if="onsiteSession.miniapp_path">
              <text>{{ onsiteSession.miniapp_path }}</text>
              <view class="onsite-mini-btn" @tap="copyOnsiteMiniappPath"><text>复制</text></view>
            </view>
          </view>
        </view>
      </block>

      <block v-else>
        <view v-if="verifyLogs.length > 0">
          <view class="staff-log" v-for="log in verifyLogs" :key="log.id" @tap="log.order_id && openOrderDetail(log.order_id)">
            <view class="staff-log__line">
              <text class="staff-log__name text-ellipsis">{{ log.product_name || log.ticket_no || '核销记录' }}</text>
              <text :class="['staff-badge', getLogBadgeClass(log.verify_result)]">
                {{ getLogResultText(log.verify_result) }}
              </text>
            </view>
            <view class="staff-log__meta">
              <text>{{ formatDateTime(log.created_at) }}</text>
              <text>{{ log.user_phone_masked || '-' }}</text>
            </view>
            <text class="staff-log__reason" v-if="log.failure_reason">{{ log.failure_reason }}</text>
          </view>
        </view>
        <view v-else class="staff-empty">
          <text class="staff-empty__title">暂无核销历史</text>
          <text class="staff-empty__desc">成功、失败和重复核销都会留痕</text>
        </view>
      </block>
    </view>

    <view class="verify-mask" v-if="showVerifyResult" @tap="onCloseResult">
      <view class="verify-popup" @tap.stop>
        <text class="verify-icon">{{ verifyResult?.needs_verification_code ? '••' : '✓' }}</text>
        <text class="verify-title">{{ verifyResult?.needs_verification_code ? '等待用户确认' : '验票成功' }}</text>
        <view class="verify-info" v-if="verifyResult">
          <view class="verify-row"><text>商品</text><text>{{ verifyResult.product_name || '-' }}</text></view>
          <view class="verify-row"><text>票号</text><text>{{ verifyResult.ticket_no }}</text></view>
          <view class="verify-row"><text>日期</text><text>{{ formatDateOnly(verifyResult.verify_date) }}</text></view>
        </view>
        <view class="verify-code-section" v-if="verifyResult?.needs_verification_code">
          <text class="verify-code-label">会员卡验证码</text>
          <text class="verify-code-num">{{ verifyResult.verification_code }}</text>
          <text class="verify-code-tip">请让用户在小程序输入验证码完成确认</text>
        </view>
        <view class="verify-actions">
          <view class="verify-action verify-action--primary" @tap="onCloseResult"><text>知道了</text></view>
        </view>
      </view>
    </view>

    <view class="order-detail-mask" v-if="showOrderDetail" @tap="closeOrderDetail">
      <view class="order-detail" @tap.stop>
        <view class="order-detail__header">
          <view>
            <text class="order-detail__title">订单详情</text>
            <text class="order-detail__no">{{ selectedOrder?.order_no }}</text>
          </view>
          <text class="order-detail__close" @tap="closeOrderDetail">×</text>
        </view>
        <view class="order-detail__user">
          <text>{{ selectedOrder?.user_nickname || '微信用户' }}</text>
          <text>{{ selectedOrder?.user_phone_masked || '-' }}</text>
        </view>
        <view class="order-detail__remark" v-if="selectedOrder?.remark">
          <text>{{ selectedOrder.remark }}</text>
        </view>
        <view class="order-detail__item" v-for="item in selectedOrder?.items || []" :key="item.order_item_id">
          <view class="order-detail__item-top">
            <text class="text-ellipsis">{{ item.product_name || '商品' }}</text>
            <text>×{{ item.quantity }}</text>
          </view>
          <view class="order-detail__item-meta">
            <text>{{ formatDateOnly(item.date) }} {{ item.time_slot || '' }}</text>
            <text>¥{{ formatMoney(item.actual_price) }}</text>
          </view>
          <view class="order-detail__tickets">
            <view class="order-ticket" v-for="ticket in item.tickets" :key="ticket.ticket_id">
              <text>{{ ticket.ticket_no }}</text>
              <text :class="ticket.can_verify ? 'order-ticket--pending' : 'order-ticket--done'">
                {{ getVerifyStatusText(ticket.verify_status) }}
              </text>
            </view>
          </view>
        </view>
        <view class="order-detail__total">
          <text>实付</text>
          <text>¥{{ formatMoney(selectedOrder?.actual_amount || 0) }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { get, post, resolveImageUrl } from '@/utils/request'
import { useUserStore } from '@/store/user'
import type {
  IStaffOrderDetail,
  IStaffPendingTicket,
  IStaffScanResponse,
  IStaffTicketLog,
  IStaffTodayOrder,
  ITemporaryOrderCodePayResult,
  ITemporaryOrderCreatePayload,
  ITemporaryOrderCreateResult,
  ITemporaryOrderSession,
} from '@/types'

interface StaffTab {
  key: 'pending' | 'orders' | 'onsite' | 'history'
  name: string
}

const tabs = ref<StaffTab[]>([
  { key: 'pending', name: '待核销' },
  { key: 'orders', name: '今日订单' },
  { key: 'onsite', name: '现场收款' },
  { key: 'history', name: '核销历史' },
])
const activeTab = ref(0)
const loading = ref(false)
const pendingTickets = ref<IStaffPendingTicket[]>([])
const todayOrders = ref<IStaffTodayOrder[]>([])
const verifyLogs = ref<IStaffTicketLog[]>([])
const verifyResult = ref<IStaffScanResponse | null>(null)
const showVerifyResult = ref(false)
const selectedOrder = ref<IStaffOrderDetail | null>(null)
const showOrderDetail = ref(false)
const userStore = useUserStore()
const onsiteSubmitting = ref(false)
const onsiteQuerying = ref(false)
const onsiteQrcodeLoadFailed = ref(false)
const onsiteResult = ref<ITemporaryOrderCreateResult | null>(null)
const onsiteForm = reactive({
  payment_flow: 'customer_scan_qr' as 'customer_scan_qr' | 'merchant_scan_code',
  mode: 'custom_amount' as 'custom_amount' | 'product',
  product_id: '',
  sku_id: '',
  quantity: '1',
  booking_date: '',
  time_slot: '',
  item_name: '',
  amount: '',
  remark: '',
  auth_code: '',
})

const todayStats = computed(() => ({
  orders: new Set(todayOrders.value.map(item => item.order_id)).size,
  pending: pendingTickets.value.length,
  verified: verifyLogs.value.filter(item => item.verify_result === 'success').length,
  revenue: sumUniqueOrderAmount(todayOrders.value),
}))

const onsiteSession = computed<ITemporaryOrderSession | null>(() => {
  if (!onsiteResult.value) return null
  if (isTemporaryCodePayResult(onsiteResult.value)) return onsiteResult.value.session
  return onsiteResult.value
})

const onsiteCodePayState = computed(() => {
  if (!onsiteResult.value || !isTemporaryCodePayResult(onsiteResult.value)) return ''
  return onsiteResult.value.trade_state || '处理中'
})

const onsiteResultRequiresQuery = computed(() => {
  return Boolean(
    onsiteResult.value
    && isTemporaryCodePayResult(onsiteResult.value)
    && onsiteResult.value.requires_query
    && onsiteSession.value?.id,
  )
})

onLoad(async () => {
  if (await ensureStaffAccess()) {
    await loadStaffDashboard()
  }
})

onPullDownRefresh(async () => {
  if (await ensureStaffAccess()) {
    await loadStaffDashboard()
  }
  uni.stopPullDownRefresh()
})

async function ensureStaffAccess(): Promise<boolean> {
  userStore.restoreFromStorage()
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    uni.switchTab({ url: '/pages/mine/index' })
    return false
  }
  if (!userStore.isStaff) {
    uni.showToast({ title: '无员工权限', icon: 'none' })
    uni.switchTab({ url: '/pages/mine/index' })
    return false
  }
  return true
}

async function loadStaffDashboard() {
  loading.value = true
  try {
    const [pending, orders, logs] = await Promise.all([
      get<IStaffPendingTicket[]>('/staff/tickets/pending', undefined, { showError: false }),
      get<IStaffTodayOrder[]>('/staff/orders/today', undefined, { showError: false }),
      get<IStaffTicketLog[]>('/staff/tickets/logs', { limit: 50, only_me: false }, { showError: false }),
    ])
    pendingTickets.value = pending || []
    todayOrders.value = orders || []
    verifyLogs.value = logs || []
  } catch (err: any) {
    uni.showToast({ title: err?.message || '员工数据加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onTabChange(index: number) {
  activeTab.value = index
}

async function onScanVerify() {
  if (!(await ensureStaffAccess())) return
  uni.scanCode({
    onlyFromCamera: true,
    success: async (res) => {
      try {
        const data = await post<IStaffScanResponse>(
          '/staff/tickets/scan',
          {
            qr_token: res.result,
            device_info: 'miniapp-staff-scan',
          },
          { showLoading: true, loadingText: '核销中...', showError: false },
        )
        verifyResult.value = data
        showVerifyResult.value = true
        await loadStaffDashboard()
      } catch (err: any) {
        uni.showToast({ title: err?.message || '验票失败', icon: 'none' })
      }
    },
    fail: (err) => {
      if (err?.errMsg?.includes('cancel')) return
      uni.showToast({ title: '无法打开扫码，请检查权限', icon: 'none' })
    },
  })
}

function isTemporaryCodePayResult(result: ITemporaryOrderCreateResult): result is ITemporaryOrderCodePayResult {
  return Boolean((result as ITemporaryOrderCodePayResult).session && (result as ITemporaryOrderCodePayResult).order)
}

function toPositiveInt(value: string, fallback = 1): number {
  const num = Number.parseInt(value, 10)
  return Number.isFinite(num) && num > 0 ? num : fallback
}

function buildOnsitePayload(): ITemporaryOrderCreatePayload {
  const payload: ITemporaryOrderCreatePayload = {
    payment_flow: onsiteForm.payment_flow,
    mode: onsiteForm.mode,
    quantity: toPositiveInt(onsiteForm.quantity),
    remark: onsiteForm.remark.trim(),
  }
  if (onsiteForm.mode === 'product') {
    const productId = toPositiveInt(onsiteForm.product_id, 0)
    if (!productId) throw new Error('请输入商品ID')
    payload.product_id = productId
    const skuId = toPositiveInt(onsiteForm.sku_id, 0)
    if (skuId) payload.sku_id = skuId
    if (onsiteForm.booking_date.trim()) payload.booking_date = onsiteForm.booking_date.trim()
    if (onsiteForm.time_slot.trim()) payload.time_slot = onsiteForm.time_slot.trim()
  } else {
    const amount = Number(onsiteForm.amount)
    if (!onsiteForm.item_name.trim()) throw new Error('请填写收款项')
    if (!Number.isFinite(amount) || amount <= 0) throw new Error('请填写收款金额')
    if (!onsiteForm.remark.trim()) throw new Error('请填写备注')
    payload.item_name = onsiteForm.item_name.trim()
    payload.amount = amount
  }
  if (onsiteForm.payment_flow === 'merchant_scan_code') {
    if (!onsiteForm.auth_code.trim()) throw new Error('请扫描用户付款码')
    payload.auth_code = onsiteForm.auth_code.trim()
    payload.device_id = 'miniapp-staff-onsite'
  }
  return payload
}

function resetOnsiteForm() {
  onsiteForm.payment_flow = 'customer_scan_qr'
  onsiteForm.mode = 'custom_amount'
  onsiteForm.product_id = ''
  onsiteForm.sku_id = ''
  onsiteForm.quantity = '1'
  onsiteForm.booking_date = ''
  onsiteForm.time_slot = ''
  onsiteForm.item_name = ''
  onsiteForm.amount = ''
  onsiteForm.remark = ''
  onsiteForm.auth_code = ''
  onsiteResult.value = null
  onsiteQrcodeLoadFailed.value = false
}

async function submitOnsiteOrder() {
  if (onsiteSubmitting.value) return
  if (!(await ensureStaffAccess())) return
  onsiteSubmitting.value = true
  try {
    const payload = buildOnsitePayload()
    onsiteResult.value = await post<ITemporaryOrderCreateResult>(
      '/staff/orders/temporary',
      payload as unknown as Record<string, unknown>,
      { showLoading: true, loadingText: '提交中...', showError: false },
    )
    onsiteQrcodeLoadFailed.value = false
    uni.showToast({
      title: onsiteForm.payment_flow === 'merchant_scan_code' ? '付款码收款已提交' : '临时收款码已生成',
      icon: 'none',
    })
    await loadStaffDashboard()
  } catch (err: any) {
    uni.showToast({ title: err?.message || '现场收款失败', icon: 'none' })
  } finally {
    onsiteSubmitting.value = false
  }
}

async function queryOnsiteCodePayResult() {
  if (onsiteQuerying.value || !onsiteSession.value?.id) return
  if (!(await ensureStaffAccess())) return
  onsiteQuerying.value = true
  try {
    onsiteResult.value = await post<ITemporaryOrderCreateResult>(
      `/staff/orders/temporary/${onsiteSession.value.id}/query-codepay`,
      {},
      { showLoading: true, loadingText: '查单中...', showError: false },
    )
    if (isTemporaryCodePayResult(onsiteResult.value) && onsiteResult.value.trade_state === 'SUCCESS') {
      uni.showToast({ title: '付款已确认', icon: 'none' })
      await loadStaffDashboard()
      return
    }
    uni.showToast({ title: '仍需稍后继续查单', icon: 'none' })
  } catch (err: any) {
    uni.showToast({ title: err?.message || '付款码查单失败', icon: 'none' })
  } finally {
    onsiteQuerying.value = false
  }
}

function onOnsiteQrcodeError() {
  onsiteQrcodeLoadFailed.value = true
  uni.showToast({ title: '小程序码图片加载失败，请复制路径或重新生成', icon: 'none' })
}

function scanPaymentAuthCode() {
  uni.scanCode({
    onlyFromCamera: true,
    success: (res) => {
      onsiteForm.auth_code = res.result
    },
    fail: (err) => {
      if (err?.errMsg?.includes('cancel')) return
      uni.showToast({ title: '无法打开扫码，请检查权限', icon: 'none' })
    },
  })
}

function copyOnsiteMiniappPath() {
  const miniapp_path = onsiteSession.value?.miniapp_path || ''
  if (!miniapp_path) return
  uni.setClipboardData({ data: miniapp_path })
}

async function openOrderDetail(orderId: number) {
  try {
    selectedOrder.value = await get<IStaffOrderDetail>(`/staff/orders/${orderId}`, undefined, {
      showLoading: true,
      loadingText: '加载订单...',
      showError: false,
    })
    showOrderDetail.value = true
  } catch (err: any) {
    uni.showToast({ title: err?.message || '订单详情加载失败', icon: 'none' })
  }
}

function closeOrderDetail() {
  showOrderDetail.value = false
  selectedOrder.value = null
}

function onCloseResult() {
  showVerifyResult.value = false
  verifyResult.value = null
}

function formatMoney(value: number | string | null | undefined): string {
  const num = Number(value || 0)
  return num.toFixed(2)
}

function sumUniqueOrderAmount(rows: IStaffTodayOrder[]): number {
  const seen = new Set<number>()
  return rows.reduce((sum, item) => {
    if (seen.has(item.order_id)) return sum
    seen.add(item.order_id)
    return sum + Number(item.actual_amount || 0)
  }, 0)
}

function formatDateOnly(value?: string | null): string {
  if (!value) return '-'
  return value.slice(0, 10)
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const normalized = value.replace('T', ' ')
  return normalized.slice(0, 16)
}

function getVerifyStatusText(status?: string | null): string {
  const map: Record<string, string> = {
    pending: '待核销',
    verified: '已核销',
    expired: '已过期',
    none: '无票券',
  }
  return map[status || ''] || status || '-'
}

function getLogResultText(result: string): string {
  const map: Record<string, string> = {
    success: '成功',
    failed: '失败',
    duplicate: '重复',
  }
  return map[result] || result
}

function getLogBadgeClass(result: string): string {
  if (result === 'success') return 'staff-badge--done'
  if (result === 'duplicate') return 'staff-badge--warning'
  return 'staff-badge--failed'
}
</script>

<style lang="scss" scoped>
.page-staff {
  min-height: 100vh;
  background: var(--color-bg);
  padding-bottom: 48rpx;
}

.staff-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 36rpx 28rpx 28rpx;
  background: linear-gradient(135deg, #2d4a3e, #527263);
}

.staff-hero__main {
  min-width: 0;
}

.staff-hero__title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #fff;
}

.staff-hero__subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.72);
}

.staff-scan-btn {
  width: 156rpx;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  border-radius: 8rpx;
  background: #c8a872;

  text {
    color: #2d2417;
    font-size: 26rpx;
    font-weight: 700;
  }
}

.staff-scan-btn__icon {
  font-size: 30rpx;
}

.staff-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 24rpx 20rpx;
  background: #fff;
  border-bottom: 1rpx solid rgba(45, 74, 62, 0.08);
}

.staff-stat {
  min-width: 0;
  text-align: center;
}

.staff-stat__num {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: var(--color-primary);
}

.staff-stat__label {
  display: block;
  margin-top: 4rpx;
  font-size: 22rpx;
  color: var(--color-text-secondary);
}

.staff-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
  padding: 20rpx 24rpx 8rpx;
}

.staff-tab {
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #fff;
  border: 1rpx solid rgba(45, 74, 62, 0.1);

  text {
    font-size: 26rpx;
    color: var(--color-text-secondary);
  }
}

.staff-tab--active {
  background: var(--color-primary);
  border-color: var(--color-primary);

  text {
    color: #fff;
    font-weight: 700;
  }
}

.staff-content {
  padding: 16rpx 24rpx;
}

.staff-loading,
.staff-empty {
  min-height: 260rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.staff-loading text,
.staff-empty__desc {
  font-size: 26rpx;
  color: var(--color-text-placeholder);
}

.staff-empty__title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--color-text);
}

.staff-empty__desc {
  margin-top: 12rpx;
}

.staff-card,
.staff-log {
  margin-bottom: 18rpx;
  padding: 24rpx;
  border-radius: 8rpx;
  background: #fff;
  box-shadow: var(--shadow-sm);
  border: 1rpx solid rgba(45, 74, 62, 0.06);
}

.staff-card__top,
.staff-log__line,
.order-detail__header,
.order-detail__item-top,
.order-detail__total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.staff-card__title {
  min-width: 0;
  flex: 1;
}

.staff-card__name,
.staff-log__name {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: var(--color-text);
}

.staff-card__meta,
.staff-log__meta,
.order-detail__item-meta {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 8rpx;

  text {
    font-size: 24rpx;
    color: var(--color-text-secondary);
  }
}

.staff-card__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx 20rpx;
  margin-top: 20rpx;

  view {
    min-width: 0;
  }

  text {
    display: block;
    font-size: 24rpx;
  }

  text:first-child {
    color: var(--color-text-placeholder);
  }

  text:last-child {
    margin-top: 4rpx;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.staff-card__remark,
.staff-card__bottom,
.staff-log__reason,
.order-detail__remark {
  margin-top: 18rpx;
  padding: 14rpx 16rpx;
  border-radius: 8rpx;
  background: #faf6f0;

  text {
    display: block;
    font-size: 24rpx;
    color: var(--color-text-secondary);
    line-height: 34rpx;
  }
}

.staff-badge {
  flex-shrink: 0;
  min-width: 96rpx;
  height: 44rpx;
  padding: 0 14rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  font-size: 22rpx;
  font-weight: 700;
}

.staff-badge--pending {
  color: #8a5d18;
  background: #fff2cf;
}

.staff-badge--done {
  color: #2d4a3e;
  background: #e8f3ed;
}

.staff-badge--warning {
  color: #7a5b18;
  background: #f6edce;
}

.staff-badge--failed {
  color: #9b2f2f;
  background: #fbe5e5;
}

.onsite-panel {
  padding: 24rpx;
  border-radius: 8rpx;
  background: #fff;
  box-shadow: var(--shadow-sm);
  border: 1rpx solid rgba(45, 74, 62, 0.06);
}

.onsite-segment {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10rpx;
  margin-bottom: 16rpx;
}

.onsite-segment--light {
  margin-bottom: 22rpx;
}

.onsite-segment__item {
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #f6f3ec;
  border: 1rpx solid rgba(45, 74, 62, 0.1);

  text {
    font-size: 26rpx;
    color: var(--color-text-secondary);
    font-weight: 600;
  }
}

.onsite-segment__item--active {
  background: var(--color-primary);
  border-color: var(--color-primary);

  text {
    color: #fff;
  }
}

.onsite-field {
  margin-bottom: 18rpx;

  > text {
    display: block;
    margin-bottom: 8rpx;
    font-size: 24rpx;
    color: var(--color-text-secondary);
  }

  input,
  textarea {
    width: 100%;
    box-sizing: border-box;
    border-radius: 8rpx;
    background: #f8f7f3;
    border: 1rpx solid rgba(45, 74, 62, 0.1);
    color: var(--color-text);
    font-size: 28rpx;
  }

  input {
    height: 76rpx;
    padding: 0 20rpx;
  }

  textarea {
    min-height: 140rpx;
    padding: 18rpx 20rpx;
    line-height: 38rpx;
  }
}

.onsite-auth-code,
.onsite-result__path {
  display: flex;
  align-items: center;
  gap: 12rpx;

  input,
  > text {
    flex: 1;
    min-width: 0;
  }
}

.onsite-mini-btn {
  flex-shrink: 0;
  min-width: 112rpx;
  height: 88rpx;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #c8a872;

  text {
    font-size: 24rpx;
    color: #2d2417;
    font-weight: 700;
  }
}

.onsite-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14rpx;
  margin-top: 22rpx;
}

.onsite-action {
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;

  text {
    font-size: 28rpx;
    font-weight: 700;
  }
}

.onsite-action--ghost {
  background: #f6f3ec;

  text {
    color: var(--color-text-secondary);
  }
}

.onsite-action--primary {
  background: var(--color-primary);

  text {
    color: #fff;
  }
}

.onsite-result {
  margin-top: 24rpx;
  padding: 22rpx;
  border-radius: 8rpx;
  background: #e8f3ed;
}

.onsite-result__title {
  display: block;
  margin-bottom: 14rpx;
  font-size: 30rpx;
  font-weight: 700;
  color: var(--color-primary);
}

.onsite-result__row {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  padding: 8rpx 0;

  text {
    font-size: 24rpx;
    color: var(--color-text-secondary);
  }

  text:last-child {
    min-width: 0;
    color: var(--color-text);
    overflow-wrap: anywhere;
    text-align: right;
  }
}

.onsite-query-btn {
  height: 88rpx;
  margin-top: 18rpx;
  border-radius: 14rpx;
  background: #2d4a3e;
  color: #fff;
  font-size: 28rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.onsite-result__qrcode {
  width: 320rpx;
  height: 320rpx;
  margin: 18rpx auto 8rpx;
  padding: 14rpx;
  border-radius: 8rpx;
  background: #fff;

  image {
    width: 100%;
    height: 100%;
  }

  text {
    display: flex;
    height: 100%;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-size: 24rpx;
    color: var(--color-text-secondary);
    line-height: 34rpx;
  }
}

.onsite-result__path {
  margin-top: 12rpx;
  padding: 16rpx;
  border-radius: 8rpx;
  background: #fff;

  > text {
    font-size: 24rpx;
    color: var(--color-text);
    overflow-wrap: anywhere;
    line-height: 34rpx;
  }
}

.verify-mask,
.order-detail-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx 28rpx;
  background: rgba(0, 0, 0, 0.48);
}

.verify-popup,
.order-detail {
  width: 100%;
  max-height: 86vh;
  overflow-y: auto;
  border-radius: 8rpx;
  background: #fff;
}

.verify-popup {
  padding: 40rpx 32rpx 30rpx;
  text-align: center;
}

.verify-icon {
  width: 96rpx;
  height: 96rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 56rpx;
  font-weight: 700;
}

.verify-title {
  display: block;
  margin-top: 20rpx;
  font-size: 34rpx;
  font-weight: 700;
  color: var(--color-text);
}

.verify-info {
  margin-top: 24rpx;
}

.verify-row {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  padding: 12rpx 0;
  border-bottom: 1rpx solid rgba(45, 74, 62, 0.08);

  text {
    font-size: 26rpx;
  }

  text:first-child {
    color: var(--color-text-secondary);
  }

  text:last-child {
    min-width: 0;
    color: var(--color-text);
    font-weight: 600;
    overflow-wrap: anywhere;
  }
}

.verify-code-section {
  margin-top: 24rpx;
  padding: 24rpx;
  border-radius: 8rpx;
  background: #2d4a3e;
}

.verify-code-label,
.verify-code-tip {
  display: block;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.72);
}

.verify-code-num {
  display: block;
  margin: 12rpx 0;
  font-size: 64rpx;
  font-weight: 700;
  color: #fff;
  letter-spacing: 10rpx;
}

.verify-actions {
  margin-top: 28rpx;
}

.verify-action {
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
}

.verify-action--primary {
  background: var(--color-primary);

  text {
    color: #fff;
    font-size: 28rpx;
    font-weight: 700;
  }
}

.order-detail {
  padding: 28rpx;
}

.order-detail__title {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
  color: var(--color-text);
}

.order-detail__no {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: var(--color-text-secondary);
}

.order-detail__close {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 42rpx;
  color: var(--color-text-secondary);
}

.order-detail__user {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 22rpx;
  padding: 18rpx;
  border-radius: 8rpx;
  background: #f8faf8;

  text {
    min-width: 0;
    font-size: 26rpx;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.order-detail__item {
  margin-top: 20rpx;
  padding: 18rpx 0;
  border-top: 1rpx solid rgba(45, 74, 62, 0.08);
}

.order-detail__item-top text:first-child {
  min-width: 0;
  flex: 1;
  font-size: 28rpx;
  font-weight: 700;
  color: var(--color-text);
}

.order-detail__item-top text:last-child,
.order-detail__total text:last-child {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--color-primary);
}

.order-ticket {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 12rpx;
  padding: 12rpx 14rpx;
  border-radius: 8rpx;
  background: #faf6f0;

  text {
    font-size: 24rpx;
  }

  text:first-child {
    min-width: 0;
    color: var(--color-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.order-ticket--pending {
  color: #8a5d18;
}

.order-ticket--done {
  color: var(--color-primary);
}

.order-detail__total {
  margin-top: 22rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid rgba(45, 74, 62, 0.08);

  text:first-child {
    font-size: 26rpx;
    color: var(--color-text-secondary);
  }
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
