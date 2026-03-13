<template>
  <view class="page-index">
    <!-- 顶部品牌区 -->
    <view class="header">
      <view class="header__brand">
        <text class="header__logo">{{ site.logoEmoji }}</text>
        <view class="header__title">
          <text class="header__name">{{ site.brandName }}</text>
          <text class="header__slogan">{{ site.slogan }}</text>
        </view>
      </view>
      <view class="header__search" @tap="onSearchTap">
        <text class="header__search-icon">🔍</text>
        <text class="header__search-text">搜索营位、活动、装备...</text>
      </view>
    </view>

    <!-- 轮播区 -->
    <view class="banner-section">
      <swiper
        class="banner-swiper"
        :indicator-dots="false"
        autoplay
        circular
        :interval="4000"
        :duration="500"
        @change="onSwiperChange"
      >
        <swiper-item v-for="item in banners" :key="item.id">
          <view
            class="banner-card"
            :style="{ backgroundColor: item.color }"
            @tap="onBannerTap(item.id)"
          >
            <image
              class="banner-card__image"
              :src="item.image"
              mode="aspectFill"
              v-if="item.image"
            />
            <view class="banner-card__content" v-else>
              <text class="banner-card__title">{{ item.title }}</text>
              <view class="banner-card__btn">
                <text>立即查看</text>
              </view>
            </view>
          </view>
        </swiper-item>
      </swiper>
      <view class="banner-dots">
        <view
          class="banner-dot"
          :class="{ 'banner-dot--active': swiperCurrent === index }"
          v-for="(item, index) in banners"
          :key="item.id"
        />
      </view>
    </view>

    <!-- 分类导航 -->
    <view class="category-nav">
      <view class="section-title">
        <text class="section-title__text">探索露营</text>
      </view>
      <view class="category-grid">
        <view
          class="category-item"
          v-for="item in categories"
          :key="item.key"
          @tap="onCategoryTap(item.key)"
        >
          <view class="category-item__icon">
            <text>{{ item.icon }}</text>
          </view>
          <text class="category-item__name">{{ item.name }}</text>
        </view>
      </view>
    </view>

    <!-- 热门推荐 -->
    <view class="recommend-section">
      <view class="section-title">
        <text class="section-title__text">🔥 热门推荐</text>
        <view class="section-title__more" @tap="onViewMore">
          <text>查看更多</text>
          <text class="section-title__arrow">›</text>
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

    <view class="safe-bottom" style="height: 20rpx" />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { onPullDownRefresh, onShareAppMessage } from '@dcloudio/uni-app'
import { get, resolveImageUrl } from '@/utils/request'
import { currentSite } from '@/config/sites'
import type { IProduct, IProductAttribute, ProductCategory, IBanner } from '@/types'
import ProductCard from '@/components/product-card/index.vue'

const site = currentSite

interface ICategoryNav {
  key: ProductCategory
  name: string
  icon: string
}

const banners = ref<IBanner[]>([])
const categories = ref<ICategoryNav[]>([
  { key: 'daily_camping', name: '日常露营', icon: '🏕️' },
  { key: 'event_camping', name: '活动露营', icon: '🎃' },
  { key: 'equipment_rental', name: '装备租赁', icon: '⛺' },
  { key: 'daily_activity', name: '日常活动', icon: '🛶' },
  { key: 'special_activity', name: '特定活动', icon: '🎪' },
  { key: 'camp_shop', name: '小商店', icon: '🛒' },
  { key: 'merchandise', name: '周边商品', icon: '👕' },
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
      get<{ list: Record<string, unknown>[]; total: number }>('/products', { page_size: 18, status: 'on_sale' }, { needAuth: false })
        .catch(() => ({ list: [], total: 0 })),
    ])

    const loadedBanners = (bannerData?.banners || []).map((b) => ({
      ...b,
      image: resolveImageUrl(b.image),
    }))
    const products = (productData?.list || []).map(mapProduct)

    banners.value = loadedBanners.length > 0
      ? loadedBanners
      : [
          { id: 1, image: '', title: '🌲 春日露营季 · 限时特惠', link: '', color: site.primaryColor },
          { id: 2, image: '', title: '🎶 仲夏夜星空音乐节', link: '', color: '#FF6B35' },
          { id: 3, image: '', title: '⛺ 新品装备上线 · 全场9折', link: '', color: '#2196F3' },
        ]

    recommendProducts.value = products
    loading.value = false
  } catch (err) {
    console.error('首页加载失败:', err)
    loading.value = false
    uni.showToast({ title: '加载失败，下拉刷新重试', icon: 'none' })
  }
}

function onSwiperChange(e: { detail: { current: number } }) {
  swiperCurrent.value = e.detail.current
}

