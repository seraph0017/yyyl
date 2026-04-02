<template>
  <view class="default-home">
    <!-- 轮播区 — 圆角卡片式 -->
    <view class="banner-section">
      <swiper
        class="banner-swiper"
        :indicator-dots="false"
        autoplay
        circular
        :interval="4500"
        :duration="600"
        @change="onSwiperChange"
        previous-margin="24rpx"
        next-margin="24rpx"
      >
        <swiper-item v-for="item in banners" :key="item.id" class="banner-swiper-item">
          <view
            class="banner-card"
            :class="{ 'banner-card--active': swiperCurrent === banners.indexOf(item) }"
            @tap="onBannerTap(item.id)"
          >
            <image
              class="banner-card__image"
              :src="item.image"
              mode="aspectFill"
              v-if="item.image"
            />
            <view class="banner-card__overlay" />
            <view class="banner-card__content" v-if="!item.image">
              <text class="banner-card__title">{{ item.title }}</text>
              <view class="banner-card__action">
                <text>了解详情</text>
                <text class="banner-card__arrow">→</text>
              </view>
            </view>
          </view>
        </swiper-item>
      </swiper>
      <view class="banner-indicator">
        <view
          class="banner-indicator__dot"
          :class="{ 'banner-indicator__dot--active': swiperCurrent === index }"
          v-for="(item, index) in banners"
          :key="item.id"
        />
      </view>
    </view>

    <!-- 分类导航 — 优雅图标卡片 -->
    <view class="category-section">
      <view class="section-header">
        <text class="section-heading">探索露营</text>
      </view>
      <view class="category-grid">
        <view
          class="category-item"
          v-for="item in categories"
          :key="item.key"
          @tap="onCategoryTap(item.key)"
        >
          <view class="category-item__icon" :style="{ background: item.bg }">
            <text>{{ item.icon }}</text>
          </view>
          <text class="category-item__name">{{ item.name }}</text>
        </view>
      </view>
    </view>

    <!-- 天气预报 -->
    <view class="weather-section">
      <weather-card />
    </view>

    <!-- 热门推荐 -->
    <view class="recommend-section">
      <view class="section-header">
        <text class="section-heading">精选推荐</text>
        <view class="section-header__more" @tap="onViewMore">
          <text>查看更多</text>
          <text class="section-header__arrow">›</text>
        </view>
      </view>

      <!-- 双列瀑布流 -->
      <view class="product-grid" v-if="!loading">
        <view class="product-grid__col">
          <product-card
            v-for="(item, index) in recommendProducts"
            :key="item.id"
            v-show="index % 2 === 0"
            :product="item"
            mode="grid"
          />
        </view>
        <view class="product-grid__col">
          <product-card
            v-for="(item, index) in recommendProducts"
            :key="item.id"
            v-show="index % 2 === 1"
            :product="item"
            mode="grid"
          />
        </view>
      </view>

      <!-- 加载骨架屏 -->
      <view class="product-grid" v-if="loading">
        <view class="product-grid__col">
          <view class="skeleton-card" v-for="i in 3" :key="i">
            <view class="skeleton-image" />
            <view class="skeleton-text" />
            <view class="skeleton-text skeleton-text--short" />
          </view>
        </view>
        <view class="product-grid__col">
          <view class="skeleton-card" v-for="i in 3" :key="i">
            <view class="skeleton-image" />
            <view class="skeleton-text" />
            <view class="skeleton-text skeleton-text--short" />
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * 默认首页组件（硬编码版本）
 * 当 CMS 配置加载失败且无缓存时，作为 L3 降级方案展示
 * 内容与原首页完全一致
 */
import { ref, onMounted } from 'vue'
import { get, resolveImageUrl } from '@/utils/request'
import type { IProduct, IProductAttribute, ProductCategory, IBanner } from '@/types'
import ProductCard from '@/components/product-card/index.vue'
import WeatherCard from '@/components/weather-card/index.vue'

interface ICategoryNav {
  key: string
  name: string
  icon: string
  bg: string
  url?: string
}

const banners = ref<IBanner[]>([])
const categories = ref<ICategoryNav[]>([
  { key: 'daily_camping', name: '日常露营', icon: '🏕️', bg: 'linear-gradient(135deg, #e8f5e9, #c8e6c9)' },
  { key: 'event_camping', name: '活动露营', icon: '🎃', bg: 'linear-gradient(135deg, #fff3e0, #ffe0b2)' },
  { key: 'equipment_rental', name: '装备租赁', icon: '⛺', bg: 'linear-gradient(135deg, #f3e5f5, #e1bee7)' },
  { key: 'daily_activity', name: '日常活动', icon: '🛶', bg: 'linear-gradient(135deg, #e3f2fd, #bbdefb)' },
  { key: 'special_activity', name: '特定活动', icon: '🎪', bg: 'linear-gradient(135deg, #fce4ec, #f8bbd0)' },
  { key: 'camp_shop', name: '小商店', icon: '🛒', bg: 'linear-gradient(135deg, #fff8e1, #ffecb3)' },
  { key: 'camp_map', name: '营地地图', icon: '🗺️', bg: 'linear-gradient(135deg, #e0f2f1, #b2dfdb)', url: '/pages-sub/product/camp-map/index' },
  { key: 'games', name: '趣味游戏', icon: '🎮', bg: 'linear-gradient(135deg, #ede7f6, #d1c4e9)', url: '/pages-sub/product/games/index' },
])
const recommendProducts = ref<IProduct[]>([])
const swiperCurrent = ref(0)
const loading = ref(true)

