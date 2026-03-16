<template>
  <view class="page-category">
    <!-- 搜索栏 -->
    <view class="search-bar" v-if="searchMode">
      <view class="search-bar__input-wrap">
        <text class="search-bar__icon">🔍</text>
        <input
          class="search-bar__input"
          placeholder="搜索营位、活动、装备..."
          :value="searchKeyword"
          @input="onSearchInput"
          @confirm="onSearchConfirm"
          :focus="searchMode"
          confirm-type="search"
        />
      </view>
      <text class="search-bar__cancel" @tap="onSearchCancel">取消</text>
    </view>

    <!-- Tab横向滑动 -->
    <scroll-view class="tab-scroll" scroll-x :show-scrollbar="false">
      <view class="tab-list">
        <view
          class="tab-item"
          :class="{ 'tab-item--active': activeTab === index }"
          v-for="(item, index) in tabs"
          :key="item.key"
          @tap="onTabChange(index)"
        >
          <text class="tab-item__icon">{{ item.icon }}</text>
          <text class="tab-item__name">{{ item.name }}</text>
          <view class="tab-item__line" v-if="activeTab === index" />
        </view>
      </view>
    </scroll-view>

    <!-- 筛选标签 -->
    <view class="filter-bar" v-if="tabs[activeTab].key === 'daily_camping' || tabs[activeTab].key === 'event_camping'">
      <scroll-view scroll-x :show-scrollbar="false">
        <view class="filter-list">
          <view
            class="filter-tag"
            :class="{ 'filter-tag--active': activeFilters.includes(item.key) }"
            v-for="item in filters"
            :key="item.key"
            @tap="onFilterToggle(item.key)"
          >
            <text class="filter-tag__icon">{{ item.icon }}</text>
            <text>{{ item.label }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <!-- 商品列表 -->
    <view class="product-list" v-if="products.length > 0">
      <view class="product-list__item" v-for="item in products" :key="item.id">
        <product-card :product="item" mode="list" />
      </view>
    </view>

    <!-- 空状态 -->
    <empty-state
      v-if="!loading && products.length === 0"
      icon="🏕️"
      title="暂无商品"
      description="当前分类暂无可用商品，请稍后再看"
    />

    <!-- 加载状态 -->
    <view class="loading-more" v-if="loading">
      <text class="loading-more__text">加载中...</text>
    </view>

    <!-- 到底提示 -->
    <view class="loading-more" v-if="!hasMore && products.length > 0">
      <view class="loading-more__line" />
      <text class="loading-more__text">已经到底啦</text>
      <view class="loading-more__line" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { onLoad, onReachBottom, onPullDownRefresh } from '@dcloudio/uni-app'
import { get, resolveImageUrl } from '@/utils/request'
import type { IProduct, ProductCategory } from '@/types'
import ProductCard from '@/components/product-card/index.vue'
import EmptyState from '@/components/empty-state/index.vue'

interface ICategoryTab {
  key: ProductCategory
  name: string
  icon: string
}

const TYPE_MAP: Record<string, string> = { rental: 'equipment_rental', shop: 'camp_shop' }
const CATEGORY_TO_TYPE: Record<string, string> = { equipment_rental: 'rental', camp_shop: 'shop' }

const tabs = ref<ICategoryTab[]>([
  { key: 'daily_camping', name: '日常露营', icon: '🏕️' },
  { key: 'event_camping', name: '活动露营', icon: '🎃' },
  { key: 'equipment_rental', name: '装备租赁', icon: '⛺' },
  { key: 'daily_activity', name: '日常活动', icon: '🛶' },
  { key: 'special_activity', name: '特定活动', icon: '🎪' },
  { key: 'camp_shop', name: '小商店', icon: '🛒' },
  { key: 'merchandise', name: '周边商品', icon: '👕' },
])

const filters = ref([
  { key: 'has_power', label: '有电', icon: '⚡' },
  { key: 'no_power', label: '无电', icon: '🔋' },
  { key: 'has_platform', label: '有木平台', icon: '🪵' },
  { key: 'sunshine', label: '阳光', icon: '☀️' },
  { key: 'shade', label: '阴凉', icon: '🌳' },
])

const activeTab = ref(0)
const activeFilters = ref<string[]>([])
const products = ref<IProduct[]>([])
const loading = ref(true)
const searchMode = ref(false)
const searchKeyword = ref('')
const page = ref(1)
const hasMore = ref(true)

function mapProductItem(item: Record<string, unknown>): IProduct {
  const images = (item.images as Array<{ url: string }>) || []
  const coverImage = images.length > 0 ? resolveImageUrl(images[0].url || '') : ''
  const tags: string[] = []
  if (item.is_seckill) tags.push('秒杀')
  let category = ((item.category || item.type || 'daily_camping') as string) as ProductCategory
  if (TYPE_MAP[category as string]) category = TYPE_MAP[category as string] as ProductCategory

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
    attributes: [],
    stock: 0,
    sales_count: 0,
    ticket_start_time: (item.sale_start_at as string) || null,
    is_seckill: (item.is_seckill as boolean) || false,
    has_disclaimer: true,
    identity_mode: 'optional',
    deposit_amount: 0,
  }
}

