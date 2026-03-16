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
      <!-- 渐变遮罩 -->
      <view class="product-card__image-fade" />
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
/* ===== 网格模式 — 野奢卡片 ===== */
.product-card--grid {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: 1rpx solid rgba(42, 37, 32, 0.03);
  transition: transform 0.3s var(--ease-out-expo), box-shadow 0.3s ease;

  .product-card__image-wrap {
    position: relative;
    width: 100%;
    height: 300rpx;
    overflow: hidden;
  }

  .product-card__image {
    width: 100%;
    height: 100%;
    transition: transform 0.6s var(--ease-out-expo);
  }

  .product-card__image-fade {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60rpx;
    background: linear-gradient(transparent, rgba(255, 255, 255, 0.6));
    pointer-events: none;
  }

  .product-card__placeholder {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, var(--color-bg-light) 0%, var(--color-bg-warm) 100%);
    display: flex;
    justify-content: center;
    align-items: center;
    text { font-size: 64rpx; }
  }

  .product-card__info {
    padding: 20rpx;
  }

  .product-card__name {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text);
    line-height: 1.5;
    min-height: 64rpx;
    letter-spacing: 0.5rpx;
  }

  .product-card__price-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 16rpx;
  }

  .product-card__sales {
    font-size: var(--font-size-xs);
    color: var(--color-text-placeholder);
    letter-spacing: 0.5rpx;
  }
}

/* ===== 列表模式 — 横排卡片 ===== */
.product-card--list {
  display: flex;
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  border: 1rpx solid rgba(42, 37, 32, 0.03);
  padding: 20rpx;
  transition: transform 0.3s var(--ease-out-expo);

  .product-card__image-wrap {
    position: relative;
    width: 200rpx;
    height: 200rpx;
    flex-shrink: 0;
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-right: 24rpx;
  }

  .product-card__image {
    width: 100%;
    height: 100%;
  }

  .product-card__image-fade {
    display: none;
  }

  .product-card__placeholder {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, var(--color-bg-light) 0%, var(--color-bg-warm) 100%);
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
    font-weight: 600;
    color: var(--color-text);
    line-height: 1.5;
    letter-spacing: 0.5rpx;
  }

  .product-card__attrs {
    display: flex;
    flex-wrap: wrap;
    gap: 8rpx;
    margin-top: 10rpx;
  }

  .product-card__attr {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    background: linear-gradient(135deg, var(--color-bg-light), var(--color-bg-grey));
    padding: 6rpx 14rpx;
    border-radius: var(--radius-sm);
    letter-spacing: 0.5rpx;
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

/* ===== 标签 — 铜金色调 ===== */
.product-card__tags {
  position: absolute;
  top: 16rpx;
  left: 16rpx;
  display: flex;
  gap: 8rpx;
  z-index: 2;
}

.product-card__tag {
  font-size: 20rpx;
  color: #fffefa;
  background: linear-gradient(135deg, var(--color-accent), #b8944e);
  padding: 6rpx 16rpx;
  border-radius: var(--radius-sm);
  font-weight: 600;
  letter-spacing: 1rpx;
  box-shadow: 0 2rpx 8rpx rgba(200, 168, 114, 0.3);
}

/* ===== 交互 ===== */
.product-card {
  &:active {
    transform: scale(0.97);
  }
}
</style>