/** 将后端商品列表项转为前端 IProduct */
function mapProduct(item: Record<string, unknown>): IProduct {
  const images = (item.images as Array<{ url: string }>) || []
  const coverImage = images.length > 0 ? resolveImageUrl(images[0].url || '') : ''
  const tags: string[] = []
  if (item.is_seckill) tags.push('秒杀')

  const attributes: IProductAttribute[] = []
  const extCamping = item.ext_camping as Record<string, unknown> | undefined
  if (extCamping) {
    if (extCamping.has_electricity) attributes.push({ key: 'power', label: '电源', value: '有电', icon: '⚡' })
    if (extCamping.has_platform) attributes.push({ key: 'platform', label: '平台', value: '木平台', icon: '🪵' })
    if (extCamping.sun_exposure === 'shaded') attributes.push({ key: 'shade', label: '遮阳', value: '阴凉', icon: '🌳' })
    if (extCamping.area) attributes.push({ key: 'area', label: '区域', value: String(extCamping.area), icon: '📍' })
  }

  let category: ProductCategory = ((item.category || item.type || 'daily_camping') as string) as ProductCategory
  if (category === ('rental' as unknown)) category = 'equipment_rental'
  if (category === ('shop' as unknown)) category = 'camp_shop'

  return {
    id: item.id as number,
    name: item.name as string,
    category,
    description: (item.description as string) || '',
    cover_image: coverImage,
    images: images.map((img) => resolveImageUrl(img.url || '')),
    base_price: parseFloat(String(item.base_price)) || 0,
    current_price: parseFloat(String(item.base_price)) || 0,
    original_price: parseFloat(String(item.base_price)) || 0,
    status: (item.status as 'on_sale' | 'off_sale') || 'on_sale',
    tags,
    attributes,
    stock: 0,
    sales_count: 0,
    ticket_start_time: (item.sale_start_at as string) || null,
    is_seckill: (item.is_seckill as boolean) || false,
    has_disclaimer: item.require_disclaimer !== false,
    identity_mode: 'optional',
    deposit_amount: ((item.ext_rental as Record<string, unknown>)?.deposit_amount as number) || 0,
  }
}

async function loadData() {
  loading.value = true

  try {
    const [bannerData, productData] = await Promise.all([
      get<{ banners: IBanner[] }>('/pages/home_banner', undefined, { needAuth: false, showError: false })
        .catch(() => ({ banners: [] as IBanner[] })),
      get<{ list: Record<string, unknown>[]; total: number }>('/products', { page_size: 18, status: 'on_sale' }, { needAuth: false, showError: false })
        .catch(() => ({ list: [] as Record<string, unknown>[], total: 0 })),
    ])

    const loadedBanners = (bannerData?.banners || []).map((b) => ({
      ...b,
      image: resolveImageUrl(b.image),
    }))
    const products = (productData?.list || []).map(mapProduct)

    banners.value = loadedBanners.length > 0
      ? loadedBanners
      : [
          { id: 1, image: '', title: '🌲 春日露营季 · 限时特惠', link: '', color: '#2d4a3e' },
          { id: 2, image: '', title: '🎶 仲夏夜星空音乐节', link: '', color: '#3d3054' },
          { id: 3, image: '', title: '⛺ 新品装备上线 · 全场9折', link: '', color: '#4a3020' },
        ]

    recommendProducts.value = products
    loading.value = false
  } catch {
    loading.value = false
    if (banners.value.length === 0) {
      banners.value = [
        { id: 1, image: '', title: '🌲 春日露营季 · 限时特惠', link: '', color: '#2d4a3e' },
        { id: 2, image: '', title: '🎶 仲夏夜星空音乐节', link: '', color: '#3d3054' },
        { id: 3, image: '', title: '⛺ 新品装备上线 · 全场9折', link: '', color: '#4a3020' },
      ]
    }
  }
}

function onSwiperChange(e: { detail: { current: number } }) {
  swiperCurrent.value = e.detail.current
}

