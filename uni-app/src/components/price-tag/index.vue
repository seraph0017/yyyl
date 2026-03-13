<template>
  <view class="price-tag" :class="[`price-tag--${size}`]">
    <text class="price-tag__symbol">¥</text>
    <text class="price-tag__integer">{{ integerPart }}</text>
    <text class="price-tag__decimal" v-if="showDecimal">.{{ decimalPart }}</text>
    <text class="price-tag__original" v-if="originalPrice && originalPrice > price">
      ¥{{ formatOriginal }}
    </text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** 价格（元） */
  price: number
  /** 原价（元） */
  originalPrice?: number
  /** 尺寸 */
  size?: 'small' | 'medium' | 'large'
  /** 是否显示小数 */
  showDecimal?: boolean
}>(), {
  originalPrice: 0,
  size: 'medium',
  showDecimal: true,
})

const priceStr = computed(() => props.price.toFixed(2))
const integerPart = computed(() => priceStr.value.split('.')[0])
const decimalPart = computed(() => priceStr.value.split('.')[1])
const formatOriginal = computed(() => props.originalPrice.toFixed(2))
</script>

<style lang="scss" scoped>
.price-tag {
  display: inline-flex;
  align-items: baseline;
  color: var(--color-orange);
  font-weight: 700;

  &__symbol {
    font-size: 22rpx;
  }

  &__integer {
    font-size: 36rpx;
    font-variant-numeric: tabular-nums;
  }

  &__decimal {
    font-size: 22rpx;
    font-variant-numeric: tabular-nums;
  }

  &__original {
    color: var(--color-text-placeholder);
    font-size: var(--font-size-sm);
    font-weight: 400;
    text-decoration: line-through;
    margin-left: 8rpx;
  }

  /* 尺寸变体 */
  &--small {
    .price-tag__symbol { font-size: 18rpx; }
    .price-tag__integer { font-size: 28rpx; }
    .price-tag__decimal { font-size: 18rpx; }
  }

  &--large {
    .price-tag__symbol { font-size: 28rpx; }
    .price-tag__integer { font-size: 48rpx; }
    .price-tag__decimal { font-size: 28rpx; }
  }
}
</style>
