<template>
  <el-form label-width="80px" size="small">
    <!-- 商品来源 -->
    <el-form-item label="商品来源">
      <el-radio-group v-model="localProps.source" @change="emitChange">
        <el-radio value="manual">手动选择</el-radio>
        <el-radio value="category">按分类</el-radio>
        <el-radio value="tag">按标签</el-radio>
      </el-radio-group>
    </el-form-item>

    <!-- 手动选择商品 -->
    <el-form-item v-if="localProps.source === 'manual'" label="选择商品">
      <el-select
        v-model="localProps.product_ids"
        multiple
        filterable
        remote
        :remote-method="searchProducts"
        :loading="productLoading"
        placeholder="搜索并选择商品"
        style="width: 100%"
        @change="emitChange"
      >
        <el-option
          v-for="product in productOptions"
          :key="product.id"
          :label="product.name"
          :value="product.id"
        />
      </el-select>
    </el-form-item>

    <!-- 分类选择 -->
    <el-form-item v-if="localProps.source === 'category'" label="商品分类">
      <el-select v-model="localProps.category_key" filterable placeholder="选择商品分类" style="width: 100%" @change="emitChange">
        <el-option v-for="category in categoryOptions" :key="category.value" :label="category.label" :value="category.value" />
      </el-select>
    </el-form-item>

    <!-- 标签输入 -->
    <el-form-item v-if="localProps.source === 'tag'" label="标签">
      <el-input v-model="localProps.tag" placeholder="输入标签名" @blur="emitChange" />
    </el-form-item>

    <!-- 展示数量 -->
    <el-form-item label="展示数量">
      <el-input-number v-model="localProps.count" :min="1" :max="20" @change="emitChange" />
    </el-form-item>

    <!-- 布局模式 -->
    <el-form-item label="布局模式">
      <el-radio-group v-model="localProps.layout" @change="emitChange">
        <el-radio-button value="grid">网格</el-radio-button>
        <el-radio-button value="list">列表</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <!-- 列数（仅grid模式） -->
    <el-form-item v-if="localProps.layout === 'grid'" label="每行列数">
      <el-radio-group v-model="localProps.columns" @change="emitChange">
        <el-radio-button :value="2">2列</el-radio-button>
        <el-radio-button :value="3">3列</el-radio-button>
      </el-radio-group>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { getProducts } from '@/api/product'
import type { ProductListPropsConfig } from '@/types/cms'
import type { Product } from '@/types'

const props = defineProps<{ modelValue: ProductListPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: ProductListPropsConfig): void }>()

const localProps = reactive<ProductListPropsConfig>({
  source: 'manual',
  product_ids: [],
  count: 6,
  layout: 'grid',
  columns: 2,
})

const productLoading = ref(false)
const productOptions = ref<Array<Pick<Product, 'id' | 'name'>>>([])
const categoryOptions = [
  { label: '日常露营', value: 'daily_camping' },
  { label: '活动露营', value: 'event_camping' },
  { label: '装备租赁', value: 'equipment_rental' },
  { label: '日常活动', value: 'daily_activity' },
  { label: '特定活动', value: 'special_activity' },
  { label: '小商店', value: 'camp_shop' },
  { label: '周边商品', value: 'merchandise' },
]

const legacyCategoryIdMap: Record<number, string> = {
  1: 'daily_camping',
  2: 'event_camping',
  3: 'equipment_rental',
  4: 'daily_activity',
  5: 'special_activity',
  6: 'camp_shop',
  7: 'merchandise',
}

watch(() => props.modelValue, (val) => {
  if (val) {
    Object.assign(localProps, val)
    if (!localProps.category_key && val.category_id) {
      localProps.category_key = legacyCategoryIdMap[Number(val.category_id)]
    }
    if (val.product_ids?.length) {
      searchProducts()
    }
  }
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}

async function searchProducts(keyword = '') {
  productLoading.value = true
  try {
    const res = await getProducts({
      page: 1,
      page_size: 50,
      keyword: keyword || undefined,
    })
    productOptions.value = (res.data.list || []).map(product => ({
      id: product.id,
      name: product.name,
    }))
  } finally {
    productLoading.value = false
  }
}

onMounted(() => {
  searchProducts()
})
</script>
