<template>
  <!-- 商品详情页 -->
  <view class="page-detail" v-if="product">
    <!-- 图片轮播 -->
    <view class="detail-swiper">
      <swiper
        class="detail-swiper__inner"
        :autoplay="false"
        circular
        @change="onSwiperChange"
      >
        <swiper-item
          v-for="(item, idx) in (product.images.length > 0 ? product.images : ['placeholder'])"
          :key="idx"
        >
          <view class="detail-swiper__slide">
            <image :src="item" mode="aspectFill" v-if="item !== 'placeholder'" />
            <view class="detail-swiper__placeholder" v-else>
              <text>🏕️</text>
              <text class="detail-swiper__placeholder-text">{{ product.name }}</text>
            </view>
          </view>
        </swiper-item>
      </swiper>
      <view class="detail-swiper__indicator">
        <text>{{ swiperCurrent + 1 }} / {{ product.images.length || 1 }}</text>
      </view>
    </view>

    <!-- 价格信息 -->
    <view class="detail-price card">
      <view class="detail-price__row">
        <PriceTag :price="product.current_price" :originalPrice="product.original_price" size="large" unit="/晚" />
        <view class="detail-price__tags">
          <text class="tag tag--orange" v-for="tag in product.tags" :key="tag">{{ tag }}</text>
        </view>
      </view>
      <text class="detail-price__name">{{ product.name }}</text>
      <text class="detail-price__sales">已售 {{ product.sales_count }} | 库存 {{ product.stock }}</text>

      <!-- 秒杀倒计时 -->
      <view class="detail-seckill" v-if="notStarted && product.ticket_start_time">
        <text class="detail-seckill__label">🔥 开票倒计时</text>
        <Countdown :targetTime="product.ticket_start_time" mode="seckill" />
      </view>
    </view>

    <!-- 属性标签 -->
    <view class="detail-attrs card" v-if="product.attributes && product.attributes.length > 0">
      <view class="detail-section-title">营位属性</view>
      <view class="detail-attrs__list">
        <view class="detail-attr" v-for="attr in product.attributes" :key="attr.key">
          <text class="detail-attr__icon">{{ attr.icon }}</text>
          <view class="detail-attr__content">
            <text class="detail-attr__label">{{ attr.label }}</text>
            <text class="detail-attr__value">{{ attr.value }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 日期选择 -->
    <view class="detail-date card" @tap="onOpenCalendar">
      <view class="detail-section-title">选择日期</view>
      <view class="detail-date__selected" v-if="selectedDates.length > 0">
        <text class="detail-date__chip" v-for="d in selectedDates" :key="d">{{ d }}</text>
      </view>
      <view class="detail-date__placeholder" v-else>
        <text>请选择入营日期</text>
        <text class="detail-date__arrow">›</text>
      </view>
    </view>

    <!-- 数量选择 -->
    <view class="detail-quantity card" v-if="product.category === 'camp_shop' || product.category === 'merchandise'">
      <view class="detail-section-title">购买数量</view>
      <view class="detail-quantity__control">
        <view :class="['qty-btn', quantity <= 1 ? 'qty-btn--disabled' : '']" @tap="onQuantityMinus">
          <text>−</text>
        </view>
        <text class="qty-value">{{ quantity }}</text>
        <view :class="['qty-btn', quantity >= product.stock ? 'qty-btn--disabled' : '']" @tap="onQuantityAdd">
          <text>+</text>
        </view>
      </view>
    </view>

    <!-- 免责声明入口 -->
    <view class="detail-disclaimer card" v-if="product.has_disclaimer" @tap="onShowDisclaimer">
      <view class="detail-disclaimer__left">
        <text class="detail-disclaimer__icon">📜</text>
        <text class="detail-disclaimer__text">免责声明</text>
        <text :class="['detail-disclaimer__status', 'tag', disclaimerAgreed ? 'tag--primary' : 'tag--orange']">
          {{ disclaimerAgreed ? '已签署' : '需签署' }}
        </text>
      </view>
      <text class="detail-disclaimer__arrow">›</text>
    </view>

    <!-- 商品描述 -->
    <view class="detail-desc card">
      <view class="detail-section-title">商品介绍</view>
      <text class="detail-desc__content">{{ product.description }}</text>
    </view>

    <!-- 底部操作栏 -->
    <view class="detail-footer safe-bottom">
      <view class="detail-footer__left">
        <view class="detail-footer__icon-btn" @tap="onContactService">
          <text>💬</text>
          <text class="detail-footer__icon-text">客服</text>
        </view>
        <view class="detail-footer__icon-btn" @tap="onToggleFavorite">
          <text>{{ isFavorite ? '❤️' : '🤍' }}</text>
          <text class="detail-footer__icon-text">收藏</text>
        </view>
      </view>
      <view class="detail-footer__right">
        <view
          class="detail-footer__cart-btn"
          @tap="onAddToCart"
          v-if="product.category === 'camp_shop' || product.category === 'merchandise'"
        >
          <text>加入购物车</text>
        </view>
        <view :class="['detail-footer__book-btn', notStarted ? 'btn-disabled' : '']" @tap="onBook">
          <text>{{ notStarted ? '即将开票' : (product.category === 'camp_shop' || product.category === 'merchandise') ? '立即购买' : '立即预定' }}</text>
        </view>
      </view>
    </view>

    <!-- 日历弹窗 -->
    <view class="calendar-mask" v-if="showCalendar" @tap="onCloseCalendar">
      <view class="calendar-popup" @tap.stop>
        <view class="calendar-header">
          <view class="calendar-nav" @tap="onPrevMonth">
            <text>‹</text>
          </view>
          <text class="calendar-title">{{ currentMonth }}</text>
          <view class="calendar-nav" @tap="onNextMonth">
            <text>›</text>
          </view>
        </view>

        <view class="calendar-weekdays">
          <text v-for="w in ['日','一','二','三','四','五','六']" :key="w">{{ w }}</text>
        </view>

        <view class="calendar-days">
          <view
            v-for="item in calendarDays"
            :key="item.date"
            :class="[
              'calendar-day',
              item.isCurrentMonth ? '' : 'calendar-day--other',
              item.isSelected ? 'calendar-day--selected' : '',
              item.isToday ? 'calendar-day--today' : '',
              !item.isAvailable || item.isPast ? 'calendar-day--disabled' : ''
            ]"
            @tap="onSelectDate(item)"
          >
            <text class="calendar-day__num">{{ item.day }}</text>
            <text class="calendar-day__price" v-if="item.isCurrentMonth && item.isAvailable && item.price > 0">¥{{ item.price }}</text>
            <text class="calendar-day__label" v-if="item.isCurrentMonth && !item.isAvailable && !item.isPast">售罄</text>
          </view>
        </view>

        <view class="calendar-legend">
          <view class="calendar-legend__item">
            <view class="calendar-legend__dot calendar-legend__dot--workday"></view>
            <text>工作日</text>
          </view>
          <view class="calendar-legend__item">
            <view class="calendar-legend__dot calendar-legend__dot--weekend"></view>
            <text>周末</text>
          </view>
        </view>

        <view class="calendar-footer">
          <text class="calendar-footer__info">已选 {{ selectedDates.length }} 天</text>
          <view class="calendar-footer__btn" @tap="onCloseCalendar">
            <text>确定</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 免责声明弹窗 -->
    <view class="disclaimer-mask" v-if="showDisclaimer" @tap="onCloseDisclaimer">
      <view class="disclaimer-popup" @tap.stop>
        <view class="disclaimer-header">
          <text class="disclaimer-title">📜 免责声明</text>
          <text class="disclaimer-close" @tap="onCloseDisclaimer">✕</text>
        </view>
        <scroll-view class="disclaimer-content" scroll-y>
          <text>{{ disclaimerText }}</text>
        </scroll-view>
        <view class="disclaimer-footer">
          <view class="disclaimer-agree-btn" @tap="onAgreeDisclaimer">
            <text>我已阅读并同意</text>
          </view>
        </view>
      </view>
    </view>
  </view>

  <!-- 加载状态 -->
  <view class="page-loading" v-if="loading">
    <text>加载中...</text>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShareAppMessage } from '@dcloudio/uni-app'
