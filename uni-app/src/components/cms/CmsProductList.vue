<template>
  <view class="cms-product-list">
    <!-- 加载骨架屏 -->
    <view v-if="loading" class="cms-product-list__skeleton">
      <view class="cms-product-list__grid">
        <view class="cms-product-list__col">
          <view v-for="i in 3" :key="i" class="skeleton-card">
            <view class="skeleton-image" />
            <view class="skeleton-text" />
            <view class="skeleton-text skeleton-text--short" />
          </view>
        </view>
        <view class="cms-product-list__col">
          <view v-for="i in 3" :key="i" class="skeleton-card">
            <view class="skeleton-image" />
            <view class="skeleton-text" />
            <view class="skeleton-text skeleton-text--short" />
          </view>
        </view>
      </view>
    </view>

    <!-- 加载失败 -->
    <view v-else-if="loadError" class="cms-product-list__error">
      <text class="cms-product-list__error-icon">🏕️</text>
      <text class="cms-product-list__error-text">商品加载失败</text>
      <view class="cms-product-list__retry" @tap="loadProducts">
        <text>点击重试</text>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else-if="products.length === 0" class="cms-product-list__empty">
      <text class="cms-product-list__empty-icon">🌿</text>
      <text class="cms-product-list__empty-text">暂无相关商品</text>
    </view>

    <!-- grid 双列瀑布流 -->
    <view v-else-if="layoutMode === 'grid'" class="cms-product-list__grid">
      <view class="cms-product-list__col">
        <product-card
          v-for="(item, index) in products"
          :key="item.id"
          v-show="index % 2 === 0"
          :product="item"
          mode="grid"
        />
      </view>
      <view class="cms-product-list__col">
        <product-card
          v-for="(item, index) in products"
          :key="item.id"
          v-show="index % 2 === 1"
          :product="item"
          mode="grid"
        />
      </view>
    </view>

    <!-- list 单列列表 -->
    <view v-else-if="layoutMode === 'list'" class="cms-product-list__list">
      <product-card
        v-for="item in products"
        :key="item.id"
        :product="item"
        mode="list"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 商品列表组件
 * 组件挂载时主动请求商品数据，支持 grid/list 两种布局
 * 这是唯一需要发网络请求的 CMS 组件
 */
import { ref, computed, onMounted } from 'vue'
import { get, resolveImageUrl } from '@/utils/request'
import type { CmsProductListProps, CmsComponentStyle } from '@/types/cms'
import type { IProduct, IProductAttribute, ProductCategory } from '@/types'
import ProductCard from '@/components/product-card/index.vue'

interface Props {
  data: CmsProductListProps
  componentStyle?: CmsComponentStyle
}

const props = defineProps<Props>()

const products = ref<IProduct[]>([])
const loading = ref(true)
const loadError = ref(false)

/** 布局模式，默认 grid */
const layoutMode = computed(() => props.data.layout || 'grid')

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

/** 根据 source 构建请求参数并加载商品 */
async function loadProducts() {
  loading.value = true
  loadError.value = false

  try {
    const params: Record<string, string | number | boolean | undefined> = {
      status: 'on_sale',
    }

    switch (props.data.source) {
      case 'manual':
        if (props.data.product_ids?.length) {
          params.ids = props.data.product_ids.join(',')
        } else {
          loading.value = false
          return
        }
        break
      case 'category':
        if (props.data.category_key) {
          params.category = props.data.category_key
        }
        params.page_size = props.data.count || 6
        break
      case 'tag':
        if (props.data.tag) {
          params.tag = props.data.tag
        }
        params.page_size = props.data.count || 6
        break
    }

    const result = await get<{ list: Record<string, unknown>[]; total: number }>(
      '/products',
      params,
      { needAuth: false, showError: false },
    )

    products.value = (result?.list || []).map(mapProduct)
  } catch (err) {
    console.warn('[CmsProductList] 商品加载失败:', err)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadProducts()
})
</script>

<style lang="scss" scoped>
.cms-product-list {
  padding: 0 var(--spacing-lg);

  // grid 模式 — 双列瀑布流
  &__grid {
    display: flex;
    gap: 16rpx;
  }

  &__col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }

  // list 模式 — 单列卡片
  &__list {
    display: flex;
    flex-direction: column;
    gap: 16rpx;
  }

  // 加载失败
  &__error {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48rpx 0;
  }

  &__error-icon {
    font-size: 56rpx;
    opacity: 0.5;
    margin-bottom: 12rpx;
  }

  &__error-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
    margin-bottom: 16rpx;
  }

  &__retry {
    padding: 12rpx 36rpx;
    background: var(--color-primary);
    border-radius: var(--radius-round);
    color: var(--color-text-white);
    font-size: var(--font-size-sm);

    &:active {
      opacity: 0.85;
    }
  }

  // 空状态
  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48rpx 0;
  }

  &__empty-icon {
    font-size: 56rpx;
    opacity: 0.5;
    margin-bottom: 12rpx;
  }

  &__empty-text {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
  }
}

/* 骨架屏 */
.skeleton-card {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  border: 1rpx solid rgba(42, 37, 32, 0.04);
}

.skeleton-image {
  width: 100%;
  height: 280rpx;
  background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
  background-size: 300% 100%;
  animation: shimmer 2s infinite;
}

.skeleton-text {
  height: 28rpx;
  margin: 16rpx 20rpx 0;
  background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
  background-size: 300% 100%;
  border-radius: 6rpx;
  animation: shimmer 2s infinite;

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
