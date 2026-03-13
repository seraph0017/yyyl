<template>
  <view class="product-card" :class="[`product-card--${mode}`]" @tap="onTap">
    <!-- 商品图片 -->
    <view class="product-card__image-wrap">
      <image
        class="product-card__image"
        :src="product.cover_image"
        mode="aspectFill"
        v-if="product.cover_image"
        lazy-load
      />
      <view class="product-card__placeholder" v-else>
        <text>{{ categoryIcon }}</text>
      </view>
      <!-- 标签 -->
      <view class="product-card__tags" v-if="product.tags && product.tags.length > 0">
        <text
          class="product-card__tag"
          v-for="tag in product.tags"
          :key="tag"
        >{{ tag }}</text>
      </view>
    </view>

    <!-- 商品信息 -->
    <view class="product-card__info">
      <text class="product-card__name text-ellipsis-2">{{ product.name }}</text>

      <!-- 属性标签（列表模式） -->
      <view class="product-card__attrs" v-if="mode === 'list' && product.attributes && product.attributes.length > 0">
        <text
          class="product-card__attr"
          v-for="attr in product.attributes.slice(0, 3)"
          :key="attr.key"
        >{{ attr.icon }} {{ attr.value }}</text>
      </view>

      <!-- 价格 -->
      <view class="product-card__price-row">
        <price-tag :price="product.current_price" :original-price="product.original_price" size="small" />
        <text class="product-card__sales" v-if="product.sales_count > 0">
          已售{{ product.sales_count }}
        </text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getCategoryIcon } from '@/utils/util'
import type { IProduct } from '@/types'
import PriceTag from '../price-tag/index.vue'

const props = withDefaults(defineProps<{
  product: IProduct
  mode?: 'grid' | 'list'
}>(), {
  mode: 'grid',
})

const categoryIcon = computed(() => getCategoryIcon(props.product.category))

function onTap() {
  uni.navigateTo({
    url: `/pages/product-detail/index?id=${props.product.id}`,
  })
}
</script>

<style lang="scss" scoped>
/* ===== 网格模式 ===== */
.product-card--grid {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);

  .product-card__image-wrap {
    position: relative;
    width: 100%;
    height: 280rpx;
  }

  .product-card__image {
    width: 100%;
    height: 100%;
  }

  .product-card__placeholder {
    width: 100%;
    height: 100%;
    background-color: var(--color-bg-light);
    display: flex;
    justify-content: center;
    align-items: center;
    text { font-size: 64rpx; }
  }

  .product-card__info {
    padding: 16rpx;
  }

  .product-card__name {
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-text);
    line-height: 1.4;
    min-height: 60rpx;
  }

  .product-card__price-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 12rpx;
  }

  .product-card__sales {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
  }
}

/* ===== 列表模式 ===== */
.product-card--list {
  display: flex;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  padding: 20rpx;

  .product-card__image-wrap {
    position: relative;
    width: 200rpx;
    height: 200rpx;
    flex-shrink: 0;
    border-radius: var(--radius-md);
    overflow: hidden;
    margin-right: 20rpx;
  }

  .product-card__image {
    width: 100%;
    height: 100%;
  }

  .product-card__placeholder {
    width: 100%;
    height: 100%;
    background-color: var(--color-bg-light);
    display: flex;
    justify-content: center;
    align-items: center;
    text { font-size: 56rpx; }
  }

  .product-card__info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .product-card__name {
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--color-text);
    line-height: 1.4;
  }

  .product-card__attrs {
    display: flex;
    flex-wrap: wrap;
    gap: 8rpx;
    margin-top: 8rpx;
  }

  .product-card__attr {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    background-color: var(--color-bg-grey);
    padding: 4rpx 12rpx;
    border-radius: var(--radius-sm);
  }

  .product-card__price-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 12rpx;
  }

  .product-card__sales {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
  }
}

/* 标签 */
.product-card__tags {
  position: absolute;
  top: 12rpx;
  left: 12rpx;
  display: flex;
  gap: 8rpx;
}

.product-card__tag {
  font-size: 20rpx;
  color: #fff;
  background-color: var(--color-orange);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

/* 交互 */
.product-card {
  &:active {
    opacity: 0.85;
    transform: scale(0.98);
  }
}
</style>