import { get, resolveImageUrl } from '@/utils/request'
import { brandConfig } from '@/config/sites'
import PriceTag from '@/components/price-tag/index.vue'
import Countdown from '@/components/countdown/index.vue'
import type { IProduct, IProductAttribute, ProductCategory } from '@/types'

interface ICalendarDay {
  date: string
  day: number
  price: number
  dateType: string
  stock: number
  isAvailable: boolean
  isSelected: boolean
  isToday: boolean
  isPast: boolean
  isCurrentMonth: boolean
}

const product = ref<IProduct | null>(null)
const swiperCurrent = ref(0)
const selectedDates = ref<string[]>([])
const calendarDays = ref<ICalendarDay[]>([])
const currentMonth = ref('')
const calendarYear = ref(2026)
const calendarMonth = ref(3)
const totalPrice = ref(0)
const quantity = ref(1)
const showCalendar = ref(false)
const showDisclaimer = ref(false)
const disclaimerText = ref('')
const disclaimerAgreed = ref(false)
const loading = ref(true)
const isFavorite = ref(false)
const notStarted = ref(false)

onLoad((options) => {
  const id = options?.id || '1'
  loadProduct(Number(id))
})

onShareAppMessage(() => {
  const p = product.value
  return {
    title: p ? p.name : brandConfig.shareDefaultTitle,
    path: `/pages/product-detail/index?id=${p?.id || 1}`,
  }
})

