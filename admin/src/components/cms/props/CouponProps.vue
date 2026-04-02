<template>
  <el-form label-width="80px" size="small">
    <!-- 优惠券ID -->
    <el-form-item label="优惠券ID">
      <el-input
        v-model="couponIdsText"
        type="textarea"
        :rows="2"
        placeholder="输入优惠券ID，用逗号分隔"
        @blur="parseCouponIds"
      />
    </el-form-item>

    <!-- 布局样式 -->
    <el-form-item label="布局样式">
      <el-radio-group v-model="localProps.layout" @change="emitChange">
        <el-radio-button value="horizontal">横向</el-radio-button>
        <el-radio-button value="vertical">纵向</el-radio-button>
      </el-radio-group>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { CouponPropsConfig } from '@/types/cms'

const props = defineProps<{ modelValue: CouponPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: CouponPropsConfig): void }>()

const localProps = reactive<CouponPropsConfig>({
  coupon_ids: [],
  layout: 'horizontal',
})

const couponIdsText = ref('')

watch(() => props.modelValue, (val) => {
  if (val) {
    Object.assign(localProps, val)
    couponIdsText.value = (val.coupon_ids || []).join(', ')
  }
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}

function parseCouponIds() {
  localProps.coupon_ids = couponIdsText.value
    .split(/[,，\s]+/)
    .map(s => parseInt(s.trim()))
    .filter(n => !isNaN(n) && n > 0)
  emitChange()
}
</script>
