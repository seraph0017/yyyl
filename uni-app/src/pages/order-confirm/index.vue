<template>
  <!-- 订单确认页 -->
  <view class="page-confirm">
    <view class="section card temporary-state" v-if="from === 'temporary' && temporaryClaimError">
      <view class="temporary-state__icon">!</view>
      <text class="temporary-state__title">临时收款码不可用</text>
      <text class="temporary-state__desc">{{ temporaryClaimError }}</text>
      <view class="temporary-state__actions">
        <view class="temporary-state__btn temporary-state__btn--primary" @tap="reloadTemporaryClaim">
          <text>重新加载</text>
        </view>
        <view class="temporary-state__btn" @tap="goMineForPhone">
          <text>去授权手机号</text>
        </view>
      </view>
    </view>

    <!-- 出行人信息 -->
    <view class="section card" v-if="!temporaryClaimError && product && showIdentitySection">
      <view class="section__header">
        <text class="section__title">👤 出行人信息</text>
        <text class="section__required" v-if="product.identity_mode === 'required'">必填</text>
        <text class="section__optional" v-else>选填</text>
      </view>
      <view class="identity-list">
        <view
          :class="['identity-item', selectedIdentity && selectedIdentity.id === item.id ? 'identity-item--active' : '']"
          v-for="item in identities"
          :key="item.id"
          @tap="onSelectIdentity(item.id)"
        >
          <view class="identity-item__check">
            <view :class="['radio', selectedIdentity && selectedIdentity.id === item.id ? 'radio--checked' : '']"></view>
          </view>
          <view class="identity-item__info">
            <text class="identity-item__name">{{ item.name }}</text>
            <text class="identity-item__detail">{{ formatIdentityIdCard(item) }} · {{ formatIdentityPhone(item.phone) }}</text>
          </view>
        </view>
      </view>
      <view class="identity-add" @tap="onAddIdentity">
        <text>+ 添加出行人</text>
      </view>
    </view>

    <!-- 收货地址 -->
    <view class="section card" v-if="!temporaryClaimError && needAddress" @tap="onSelectAddress">
      <view class="section__header">
        <text class="section__title">📍 收货地址</text>
      </view>
      <view class="address-info" v-if="address">
        <text class="address-info__name">{{ address.contact_name }} {{ address.contact_phone }}</text>
        <text class="address-info__detail">{{ address.province }}{{ address.city }}{{ address.district }}{{ address.detail }}</text>
      </view>
      <view class="address-placeholder" v-else>
        <text>请选择收货地址</text>
        <text class="address-placeholder__arrow">›</text>
      </view>
    </view>

    <!-- 商品信息 -->
    <view class="section card" v-if="!temporaryClaimError && (product || cartProducts.length > 0)">
      <view class="section__header">
        <text class="section__title">商品信息</text>
      </view>
      <view class="confirm-product" v-if="product">
        <view class="confirm-product__image">
          <image :src="directProductImage" mode="aspectFill" v-if="directProductImage" />
          <text v-else>{{ directProductFallbackText }}</text>
        </view>
        <view class="confirm-product__info">
          <text class="confirm-product__name">{{ product.name }}</text>
          <text class="confirm-product__spec" v-if="selectedSkuLabel">{{ selectedSkuLabel }}</text>
          <view class="confirm-product__dates" v-if="showDates">
            <text class="confirm-product__date" v-for="d in dates" :key="d">📅 {{ d }}</text>
          </view>
          <text class="confirm-product__meta" v-if="activityTimeSlot">预约时间：{{ activityTimeSlot }}</text>
          <text class="confirm-product__meta" v-if="activityMeetingPoint">集合地点：{{ activityMeetingPoint }}</text>
          <view class="confirm-product__price-row">
            <PriceTag :price="product.current_price" size="small" />
            <text class="confirm-product__qty">x{{ displayQuantity }}</text>
          </view>
        </view>
      </view>
      <view
        class="confirm-product confirm-product--cart"
        v-for="item in cartProducts"
        :key="item.id"
      >
        <view class="confirm-product__image">
          <image :src="item.cover_image" mode="aspectFill" v-if="item.cover_image" />
          <text v-else>物</text>
        </view>
        <view class="confirm-product__info">
          <text class="confirm-product__name">{{ item.product_name }}</text>
          <text class="confirm-product__spec" v-if="formatSkuLabel(item.sku_spec_values)">
            {{ formatSkuLabel(item.sku_spec_values) }}
          </text>
          <view class="confirm-product__price-row">
            <PriceTag :price="item.price" size="small" />
            <text class="confirm-product__qty">x{{ item.quantity }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 费用明细 -->
    <view class="section card" v-if="!temporaryClaimError">
      <view class="section__header">
        <text class="section__title">💰 费用明细</text>
      </view>
      <view class="fee-row">
        <text>商品金额</text>
        <text>¥{{ formatAmount(totalPrice) }}</text>
      </view>
      <view class="fee-row fee-row--discount" v-if="discountAmount > 0">
        <text>优惠</text>
        <text>-¥{{ formatAmount(discountAmount) }}</text>
      </view>
      <view class="fee-row fee-row--deposit" v-if="depositAmount > 0">
        <text>押金</text>
        <text>¥{{ formatAmount(depositAmount) }}</text>
      </view>
      <view class="divider"></view>
      <view class="fee-row fee-row--total">
        <text>实付金额</text>
        <view class="fee-total-price">
          <text class="fee-total-symbol">¥</text>
          <text class="fee-total-amount">{{ formatAmount(actualPrice) }}</text>
        </view>
      </view>
    </view>

    <!-- 底部提交 -->
    <view class="confirm-footer safe-bottom" v-if="!temporaryClaimError">
      <view class="confirm-footer__price">
        <text class="confirm-footer__label">合计：</text>
        <text class="confirm-footer__symbol">¥</text>
        <text class="confirm-footer__amount">{{ formatAmount(actualPrice) }}</text>
      </view>
      <view :class="['confirm-footer__btn', submitting ? 'btn-disabled' : '']" @tap="onSubmitOrder">
        <text>{{ submitting ? '提交中...' : '提交订单' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { get, post, resolveImageUrl } from '@/utils/request'
import { ensureLogin, getUserInfo } from '@/utils/auth'
import { appendAttributionPayload } from '@/utils/attribution'
import { isCampsiteProduct, isDateBookingProduct, isRetailProduct, normalizeProductCategory } from '@/utils/product-rules'
import PriceTag from '@/components/price-tag/index.vue'
import type { IProduct, IIdentity, IAddress, IOrder, IOrderQuoteResponse, ICartItem } from '@/types'

interface CartListResponse {
  items: Array<{
    id: number
    product_id: number
    sku_id?: number | null
    product_name?: string
    image?: string
    price?: string | number
    quantity: number
    checked?: boolean
    product_type?: string
    stock_available?: boolean
    stock?: number
    sku_spec_values?: Record<string, unknown> | null
    shipping_required?: boolean
  }>
  summary?: {
    total_count: number
    total_price: string
  }
}

interface TemporaryOrderClaimResponse {
  order: IOrder & { biz_data?: Record<string, any> | null }
  payment_params?: Record<string, any> | null
}

const from = ref('direct')
const productId = ref(0)
const skuId = ref<number | null>(null)
const cartItemIds = ref<string[]>([])
const dates = ref<string[]>([])
const quantity = ref(1)
const product = ref<IProduct | null>(null)
const cartProducts = ref<ICartItem[]>([])
const identities = ref<IIdentity[]>([])
const selectedIdentity = ref<IIdentity | null>(null)
const address = ref<IAddress | null>(null)
const needAddress = ref(false)
const totalPrice = ref(0)
const discountAmount = ref(0)
const depositAmount = ref(0)
const actualPrice = ref(0)
const quote = ref<IOrderQuoteResponse | null>(null)
const submitting = ref(false)
const disclaimerSigned = ref(false)
const selectedSkuLabel = ref('')
const directProductImage = ref('')
const temporaryToken = ref('')
const temporaryClaimedOrder = ref<(IOrder & { biz_data?: Record<string, any> | null }) | null>(null)
const temporaryClaimError = ref('')
const activityTimeSlot = ref('')
const showDates = computed(() => !!product.value && isDateBookingProduct(product.value.category) && dates.value.length > 0)
const showIdentitySection = computed(() => !!product.value && isCampsiteProduct(product.value.category) && product.value.identity_mode !== 'none')
const displayQuantity = computed(() => {
  if (product.value && isDateBookingProduct(product.value.category)) {
    return dates.value.length || 1
  }
  return quantity.value
})
const directProductFallbackText = computed(() => {
  if (!product.value) return '物'
  return isCampsiteProduct(product.value.category) ? '营' : '物'
})
const activityMeetingPoint = computed(() => product.value?.ext_activity?.meeting_point || '')

onLoad((options) => {
  const hasTemporaryTokenParam = Boolean(options?.temporary_token || options?.scene)
  temporaryToken.value = safeDecodeTemporaryToken(options?.temporary_token || options?.scene)
  productId.value = Number(options?.product_id || 0)
  skuId.value = options?.sku_id ? Number(options.sku_id) : null
  dates.value = options?.dates ? options.dates.split(',') : []
  activityTimeSlot.value = options?.time_slot ? safeDecodeQueryValue(options.time_slot) : ''
  quantity.value = Number(options?.quantity || 1)
  from.value = hasTemporaryTokenParam ? 'temporary' : (options?.from || 'direct')
  cartItemIds.value = options?.cart_item_ids ? options.cart_item_ids.split(',') : []
  disclaimerSigned.value = options?.disclaimer_signed === '1' || options?.disclaimer_signed === 'true'

  loadData()
})

onShow(() => {
  if (showIdentitySection.value) {
    loadIdentities()
  }
})

function safeDecodeTemporaryToken(value: unknown): string {
  const raw = String(value || '')
  if (!raw) return ''
  try {
    return decodeURIComponent(raw)
  } catch {
    temporaryClaimError.value = '临时收款码参数无效'
    return ''
  }
}

function safeDecodeQueryValue(value: unknown): string {
  const raw = String(value || '')
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
}

async function loadData() {
  try {
    const loggedIn = await ensureLogin()
    if (!loggedIn) return

    if (from.value === 'temporary') {
      if (!ensureUserPhoneBeforeTemporaryClaim()) return
      await applyTemporaryOrderClaim()
      return
    }

    if (from.value === 'cart') {
      const selectedIds = cartItemIds.value.map(Number).filter(Boolean)
      if (selectedIds.length === 0) {
        uni.showToast({ title: '请选择要结算的商品', icon: 'none' })
        return
      }
      await loadCartCheckoutPreview(selectedIds)
      return
    }

    // 加载商品信息（如果是直接购买）
    if (productId.value) {
      const raw = await get<Record<string, any>>(`/products/${productId.value}`)

      // 映射API原始数据为IProduct结构
      const category = normalizeProductCategory(raw.type, raw.category)

      const price = parseFloat(raw.base_price) || 0
      const selectedSku = skuId.value
        ? (raw.skus || []).find((sku: Record<string, any>) => Number(sku.id) === skuId.value)
        : null
      const displayPrice = selectedSku ? Number(selectedSku.price || price) : price
      const displayStock = selectedSku ? resolveSkuAvailableStock(selectedSku, Number(raw.stock || 0)) : Number(raw.stock || 0)
      selectedSkuLabel.value = formatSkuLabel(selectedSku?.spec_values || {})
      directProductImage.value = resolveProductImage(raw, selectedSku)

      const p: IProduct = {
        id: raw.id,
        name: raw.name || '',
        category,
        description: raw.description || '',
        cover_image: directProductImage.value,
        images: directProductImage.value ? [directProductImage.value] : [],
        base_price: displayPrice,
        current_price: displayPrice,
        original_price: displayPrice,
        status: raw.status || 'on_sale',
        tags: [],
        attributes: [],
        stock: displayStock,
        sales_count: 0,
        ticket_start_time: raw.sale_start_at || null,
        is_seckill: raw.is_seckill || false,
        has_disclaimer: raw.require_disclaimer !== false,
        identity_mode: raw.identity_mode || 'optional',
        deposit_amount: raw.ext_rental?.deposit_amount || 0,
        ext_shop: raw.ext_shop || undefined,
        ext_activity: raw.ext_activity || undefined,
      }

      product.value = p
      needAddress.value = Boolean(raw.ext_shop?.shipping_required)

      if (!isDateBookingProduct(p.category)) {
        dates.value = []
      }

      if (isDateBookingProduct(p.category) && dates.value.length === 0) {
        resetOrderAmounts()
        uni.showToast({ title: '请选择预约日期', icon: 'none' })
        return
      }

      await refreshQuote(false)
    }

    if (showIdentitySection.value) {
      await loadIdentities()
    } else {
      identities.value = []
      selectedIdentity.value = null
    }
  } catch (err: any) {
    uni.showToast({ title: err?.message || '加载数据失败', icon: 'none' })
  }
}

function formatSkuLabel(specValues?: Record<string, unknown> | null): string {
  return Object.values(specValues || {}).filter(Boolean).map(value => String(value)).join(' / ')
}

function resolveSkuAvailableStock(sku: Record<string, any>, fallbackStock = 0): number {
  if (sku.inventory_mode === 'shared_product' || sku.inventory_pool_id) {
    return Number(sku.inventory_pool_available ?? fallbackStock)
  }
  return Number(sku.stock || 0)
}

function resolveProductImage(raw: Record<string, any>, selectedSku?: Record<string, any> | null): string {
  const skuImage = selectedSku?.image_url ? resolveImageUrl(selectedSku.image_url) : ''
  if (skuImage) return skuImage
  const firstImage = Array.isArray(raw.images) ? raw.images[0] : null
  const imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url
  return imageUrl ? resolveImageUrl(imageUrl) : ''
}

async function loadCartCheckoutPreview(item_ids: number[]) {
  const data = await get<CartListResponse>('/cart/')
  const selected = (data.items || []).filter(item => item_ids.includes(item.id))
  cartProducts.value = selected.map(item => ({
    id: item.id,
    product_id: item.product_id,
    sku_id: item.sku_id ?? null,
    product_name: item.product_name || '',
    cover_image: resolveImageUrl(item.image || ''),
    sku_spec_values: item.sku_spec_values || null,
    price: toMoneyNumber(item.price),
    quantity: item.quantity,
    selected: item.checked !== false,
    stock: Number(item.stock ?? item.quantity),
    category: item.product_type as ICartItem['category'],
    shipping_required: Boolean(item.shipping_required),
  }))
  needAddress.value = cartProducts.value.some(item => item.shipping_required)
  const quoteData = await post<IOrderQuoteResponse>(
    '/cart/quote',
    { item_ids, disclaimer_signed: disclaimerSigned.value },
    { showError: false },
  )
  applyCartQuote(quoteData)
}

function toMoneyNumber(value: unknown): number {
  const num = typeof value === 'number' ? value : Number(value || 0)
  return Number.isFinite(num) ? num : 0
}

function formatAmount(value: number): string {
  return toMoneyNumber(value).toFixed(2)
}

function applyQuote(data: IOrderQuoteResponse) {
  quote.value = data
  totalPrice.value = toMoneyNumber(data.total_amount)
  discountAmount.value = toMoneyNumber(data.discount_amount)
  depositAmount.value = toMoneyNumber(data.deposit_amount)
  actualPrice.value = toMoneyNumber(data.actual_amount)

  const firstItem = data.items?.[0]
  const p = product.value
  if (p && firstItem) {
    const availableValues = data.items
      .map(item => item.available)
      .filter((item): item is number => typeof item === 'number')
    product.value = {
      ...p,
      current_price: toMoneyNumber(firstItem.unit_price),
      stock: availableValues.length ? Math.min(...availableValues) : p.stock,
      deposit_amount: depositAmount.value,
    }
  }
}

function applyCartQuote(data: IOrderQuoteResponse) {
  quote.value = data
  totalPrice.value = toMoneyNumber(data.total_amount)
  discountAmount.value = toMoneyNumber(data.discount_amount)
  depositAmount.value = toMoneyNumber(data.deposit_amount)
  actualPrice.value = toMoneyNumber(data.actual_amount)
  cartProducts.value = cartProducts.value.map((item) => {
    const quoteItem = data.items.find(row => row.product_id === item.product_id && (row.sku_id || null) === (item.sku_id || null))
      || data.items.find(row => row.product_id === item.product_id)
    if (!quoteItem) return item
    return {
      ...item,
      price: toMoneyNumber(quoteItem.unit_price),
      stock: Number(quoteItem.available ?? item.stock),
    }
  })
}

async function applyTemporaryOrderClaim() {
  if (!temporaryToken.value) {
    throw new Error('临时收款码无效')
  }
  temporaryClaimError.value = ''
  let data: TemporaryOrderClaimResponse
  try {
    data = await post<TemporaryOrderClaimResponse>(
      `/orders/temporary/${encodeURIComponent(temporaryToken.value)}/claim`,
      {},
      { showError: false },
    )
  } catch (err: any) {
    temporaryClaimError.value = err?.message || '临时收款码已过期或已被认领，请联系现场工作人员重新生成。'
    product.value = null
    resetOrderAmounts()
    throw err
  }
  const order = data.order
  const firstItem = order.items?.[0]
  const temporaryInfo = order.biz_data?.temporary_order || {}
  const itemName = firstItem?.product_name || temporaryInfo.item_name || '现场临时订单'
  const itemQuantity = firstItem?.quantity || 1
  const itemPrice = toMoneyNumber(firstItem?.unit_price || order.total_amount)
  temporaryClaimedOrder.value = order
  from.value = 'temporary'
  cartProducts.value = []
  identities.value = []
  selectedIdentity.value = null
  needAddress.value = false
  quote.value = null
  dates.value = firstItem?.date ? [firstItem.date] : []
  quantity.value = itemQuantity
  totalPrice.value = toMoneyNumber(order.total_amount)
  discountAmount.value = toMoneyNumber(order.discount_amount)
  depositAmount.value = 0
  actualPrice.value = toMoneyNumber(order.actual_amount)
  selectedSkuLabel.value = order.order_no
  const firstItemImage = firstItem?.cover_image || (firstItem as any)?.product_image || ''
  directProductImage.value = firstItemImage ? resolveImageUrl(firstItemImage) : ''
  product.value = {
    id: firstItem?.product_id || 0,
    name: itemName,
    category: 'camp_shop',
    description: temporaryInfo.remark || '',
    cover_image: directProductImage.value,
    images: directProductImage.value ? [directProductImage.value] : [],
    base_price: itemPrice,
    current_price: itemPrice,
    original_price: itemPrice,
    status: 'on_sale',
    tags: [],
    attributes: [],
    stock: itemQuantity,
    sales_count: 0,
    ticket_start_time: null,
    is_seckill: false,
    has_disclaimer: false,
    identity_mode: 'none',
    deposit_amount: 0,
  }
}

function resetOrderAmounts() {
  const emptyAmount = 0
  totalPrice.value = emptyAmount
  discountAmount.value = emptyAmount
  depositAmount.value = emptyAmount
  actualPrice.value = emptyAmount
}

function ensureUserPhoneBeforeTemporaryClaim(): boolean {
  const userInfo = getUserInfo()
  if (userInfo?.phone) return true
  temporaryClaimError.value = '请先授权手机号，再继续现场临时订单支付；未授权前不会占用这个收款码。'
  uni.showModal({
    title: '请先授权手机号',
    content: '现场临时订单支付前需要绑定手机号，便于订单通知和营地联系。',
    confirmText: '去授权',
    success(res) {
      if (res.confirm) {
        uni.switchTab({ url: '/pages/mine/index' })
      }
    },
  })
  return false
}

async function reloadTemporaryClaim() {
  if (!ensureUserPhoneBeforeTemporaryClaim()) return
  try {
    await applyTemporaryOrderClaim()
  } catch {
    // applyTemporaryOrderClaim 已设置页面错误态
  }
}

function goMineForPhone() {
  uni.switchTab({ url: '/pages/mine/index' })
}

function buildOrderPayload(includeIdentity = true): Record<string, unknown> {
  const p = product.value
  if (!p || from.value === 'cart') {
    return {}
  }

  const item: Record<string, unknown> = {
    product_id: productId.value,
    sku_id: skuId.value,
    dates: isDateBookingProduct(p.category) ? dates.value : [],
    quantity: quantity.value,
  }
  if (activityTimeSlot.value) item.time_slot = activityTimeSlot.value
  if (includeIdentity && showIdentitySection.value && selectedIdentity.value) {
    item.identity_ids = [selectedIdentity.value.id]
  }

  const payload: Record<string, unknown> = {
    items: [item],
    disclaimer_signed: disclaimerSigned.value,
  }
  if (address.value) payload.address_id = address.value.id
  return payload
}

async function refreshQuote(showError = true): Promise<IOrderQuoteResponse | null> {
  if (!product.value || from.value === 'cart') return null
  if (isDateBookingProduct(product.value.category) && dates.value.length === 0) {
    if (showError) {
      uni.showToast({ title: '请选择预约日期', icon: 'none' })
    }
    return null
  }
  const payload = buildOrderPayload(false)
  const data = await post<IOrderQuoteResponse>('/orders/quote', payload, { showError })
  applyQuote(data)
  return data
}

async function loadIdentities() {
  if (!showIdentitySection.value) return
  const previousSelectedId = selectedIdentity.value?.id
  const idList = await get<IIdentity[]>('/users/identities')
  identities.value = idList || []
  const matched = previousSelectedId ? identities.value.find(i => i.id === previousSelectedId) : null
  const defaultId = identities.value.find(i => i.is_default)
  selectedIdentity.value = matched || defaultId || identities.value[0] || null
}

/** 选择身份 */
function onSelectIdentity(id: number) {
  const identity = identities.value.find(i => i.id === id) || null
  selectedIdentity.value = identity
}

/** 添加身份 */
function onAddIdentity() {
  uni.navigateTo({ url: '/pages/identity/index?action=add' })
}

/** 选择地址 */
function onSelectAddress() {
  uni.navigateTo({
    url: '/pages/address/index?action=select',
    events: {
      select(addr: IAddress) {
        address.value = addr
      },
    },
  })
}

/** 提交订单 */
async function onSubmitOrder() {
  const p = product.value

  if (submitting.value) return
  if (!p && from.value !== 'cart' && from.value !== 'temporary') return
  if (p && isRetailProduct(p.category) && p.stock <= 0) {
    uni.showToast({ title: '该商品已售罄', icon: 'none' })
    return
  }
  if (p && isDateBookingProduct(p.category) && dates.value.length === 0) {
    uni.showToast({ title: '请选择预约日期', icon: 'none' })
    return
  }

  const userInfo = getUserInfo()
  if (!userInfo?.phone) {
    uni.showModal({
      title: '请先授权手机号',
      content: '下单前需要绑定手机号，便于订单通知和营地联系。',
      confirmText: '去授权',
      success(res) {
        if (res.confirm) {
          uni.switchTab({ url: '/pages/mine/index' })
        }
      },
    })
    return
  }

  // 验证身份
  if (p && showIdentitySection.value && p.identity_mode === 'required' && !selectedIdentity.value) {
    uni.showToast({ title: '请选择出行人信息', icon: 'none' })
    return
  }

  // 验证地址
  if (needAddress.value && !address.value) {
    uni.showToast({ title: '请选择收货地址', icon: 'none' })
    return
  }

  submitting.value = true

  try {
    if (from.value === 'temporary') {
      if (!temporaryClaimedOrder.value) {
        await applyTemporaryOrderClaim()
      }
      if (!temporaryClaimedOrder.value) {
        throw new Error('临时订单未生成')
      }
      uni.navigateTo({
        url: `/pages/payment/index?order_id=${temporaryClaimedOrder.value.id}&amount=${temporaryClaimedOrder.value.actual_amount}&order_no=${encodeURIComponent(temporaryClaimedOrder.value.order_no)}`,
      })
      return
    }

    if (from.value === 'cart') {
      const checkout = await post<{ order_no: string; order_ids: number[] }>(
        '/cart/checkout',
        {
          item_ids: cartItemIds.value.map(Number),
          address_id: address.value?.id,
          disclaimer_signed: disclaimerSigned.value,
        },
        { showError: false },
      )
      const firstOrderId = checkout.order_ids?.[0]
      if (!firstOrderId) {
        throw new Error('购物车结算失败')
      }
      if (checkout.order_ids.length > 1) {
        uni.showToast({ title: '已拆分为多个订单，请分别支付', icon: 'none' })
        uni.switchTab({ url: '/pages/order/index' })
        return
      }
      const orderDetail = await get<{ id: number; order_no: string; actual_amount: number }>(
        `/orders/${firstOrderId}`,
        undefined,
        { showError: false },
      )
      uni.navigateTo({
        url: `/pages/payment/index?order_id=${firstOrderId}&amount=${orderDetail.actual_amount}&order_no=${encodeURIComponent(orderDetail.order_no || checkout.order_no)}`,
      })
      return
    }

    await refreshQuote(false)
    const orderData: Record<string, unknown> = {}
    if (from.value === 'cart') {
      // 当前分支已提前 return，保留结构避免未来重构误用普通订单接口。
    } else {
      Object.assign(orderData, buildOrderPayload(true))
    }
    if (address.value) orderData.address_id = address.value.id
    appendAttributionPayload(orderData)

    const result = await post<{ id: number; order_no: string; actual_amount: number }>(
      '/orders',
      orderData,
      { showError: false },
    )
    uni.navigateTo({
      url: `/pages/payment/index?order_id=${result.id}&amount=${result.actual_amount}&order_no=${encodeURIComponent(result.order_no)}`,
    })
  } catch (err: any) {
    const message = err?.message || '提交订单失败'
    uni.showToast({ title: message, icon: 'none' })
  } finally {
    submitting.value = false
  }
}

function isMaskedValue(value?: string | null): boolean {
  return Boolean(value && value.includes('*'))
}

function maskIdCard(idCard: string): string {
  if (!idCard || idCard.length < 8) return idCard
  return idCard.slice(0, 4) + '****' + idCard.slice(-4)
}

function maskPhone(phone: string): string {
  if (!phone || phone.length < 7) return phone
  return phone.slice(0, 3) + '****' + phone.slice(-4)
}

function formatIdentityIdCard(item: IIdentity): string {
  if (item.id_card_masked) return item.id_card_masked
  return item.id_card ? maskIdCard(item.id_card) : '未填写身份证'
}

function formatIdentityPhone(phone?: string | null): string {
  if (!phone) return ''
  return isMaskedValue(phone) ? phone : maskPhone(phone)
}
</script>

<style lang="scss" scoped>
.page-confirm {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding: 32rpx 24rpx 160rpx;
}

.section {
  margin-bottom: 16rpx;
  padding: 24rpx;

  &__header {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-bottom: 20rpx;
  }

  &__title {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  &__required {
    font-size: var(--font-size-xs);
    color: var(--color-red);
    padding: 2rpx 8rpx;
    background-color: rgba(229, 57, 53, 0.08);
    border-radius: var(--radius-sm);
  }

  &__optional {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    padding: 2rpx 8rpx;
    background-color: var(--color-bg-grey);
    border-radius: var(--radius-sm);
  }
}

.temporary-state {
  text-align: center;
}

.temporary-state__icon {
  width: 80rpx;
  height: 80rpx;
  margin: 8rpx auto 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #fff2cf;
  color: #8a5d18;
  font-size: 44rpx;
  font-weight: 700;
}

.temporary-state__title {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
  color: var(--color-text);
}

.temporary-state__desc {
  display: block;
  margin-top: 14rpx;
  font-size: 26rpx;
  color: var(--color-text-secondary);
  line-height: 38rpx;
}

.temporary-state__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
  margin-top: 28rpx;
}

.temporary-state__btn {
  height: 76rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #f6f3ec;

  text {
    font-size: 26rpx;
    color: var(--color-text-secondary);
    font-weight: 700;
  }
}

.temporary-state__btn--primary {
  background: var(--color-primary);

  text {
    color: #fff;
  }
}

/* 身份信息 */
.identity-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.identity-item {
  display: flex;
  align-items: center;
  padding: 20rpx;
  background-color: var(--color-bg-grey);
  border-radius: var(--radius-md);
  border: 2rpx solid transparent;
  transition: all 0.2s ease;

  &--active {
    background-color: var(--color-primary-bg);
    border-color: var(--color-primary-lighter);
  }

  &__check {
    margin-right: 16rpx;
  }

  &__info {
    flex: 1;
  }

  &__name {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
    display: block;
  }

  &__detail {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 4rpx;
    display: block;
  }
}

.radio {
  width: 36rpx;
  height: 36rpx;
  border: 3rpx solid #D0D0D0;
  border-radius: 50%;
  transition: all 0.2s ease;

  &--checked {
    border-color: var(--color-primary);
    background-color: var(--color-primary);
    box-shadow: inset 0 0 0 4rpx #fff;
  }
}

.identity-add {
  padding: 20rpx;
  text-align: center;
  margin-top: 12rpx;

  text {
    font-size: var(--font-size-base);
    color: var(--color-primary);
    font-weight: 500;
  }
}

/* 地址 */
.address-info {
  &__name {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
    display: block;
  }

  &__detail {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: 6rpx;
    display: block;
  }
}

.address-placeholder {
  display: flex;
  justify-content: space-between;
  align-items: center;

  text { font-size: var(--font-size-base); color: var(--color-text-placeholder); }
  &__arrow { font-size: var(--font-size-xl); }
}

/* 商品信息 */
.confirm-product {
  display: flex;

  &__image {
    width: 160rpx;
    height: 160rpx;
    background-color: var(--color-bg-light);
    border-radius: var(--radius-md);
    display: flex;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
    margin-right: 20rpx;
    overflow: hidden;
    image { width: 100%; height: 100%; }
    text { font-size: 56rpx; }
  }

  &__info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  &__name {
    font-size: var(--font-size-md);
    font-weight: 600;
    color: var(--color-text);
  }

  &__dates {
    display: flex;
    flex-wrap: wrap;
    gap: 8rpx;
    margin-top: 8rpx;
  }

  &__date {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &__spec {
    display: block;
    margin-top: 6rpx;
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    line-height: 1.4;
  }

  &__meta {
    display: block;
    margin-top: 8rpx;
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.45;
  }

  &__price-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 12rpx;
  }

  &__qty {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  &--cart + &--cart {
    margin-top: 20rpx;
  }
}

/* 费用明细 */
.fee-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12rpx 0;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);

  &--discount text:last-child {
    color: var(--color-primary);
  }

  &--total {
    font-weight: 600;
    text:first-child { color: var(--color-text); font-size: var(--font-size-md); }
  }
}

.fee-total-price {
  display: flex;
  align-items: baseline;
}

.fee-total-symbol {
  font-size: var(--font-size-base);
  color: var(--color-orange);
  font-weight: 700;
}

.fee-total-amount {
  font-size: var(--font-size-xxl);
  color: var(--color-orange);
  font-weight: 700;
}

/* 底部提交 */
.confirm-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 32rpx;
  background-color: var(--color-bg-white);
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
  z-index: 100;

  &__price {
    display: flex;
    align-items: baseline;
  }

  &__label {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
  }

  &__symbol {
    font-size: var(--font-size-base);
    color: var(--color-orange);
    font-weight: 700;
  }

  &__amount {
    font-size: var(--font-size-xxl);
    color: var(--color-orange);
    font-weight: 700;
  }

  &__btn {
    height: 84rpx;
    padding: 0 60rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
    border-radius: var(--radius-round);

    text { font-size: var(--font-size-lg); color: #fff; font-weight: 600; }
    &:active { opacity: 0.85; }
  }
}
</style>