/** 加载商品详情 */
async function loadProduct(id: number) {
  loading.value = true

  try {
    const detail = await get<Record<string, any>>(`/products/${id}`, undefined, { needAuth: false })

    const images = detail.images || []
    const coverImage = images.length > 0 ? resolveImageUrl(images[0].url || '') : ''
    const tags: string[] = []
    if (detail.is_seckill) tags.push('秒杀')

    const attributes: IProductAttribute[] = []
    if (detail.ext_camping) {
      if (detail.ext_camping.has_electricity) attributes.push({ key: 'power', label: '电源', value: '有电 ⚡', icon: '⚡' })
      if (detail.ext_camping.has_platform) attributes.push({ key: 'platform', label: '平台', value: '木平台 🪵', icon: '🪵' })
      if (detail.ext_camping.sun_exposure === 'sunny') attributes.push({ key: 'shade', label: '光照', value: '阳光 ☀️', icon: '☀️' })
      if (detail.ext_camping.sun_exposure === 'shaded') attributes.push({ key: 'shade', label: '光照', value: '阴凉 🌳', icon: '🌳' })
      if (detail.ext_camping.sun_exposure === 'mixed') attributes.push({ key: 'shade', label: '光照', value: '半阴半阳', icon: '⛅' })
      if (detail.ext_camping.max_persons) attributes.push({ key: 'size', label: '人数', value: `最多${detail.ext_camping.max_persons}人`, icon: '👥' })
      if (detail.ext_camping.area) attributes.push({ key: 'area', label: '区域', value: detail.ext_camping.area, icon: '📍' })
    }

    let category: ProductCategory = (detail.category || detail.type || 'daily_camping') as ProductCategory
    if (category === 'rental' as any) category = 'equipment_rental'
    if (category === 'shop' as any) category = 'camp_shop'

    const p: IProduct = {
      id: detail.id,
      name: detail.name,
      category,
      description: detail.description || '',
      cover_image: coverImage,
      images: images.map((img: any) => resolveImageUrl(img.url || '')),
      base_price: parseFloat(detail.base_price) || 0,
      current_price: parseFloat(detail.base_price) || 0,
      original_price: parseFloat(detail.base_price) || 0,
      status: detail.status || 'on_sale',
      tags,
      attributes,
      stock: 0,
      sales_count: 0,
      ticket_start_time: detail.sale_start_at || null,
      is_seckill: detail.is_seckill || false,
      has_disclaimer: detail.require_disclaimer !== false,
      identity_mode: 'optional',
      deposit_amount: detail.ext_rental?.deposit_amount || 0,
    }

    disclaimerText.value = '免责声明\n\n1. 参与者确认已充分了解户外露营活动的风险性，自愿参加本次露营活动。\n2. 参与者应遵守营地管理规定，爱护公共设施，保持环境整洁。\n3. 参与者对自身及随行人员的安全负有责任。\n4. 如遇极端天气或不可抗力因素，营地有权调整或取消活动。\n5. 参与者应妥善管理个人财物，营地对个人财物遗失不承担赔偿责任。\n6. 未成年人须在监护人陪同下参加露营活动。\n7. 禁止在非指定区域使用明火，违规产生的一切后果由参与者自行承担。'

    product.value = p
    notStarted.value = !!p.ticket_start_time && new Date(p.ticket_start_time).getTime() > Date.now()
    loading.value = false

    generateCalendar()
  } catch (err) {
    console.error('加载商品详情失败:', err)
    loading.value = false
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
}

/** 生成日历 */
function generateCalendar() {
  const year = calendarYear.value
  const month = calendarMonth.value
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const startWeekDay = firstDay.getDay()

  const days: ICalendarDay[] = []

  // 上月补位
  const prevMonthLastDay = new Date(year, month - 1, 0).getDate()
  for (let i = startWeekDay - 1; i >= 0; i--) {
    const d = prevMonthLastDay - i
    const m = month === 1 ? 12 : month - 1
    const y = month === 1 ? year - 1 : year
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({
      date: dateStr, day: d, price: 0, dateType: '', stock: 0,
      isAvailable: false, isSelected: false, isToday: false, isPast: true, isCurrentMonth: false,
    })
  }

  // 当月日期
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const dayOfWeek = new Date(year, month - 1, d).getDay()
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
    const isPast = dateStr < todayStr

    days.push({
      date: dateStr,
      day: d,
      price: isWeekend ? 168 : 128,
      dateType: isWeekend ? '周末' : '工作日',
      stock: isPast ? 0 : Math.floor(Math.random() * 8) + 1,
      isAvailable: !isPast,
      isSelected: selectedDates.value.includes(dateStr),
      isToday: dateStr === todayStr,
      isPast,
      isCurrentMonth: true,
    })
  }

  // 下月补位
  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++) {
    const m = month === 12 ? 1 : month + 1
    const y = month === 12 ? year + 1 : year
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({
      date: dateStr, day: d, price: 0, dateType: '', stock: 0,
      isAvailable: false, isSelected: false, isToday: false, isPast: false, isCurrentMonth: false,
    })
  }

  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']

  calendarDays.value = days
  currentMonth.value = `${year}年${monthNames[month - 1]}`
}

