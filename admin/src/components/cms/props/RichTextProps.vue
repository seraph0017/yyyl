<template>
  <el-form label-width="80px" size="small">
    <el-form-item label="内容">
      <div class="rich-text-editor-wrap">
        <el-input
          v-model="localContent"
          type="textarea"
          :rows="8"
          placeholder="输入 HTML 内容"
          @blur="emitChange"
        />
        <div class="content-length">
          {{ contentSize }} / 50KB
        </div>
      </div>
    </el-form-item>

    <!-- 预览 -->
    <el-form-item label="预览">
      <div class="rich-text-preview" v-html="safeHtml" />
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import DOMPurify from 'dompurify'
import type { RichTextPropsConfig } from '@/types/cms'

const props = defineProps<{ modelValue: RichTextPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: RichTextPropsConfig): void }>()

const localContent = ref('')

watch(() => props.modelValue, (val) => {
  if (val) localContent.value = val.content || ''
}, { immediate: true, deep: true })

// XSS 防护
const safeHtml = computed(() => DOMPurify.sanitize(localContent.value))

// 内容大小
const contentSize = computed(() => {
  const bytes = new Blob([localContent.value]).size
  if (bytes < 1024) return `${bytes}B`
  return `${(bytes / 1024).toFixed(1)}KB`
})

function emitChange() {
  // 50KB 限制检查
  const bytes = new Blob([localContent.value]).size
  if (bytes > 50 * 1024) {
    ElMessage.warning('富文本内容超过50KB限制，请精简内容')
    return
  }
  emit('update:modelValue', { content: localContent.value })
}
</script>

<style lang="scss" scoped>
.rich-text-editor-wrap {
  width: 100%;
}

.content-length {
  text-align: right;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.rich-text-preview {
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
  font-size: 14px;
  line-height: 1.6;

  :deep(img) {
    max-width: 100%;
    height: auto;
  }
}
</style>