function onSearchTap() {
  uni.navigateTo({ url: '/pages/category/index?search=1' })
}

function onCategoryTap(_key: string) {
  uni.switchTab({ url: '/pages/category/index' })
}

function onBannerTap(id: number) {
  console.log('Banner tapped:', id)
}

function onViewMore() {
  uni.switchTab({ url: '/pages/category/index' })
}

onMounted(() => {
  loadData()
})

onPullDownRefresh(() => {
  loadData().then(() => {
    uni.stopPullDownRefresh()
  })
})

onShareAppMessage(() => ({
  title: site.shareTitle,
  path: '/pages/index/index',
}))
</script>

<style lang="scss" scoped>
.page-index {
  min-height: 100vh;
  background-color: var(--color-bg);
  padding-bottom: 20rpx;
}

.header {
  padding: 20rpx 32rpx;
  background: linear-gradient(180deg, var(--color-primary) 0%, var(--color-primary-light) 100%);

  &__brand {
    display: flex;
    align-items: center;
    margin-bottom: 20rpx;
  }

  &__logo { font-size: 56rpx; margin-right: 16rpx; }

  &__title { display: flex; flex-direction: column; }

  &__name {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: #fff;
    letter-spacing: 4rpx;
  }

  &__slogan {
    font-size: var(--font-size-xs);
    color: rgba(255, 255, 255, 0.8);
    margin-top: 2rpx;
    letter-spacing: 2rpx;
  }

  &__search {
    display: flex;
    align-items: center;
    height: 72rpx;
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: var(--radius-round);
    padding: 0 24rpx;

    &:active { background-color: rgba(255, 255, 255, 0.3); }
  }

  &__search-icon { font-size: 32rpx; margin-right: 12rpx; }
  &__search-text { font-size: var(--font-size-base); color: rgba(255, 255, 255, 0.7); }
}

.banner-section { padding: 24rpx 32rpx 12rpx; position: relative; }

.banner-swiper { height: 320rpx; border-radius: var(--radius-xl); overflow: hidden; }

.banner-card {
  width: 100%; height: 100%; border-radius: var(--radius-xl); overflow: hidden; position: relative;

  &__image { width: 100%; height: 100%; }

  &__content {
    width: 100%; height: 100%; display: flex; flex-direction: column;
    justify-content: center; padding: 40rpx; box-sizing: border-box;
  }

  &__title {
    font-size: var(--font-size-xl); font-weight: 700; color: #fff;
    line-height: 1.4; text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.2);
  }

  &__btn {
    display: inline-flex; align-items: center; padding: 12rpx 28rpx;
    background-color: rgba(255, 255, 255, 0.25); backdrop-filter: blur(10px);
    border-radius: var(--radius-round); margin-top: 24rpx; align-self: flex-start;
    text { font-size: var(--font-size-sm); color: #fff; font-weight: 500; }
  }
}

.banner-dots { display: flex; justify-content: center; margin-top: 16rpx; gap: 8rpx; }

.banner-dot {
  width: 12rpx; height: 12rpx; border-radius: 50%; background-color: #d9d9d9;
  transition: all 0.3s ease;

  &--active { width: 32rpx; border-radius: 6rpx; background-color: var(--color-primary); }
}

.category-nav { padding: 24rpx 32rpx; }

.section-title {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 24rpx;

  &__text { font-size: var(--font-size-lg); font-weight: 700; color: var(--color-text); }

  &__more {
    display: flex; align-items: center; font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    &:active { color: var(--color-primary); }
  }

  &__arrow { font-size: var(--font-size-lg); margin-left: 4rpx; }
}

.category-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20rpx 0; }

.category-item {
  display: flex; flex-direction: column; align-items: center; padding: 8rpx 0;

  &:active { opacity: 0.7; }

  &__icon {
    width: 96rpx; height: 96rpx; display: flex; justify-content: center; align-items: center;
    background-color: var(--color-bg-white); border-radius: var(--radius-xl);
    box-shadow: var(--shadow-sm); margin-bottom: 12rpx;
    text { font-size: 44rpx; }
  }

  &__name { font-size: var(--font-size-xs); color: var(--color-text-secondary); font-weight: 500; }
}

.recommend-section { padding: 12rpx 32rpx; }

.product-grid {
  display: flex; gap: 16rpx;
  &__col { flex: 1; display: flex; flex-direction: column; gap: 16rpx; }
}

.skeleton-card { background-color: var(--color-bg-card); border-radius: var(--radius-lg); overflow: hidden; }

.skeleton-image {
  width: 100%; height: 280rpx;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite;
}

.skeleton-text {
  height: 28rpx; margin: 16rpx 16rpx 0;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%; border-radius: 4rpx; animation: shimmer 1.5s infinite;

  &--short { width: 60%; margin-bottom: 16rpx; }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