/** 轮播切换 */
function onSwiperChange(e: any) {
  swiperCurrent.value = e.detail.current
}

/** 打开/关闭日历 */
function onOpenCalendar() {
  showCalendar.value = true
}

function onCloseCalendar() {
  showCalendar.value = false
}

/** 上个月 */
function onPrevMonth() {
  if (calendarMonth.value === 1) {
    calendarYear.value--
    calendarMonth.value = 12
  } else {
    calendarMonth.value--
  }
  generateCalendar()
}

/** 下个月 */
function onNextMonth() {
  if (calendarMonth.value === 12) {
    calendarYear.value++
    calendarMonth.value = 1
  } else {
    calendarMonth.value++
  }
  generateCalendar()
}

/** 选择日期 */
function onSelectDate(item: ICalendarDay) {
  if (!item.isAvailable || item.isPast) return

  const date = item.date
  const index = selectedDates.value.indexOf(date)
  if (index >= 0) {
    selectedDates.value.splice(index, 1)
  } else {
    selectedDates.value.push(date)
    selectedDates.value.sort()
  }

  generateCalendar()
  calcPrice()
}

/** 计算价格 */
function calcPrice() {
  let total = 0
  selectedDates.value.forEach(date => {
    const day = calendarDays.value.find(d => d.date === date)
    if (day) {
      total += day.price
    }
  })
  totalPrice.value = total * quantity.value
}

/** 数量加减 */
function onQuantityAdd() {
  if (product.value && quantity.value < product.value.stock) {
    quantity.value++
    calcPrice()
  }
}

function onQuantityMinus() {
  if (quantity.value > 1) {
    quantity.value--
    calcPrice()
  }
}

/** 免责声明 */
function onShowDisclaimer() {
  showDisclaimer.value = true
}

function onCloseDisclaimer() {
  showDisclaimer.value = false
}

function onAgreeDisclaimer() {
  disclaimerAgreed.value = true
  showDisclaimer.value = false
}

/** 加入购物车 */
function onAddToCart() {
  const p = product.value
  if (!p) return

  if (p.category !== 'camp_shop' && p.category !== 'merchandise') {
    uni.showToast({ title: '该商品不支持加入购物车，请直接预定', icon: 'none' })
    return
  }

  uni.showToast({ title: '已加入购物车', icon: 'success' })
}

/** 立即预定 */
function onBook() {
  const p = product.value
  if (!p) return

  if (notStarted.value) {
    uni.showToast({ title: '尚未开票，请等待', icon: 'none' })
    return
  }

  const needDate = ['daily_camping', 'event_camping', 'equipment_rental', 'daily_activity', 'special_activity']
  if (needDate.includes(p.category) && selectedDates.value.length === 0) {
    uni.showToast({ title: '请先选择日期', icon: 'none' })
    return
  }

  if (p.has_disclaimer && !disclaimerAgreed.value) {
    onShowDisclaimer()
    return
  }

  uni.navigateTo({
    url: `/pages/order-confirm/index?product_id=${p.id}&dates=${selectedDates.value.join(',')}&quantity=${quantity.value}`,
  })
}

