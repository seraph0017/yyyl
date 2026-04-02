<template>
  <el-form label-width="80px" size="small">
    <!-- 线条样式 -->
    <el-form-item label="线条样式">
      <el-radio-group v-model="localProps.style" @change="emitChange">
        <el-radio-button value="solid">实线</el-radio-button>
        <el-radio-button value="dashed">虚线</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <!-- 颜色 -->
    <el-form-item label="颜色">
      <el-color-picker v-model="localProps.color" @change="emitChange" />
    </el-form-item>

    <!-- 左右边距 -->
    <el-form-item label="左右边距">
      <el-input-number v-model="localProps.margin" :min="0" :max="100" @change="emitChange" />
      <span class="unit-text">px</span>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { DividerPropsConfig } from '@/types/cms'

const props = defineProps<{ modelValue: DividerPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: DividerPropsConfig): void }>()

const localProps = reactive<DividerPropsConfig>({
  style: 'solid',
  color: '#EEEEEE',
  margin: 16,
})

watch(() => props.modelValue, (val) => {
  if (val) Object.assign(localProps, val)
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}
</script>

<style lang="scss" scoped>
.unit-text {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
