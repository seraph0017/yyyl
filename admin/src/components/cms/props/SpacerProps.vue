<template>
  <el-form label-width="80px" size="small">
    <el-form-item label="高度">
      <el-slider v-model="localHeight" :min="1" :max="200" @change="emitChange" />
    </el-form-item>
    <el-form-item label="精确值">
      <el-input-number v-model="localHeight" :min="1" :max="200" @change="emitChange" />
      <span class="unit-text">px</span>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SpacerPropsConfig } from '@/types/cms'

const props = defineProps<{ modelValue: SpacerPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: SpacerPropsConfig): void }>()

const localHeight = ref(20)

watch(() => props.modelValue, (val) => {
  if (val) localHeight.value = val.height || 20
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { height: localHeight.value })
}
</script>

<style lang="scss" scoped>
.unit-text {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