/** 联系客服 */
function onContactService() {
  uni.navigateTo({ url: '/pages/customer-service/index' })
}

/** 收藏 */
function onToggleFavorite() {
  isFavorite.value = !isFavorite.value
  uni.showToast({
    title: isFavorite.value ? '已收藏' : '已取消收藏',
    icon: 'success',
  })
}
</script>

<style lang="scss" scoped>
.page-detail {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding-bottom: 160rpx;
}

/* 图片轮播 */
.detail-swiper {
  position: relative;

  &__inner {
    height: 560rpx;
  }

  &__slide {
    width: 100%;
    height: 100%;

    image {
      width: 100%;
      height: 100%;
    }
  }

  &__placeholder {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #2E7D32, #4CAF50);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;

    text:first-child {
      font-size: 120rpx;
    }
  }

  &__placeholder-text {
    font-size: var(--font-size-lg) !important;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 16rpx;
  }

  &__indicator {
    position: absolute;
    bottom: 24rpx;
    right: 24rpx;
    background-color: rgba(0, 0, 0, 0.5);
    padding: 6rpx 16rpx;
    border-radius: var(--radius-round);

    text {
      font-size: var(--font-size-xs);
      color: #fff;
    }
  }
}

/* 价格信息 */
.detail-price {
  margin: -24rpx 24rpx 16rpx;
  padding: 28rpx;
  position: relative;
  z-index: 2;

  &__row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  &__tags {
    display: flex;
    gap: 8rpx;
  }

  &__name {
    display: block;
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--color-text);
    margin-top: 16rpx;
    line-height: 1.4;
  }

  &__sales {
    display: block;
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    margin-top: 8rpx;
  }
}

.detail-seckill {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 20rpx;
  padding: 16rpx 20rpx;
  background: linear-gradient(135deg, rgba(229, 57, 53, 0.08), rgba(255, 107, 53, 0.08));
  border-radius: var(--radius-md);

  &__label {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-red);
  }
}

/* 通用段标题 */
.detail-section-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16rpx;
}

/* 属性标签 */
.detail-attrs {
  margin: 0 24rpx 16rpx;
  padding: 24rpx;

  &__list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16rpx;
  }
}

.detail-attr {
  display: flex;
  align-items: center;
  padding: 16rpx;
  background-color: var(--color-bg-light);
  border-radius: var(--radius-md);

  &__icon {
    font-size: 32rpx;
    margin-right: 12rpx;
  }

  &__content {
    display: flex;
    flex-direction: column;
  }

  &__label {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
  }

  &__value {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    font-weight: 500;
  }
}

/* 日期选择 */
.detail-date {
  margin: 0 24rpx 16rpx;
  padding: 24rpx;

  &__selected {
    display: flex;
    flex-wrap: wrap;
    gap: 12rpx;
  }

  &__chip {
    display: inline-flex;
    padding: 8rpx 20rpx;
    background-color: var(--color-primary-bg);
    color: var(--color-primary);
    font-size: var(--font-size-sm);
    border-radius: var(--radius-round);
    font-weight: 500;
  }

  &__placeholder {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12rpx 0;

    text {
      font-size: var(--font-size-base);
      color: var(--color-text-placeholder);
    }
  }

  &__arrow {
    font-size: var(--font-size-xl);
    color: var(--color-text-placeholder);
  }
}

/* 数量选择 */
.detail-quantity {
  margin: 0 24rpx 16rpx;
  padding: 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &__control {
    display: flex;
    align-items: center;
    gap: 4rpx;
  }
}

.qty-btn {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--color-bg-grey);
  border-radius: var(--radius-sm);

  text { font-size: 32rpx; color: var(--color-text); font-weight: 600; }
  &--disabled { opacity: 0.3; pointer-events: none; }
  &:active { background-color: #E8E8E8; }
}