function onCategoryTap(_key: string) {
  const cat = categories.value.find((c) => c.key === _key)
  if (cat?.url) {
    uni.navigateTo({ url: cat.url })
  } else {
    uni.switchTab({ url: '/pages/category/index' })
  }
}

function onBannerTap(id: number) {
  console.log('Banner tapped:', id)
}

function onViewMore() {
  uni.switchTab({ url: '/pages/category/index' })
}

/** 供父组件调用刷新 */
function refresh() {
  return loadData()
}

onMounted(() => {
  loadData()
})

defineExpose({ refresh })
</script>

<style lang="scss" scoped>
/* ========== 轮播区 — 卡片式 ========== */
.banner-section {
  padding: 0 0 20rpx;
  margin-top: -16rpx;
  position: relative;
}

.banner-swiper {
  height: 340rpx;
}

.banner-swiper-item {
  padding: 0 8rpx;
}

.banner-card {
  width: 100%;
  height: 310rpx;
  border-radius: var(--radius-xl);
  overflow: hidden;
  position: relative;
  transition: transform 0.4s var(--ease-out-expo);

  &--active {
    transform: scale(1);
  }

  &__image {
    width: 100%;
    height: 100%;
  }

  &__overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent 30%, rgba(30, 40, 35, 0.7) 100%);
  }

  &__content {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 32rpx;
    z-index: 1;
  }

  &__title {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--color-text-white);
    line-height: 1.4;
    text-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.3);
    letter-spacing: 2rpx;
  }

  &__action {
    display: inline-flex;
    align-items: center;
    gap: 8rpx;
    margin-top: 16rpx;
    padding: 8rpx 24rpx;
    background: rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(10px);
    border: 1rpx solid rgba(255, 255, 255, 0.2);
    border-radius: var(--radius-round);

    text {
      font-size: var(--font-size-xs);
      color: rgba(255, 255, 255, 0.9);
      font-weight: 500;
      letter-spacing: 1rpx;
    }
  }

  &__arrow {
    font-size: var(--font-size-sm);
  }
}

/* 没有图片时的渐变背景 */
.banner-card:not(:has(.banner-card__image)) {
  background: linear-gradient(135deg, #2d4a3e, #3d6b5a);
}

.banner-indicator {
  display: flex;
  justify-content: center;
  margin-top: 16rpx;
  gap: 10rpx;

  &__dot {
    width: 8rpx;
    height: 8rpx;
    border-radius: 50%;
    background-color: var(--color-text-placeholder);
    opacity: 0.3;
    transition: all 0.4s var(--ease-out-expo);

    &--active {
      width: 28rpx;
      border-radius: 4rpx;
      background: linear-gradient(90deg, var(--color-accent), var(--color-primary-light));
      opacity: 1;
    }
  }
}

/* ========== 分类导航 ========== */
.category-section {
  padding: 24rpx 36rpx 8rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28rpx;

  &__more {
    display: flex;
    align-items: center;
    gap: 4rpx;

    text {
      font-size: var(--font-size-sm);
      color: var(--color-text-placeholder);
      letter-spacing: 1rpx;
    }

    &:active text {
      color: var(--color-primary);
    }
  }

  &__arrow {
    font-size: var(--font-size-lg);
  }
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24rpx 16rpx;
}

.category-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4rpx 0;
  transition: var(--transition-base);

  &:active {
    transform: scale(0.92);
  }

  &__icon {
    width: 100rpx;
    height: 100rpx;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: var(--radius-xl);
    margin-bottom: 12rpx;
    box-shadow: var(--shadow-sm);
    border: 1rpx solid rgba(255, 255, 255, 0.6);

    text {
      font-size: 44rpx;
    }
  }

  &__name {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    font-weight: 500;
    letter-spacing: 1rpx;
  }
}

/* ========== 天气区 ========== */
.weather-section {
  padding: 8rpx 36rpx 0;
}

/* ========== 热门推荐 ========== */
.recommend-section {
  padding: 24rpx 36rpx 0;
}

.product-grid {
  display: flex;
  gap: 16rpx;

  &__col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }
}

/* ========== 骨架屏 ========== */
.skeleton-card {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  border: 1rpx solid rgba(42, 37, 32, 0.04);
}

.skeleton-image {
  width: 100%;
  height: 280rpx;
  background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 30%, var(--color-bg-light) 60%, var(--color-bg-warm) 100%);
  background-size: 300% 100%;
  animation: shimmer 2s infinite ease-in-out;
}

.skeleton-text {
  height: 28rpx;
  margin: 16rpx 20rpx 0;
  background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 30%, var(--color-bg-light) 60%);
  background-size: 300% 100%;
  border-radius: 6rpx;
  animation: shimmer 2s infinite ease-in-out;

  &--short {
    width: 55%;
    margin-bottom: 20rpx;
  }
}

@keyframes shimmer {
  0% { background-position: 300% 0; }
  100% { background-position: -300% 0; }
}
</style>