async function loadProducts() {
  loading.value = true
  const currentTab = tabs.value[activeTab.value]
  const params: Record<string, string | number | boolean | undefined> = {
    page: page.value,
    page_size: 10,
    status: 'on_sale',
  }
  const backendType = CATEGORY_TO_TYPE[currentTab.key] || currentTab.key
  params.type = backendType
  if (searchKeyword.value) params.keyword = searchKeyword.value

  try {
    const data = await get<{ list: Record<string, unknown>[]; total: number }>('/products', params, { needAuth: false })
    const newProducts = (data.list || []).map(mapProductItem)
    products.value = page.value === 1 ? newProducts : [...products.value, ...newProducts]
    hasMore.value = products.value.length < (data.total || 0)
    loading.value = false
  } catch (err) {
    console.error('加载商品列表失败:', err)
    loading.value = false
  }
}

function onTabChange(index: number) {
  activeTab.value = index
  page.value = 1
  hasMore.value = true
  products.value = []
  activeFilters.value = []
  loadProducts()
}

function onFilterToggle(key: string) {
  const idx = activeFilters.value.indexOf(key)
  if (idx >= 0) {
    activeFilters.value.splice(idx, 1)
  } else {
    activeFilters.value.push(key)
  }
  page.value = 1
  products.value = []
  loadProducts()
}

function onSearchInput(e: any) {
  searchKeyword.value = e.detail.value
}

function onSearchConfirm() {
  page.value = 1
  products.value = []
  loadProducts()
}

function onSearchCancel() {
  searchMode.value = false
  searchKeyword.value = ''
  loadProducts()
}

onLoad((options) => {
  if (options?.search === '1') searchMode.value = true
  if (options?.category) {
    const tabIndex = tabs.value.findIndex((t) => t.key === options.category)
    if (tabIndex >= 0) activeTab.value = tabIndex
  }
  loadProducts()
})

onReachBottom(() => {
  if (hasMore.value && !loading.value) {
    page.value++
    loadProducts()
  }
})

onPullDownRefresh(() => {
  page.value = 1
  hasMore.value = true
  loadProducts().then(() => uni.stopPullDownRefresh())
})
</script>

<style lang="scss" scoped>
.page-category { min-height: 100vh; background-color: var(--color-bg); }

.search-bar {
  display: flex; align-items: center; padding: 16rpx 28rpx;
  background: rgba(255, 255, 255, 0.88); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  &__input-wrap {
    flex: 1; display: flex; align-items: center; height: 72rpx;
    background: var(--color-bg-light); border-radius: var(--radius-round); padding: 0 24rpx;
    border: 1rpx solid rgba(42, 37, 32, 0.04);
  }
  &__icon { font-size: 28rpx; margin-right: 14rpx; opacity: 0.6; }
  &__input { flex: 1; font-size: var(--font-size-base); color: var(--color-text); letter-spacing: 0.5rpx; }
  &__cancel { font-size: var(--font-size-base); color: var(--color-primary); margin-left: 20rpx; padding: 12rpx; font-weight: 600; }
}

.tab-scroll {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border-bottom: 1rpx solid rgba(42, 37, 32, 0.04);
}
.tab-list { display: inline-flex; padding: 0 20rpx; white-space: nowrap; }
.tab-item {
  display: inline-flex; flex-direction: column; align-items: center;
  padding: 22rpx 28rpx; position: relative; transition: var(--transition-base);
  &:active { opacity: 0.7; }
  &__icon {
    font-size: 36rpx; margin-bottom: 6rpx;
    width: 56rpx; height: 56rpx; display: flex; justify-content: center; align-items: center;
    background: var(--color-bg-light); border-radius: var(--radius-sm);
    transition: var(--transition-base);
  }
  &__name { font-size: var(--font-size-sm); color: var(--color-text-secondary); white-space: nowrap; letter-spacing: 0.5rpx; }
  &--active .tab-item__icon { background: var(--color-primary-bg); }
  &--active .tab-item__name { color: var(--color-primary); font-weight: 700; }
  &__line {
    position: absolute; bottom: 4rpx; left: 50%; transform: translateX(-50%);
    width: 44rpx; height: 6rpx;
    background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
    border-radius: 3rpx;
  }
}

.filter-bar {
  background: rgba(255, 255, 255, 0.85);
  padding: 14rpx 0;
  border-bottom: 1rpx solid rgba(42, 37, 32, 0.04);
}
.filter-list { display: inline-flex; padding: 0 28rpx; gap: 14rpx; white-space: nowrap; }
.filter-tag {
  display: inline-flex; align-items: center; padding: 12rpx 28rpx;
  background: var(--color-bg-light); border-radius: var(--radius-round);
  font-size: var(--font-size-sm); color: var(--color-text-secondary);
  border: 2rpx solid transparent; transition: var(--transition-base);
  &__icon { margin-right: 8rpx; }
  &--active {
    background: linear-gradient(135deg, var(--color-primary-bg), rgba(200, 168, 114, 0.06));
    color: var(--color-primary); border-color: rgba(45, 74, 62, 0.12);
    font-weight: 600;
  }
  &:active { transform: scale(0.95); }
}

.product-list { padding: 20rpx 28rpx; &__item { margin-bottom: 16rpx; } }

.loading-more {
  display: flex; justify-content: center; align-items: center; padding: 40rpx 0; gap: 20rpx;
  &__text { font-size: var(--font-size-sm); color: var(--color-text-placeholder); letter-spacing: 1rpx; }
  &__line { width: 56rpx; height: 1rpx; background: linear-gradient(90deg, transparent, var(--color-text-placeholder), transparent); }
}
</style>