.qty-value {
  min-width: 64rpx;
  text-align: center;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

/* 免责声明 */
.detail-disclaimer {
  margin: 0 24rpx 16rpx;
  padding: 24rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &__left {
    display: flex;
    align-items: center;
    gap: 12rpx;
  }

  &__icon { font-size: 32rpx; }
  &__text { font-size: var(--font-size-base); color: var(--color-text); }
  &__arrow { font-size: var(--font-size-xl); color: var(--color-text-placeholder); }
}

/* 商品描述 */
.detail-desc {
  margin: 0 24rpx 16rpx;
  padding: 24rpx;

  &__content {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    line-height: 1.8;
    white-space: pre-wrap;
  }
}

/* 底部操作栏 */
.detail-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  background-color: var(--color-bg-white);
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
  z-index: 100;

  &__left {
    display: flex;
    gap: 24rpx;
    margin-right: 24rpx;
  }

  &__icon-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rpx;

    text:first-child { font-size: 36rpx; }
    &:active { opacity: 0.7; }
  }

  &__icon-text {
    font-size: 18rpx !important;
    color: var(--color-text-secondary);
  }

  &__right {
    flex: 1;
    display: flex;
    gap: 12rpx;
  }

  &__cart-btn {
    flex: 1;
    height: 84rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #FFC107, #FF9800);
    border-radius: var(--radius-xl);

    text { font-size: var(--font-size-base); color: #fff; font-weight: 600; }
    &:active { opacity: 0.85; }
  }

  &__book-btn {
    flex: 1;
    height: 84rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
    border-radius: var(--radius-xl);

    text { font-size: var(--font-size-base); color: #fff; font-weight: 600; }
    &:active { opacity: 0.85; }
  }
}

/* 日历弹窗 */
.calendar-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: flex-end;
}

.calendar-popup {
  width: 100%;
  max-height: 85vh;
  background-color: var(--color-bg-white);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: 32rpx;
  animation: slideUp 0.3s ease;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.calendar-nav {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  background-color: var(--color-bg-grey);

  text { font-size: 36rpx; font-weight: 700; color: var(--color-text); }
  &:active { background-color: #E0E0E0; }
}

.calendar-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 8rpx;

  text {
    text-align: center;
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    padding: 12rpx 0;
  }
}

.calendar-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4rpx;
}

.calendar-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10rpx 0;
  min-height: 90rpx;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;

  &__num {
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--color-text);
  }

  &__price {
    font-size: 18rpx;
    color: var(--color-orange);
    margin-top: 2rpx;
  }

  &__label {
    font-size: 18rpx;
    color: var(--color-text-placeholder);
    margin-top: 2rpx;
  }

  &--other {
    .calendar-day__num { color: #D0D0D0; }
  }

  &--today {
    .calendar-day__num { color: var(--color-primary); font-weight: 700; }
  }

  &--selected {
    background-color: var(--color-primary);
    .calendar-day__num { color: #fff; }
    .calendar-day__price { color: rgba(255, 255, 255, 0.8); }
  }

  &--disabled {
    opacity: 0.4;
    pointer-events: none;
  }
}

.calendar-legend {
  display: flex;
  justify-content: center;
  gap: 32rpx;
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #F0F0F0;

  &__item {
    display: flex;
    align-items: center;
    gap: 8rpx;

    text { font-size: var(--font-size-xs); color: var(--color-text-secondary); }
  }

  &__dot {
    width: 16rpx;
    height: 16rpx;
    border-radius: 50%;

    &--workday { background-color: var(--color-primary); }
    &--weekend { background-color: var(--color-orange); }
  }
}

.calendar-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24rpx;

  &__info {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
  }

  &__btn {
    height: 76rpx;
    padding: 0 60rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
    border-radius: var(--radius-round);

    text { font-size: var(--font-size-base); color: #fff; font-weight: 600; }
    &:active { opacity: 0.85; }
  }
}

/* 免责声明弹窗 */
.disclaimer-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.disclaimer-popup {
  width: 85%;
  max-height: 80vh;
  background-color: var(--color-bg-white);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.2s ease;
}

.disclaimer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid #F0F0F0;
}

.disclaimer-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
}

.disclaimer-close {
  font-size: var(--font-size-xl);
  color: var(--color-text-placeholder);
  padding: 8rpx;
}

.disclaimer-content {
  padding: 28rpx 32rpx;
  max-height: 50vh;

  text {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
    line-height: 1.8;
    white-space: pre-wrap;
  }
}

.disclaimer-footer {
  padding: 20rpx 32rpx 32rpx;
}

.disclaimer-agree-btn {
  width: 100%;
  height: 84rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  border-radius: var(--radius-xl);

  text { font-size: var(--font-size-base); color: #fff; font-weight: 600; }
  &:active { opacity: 0.85; }
}

/* 动画 */
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

.page-loading {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  text { font-size: var(--font-size-base); color: var(--color-text-placeholder); }
}
</style>
