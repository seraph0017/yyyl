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

    <!-- 手动选择商品ID -->
    <el-form-item v-if="localProps.source === 'manual'" label="商品ID">
      <el-input
        v-model="productIdsText"
        type="textarea"
        :rows="2"
        placeholder="输入商品ID，用逗号分隔"
        @blur="parseProductIds"
      />
    </el-form-item>

    <!-- 分类选择 -->
    <el-form-item v-if="localProps.source === 'category'" label="分类ID">
      <el-input-number v-model="localProps.category_id" :min="1" @change="emitChange" />
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
import { reactive, ref, watch } from 'vue'
import type { ProductListPropsConfig } from '@/types/cms'

const props = defineProps<{ modelValue: ProductListPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: ProductListPropsConfig): void }>()

const localProps = reactive<ProductListPropsConfig>({
  source: 'manual',
  product_ids: [],
  count: 6,
  layout: 'grid',
  columns: 2,
})

const productIdsText = ref('')

watch(() => props.modelValue, (val) => {
  if (val) {
    Object.assign(localProps, val)
    productIdsText.value = (val.product_ids || []).join(', ')
  }
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}

function parseProductIds() {
  localProps.product_ids = productIdsText.value
    .split(/[,，\s]+/)
    .map(s => parseInt(s.trim()))
    .filter(n => !isNaN(n) && n > 0)
  emitChange()
}
</script>
