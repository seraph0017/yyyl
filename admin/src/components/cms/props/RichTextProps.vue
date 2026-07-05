<template>
  <el-form label-width="80px" size="small">
    <el-form-item label="内容">
      <div class="rich-text-editor-wrap">
        <div class="rich-toolbar">
          <el-button size="small" @click="applyCommand('bold')">B</el-button>
          <el-button size="small" @click="applyCommand('italic')">I</el-button>
          <el-button size="small" @click="applyCommand('heading')">H3</el-button>
          <el-select v-model="fontSize" size="small" style="width: 94px" @change="applyCommand('fontSize', fontSize)">
            <el-option label="14px" value="14px" />
            <el-option label="16px" value="16px" />
            <el-option label="18px" value="18px" />
            <el-option label="22px" value="22px" />
          </el-select>
          <el-color-picker v-model="textColor" size="small" @change="value => applyCommand('textColor', value || textColor)" />
          <el-color-picker v-model="bgColor" size="small" @change="value => applyCommand('backgroundColor', value || bgColor)" />
          <el-button size="small" @click="applyCommand('divider')">分割线</el-button>
          <el-button size="small" @click="insertImage">图片</el-button>
          <el-button size="small" @click="insertLink">链接</el-button>
        </div>
        <div
          ref="editorRef"
          class="rich-editable"
          contenteditable="true"
          @input="syncLocalContent"
          @blur="emitChange"
          v-html="safeHtml"
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
import type { RichTextPropsConfig } from '@/types/cms'
import { applyRichTextCommand, sanitizeRichText, type RichTextFormatCommand } from '@/utils/rich-text'

const props = defineProps<{ modelValue: RichTextPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: RichTextPropsConfig): void }>()

const localContent = ref('')
const editorRef = ref<HTMLElement>()
const fontSize = ref('16px')
const textColor = ref('#2d4a3e')
const bgColor = ref('#faf6f0')

watch(() => props.modelValue, (val) => {
  if (val) localContent.value = sanitizeRichText(val.content || '')
  requestAnimationFrame(() => {
    if (editorRef.value && editorRef.value.innerHTML !== localContent.value) {
      editorRef.value.innerHTML = localContent.value
    }
  })
}, { immediate: true, deep: true })

// XSS 防护
const safeHtml = computed(() => sanitizeRichText(localContent.value))

// 内容大小
const contentSize = computed(() => {
  const bytes = new Blob([localContent.value]).size
  if (bytes < 1024) return `${bytes}B`
  return `${(bytes / 1024).toFixed(1)}KB`
})

function emitChange() {
  const sanitizedContent = sanitizeRichText(localContent.value)
  if (sanitizedContent !== localContent.value) {
    localContent.value = sanitizedContent
  }
  if (editorRef.value && editorRef.value.innerHTML !== sanitizedContent) {
    editorRef.value.innerHTML = sanitizedContent
  }
  // 50KB 限制检查
  const bytes = new Blob([sanitizedContent]).size
  if (bytes > 50 * 1024) {
    ElMessage.warning('富文本内容超过50KB限制，请精简内容')
    return
  }
  emit('update:modelValue', { content: sanitizedContent })
}

function syncLocalContent() {
  const sanitizedContent = sanitizeRichText(editorRef.value?.innerHTML || '')
  localContent.value = sanitizedContent
  if (editorRef.value && editorRef.value.innerHTML !== sanitizedContent) {
    editorRef.value.innerHTML = sanitizedContent
  }
}

function applyCommand(command: RichTextFormatCommand, value?: string) {
  editorRef.value?.focus()
  applyRichTextCommand(command, value)
  syncLocalContent()
  emitChange()
}

async function insertImage() {
  try {
    const { value } = await ElMessageBox.prompt('请输入图片 URL', '插入图片', {
      confirmButtonText: '插入',
      cancelButtonText: '取消',
      inputPlaceholder: 'https://...',
    })
    applyCommand('image', value)
  } catch {}
}

async function insertLink() {
  try {
    const { value } = await ElMessageBox.prompt('请输入链接地址', '插入链接', {
      confirmButtonText: '插入',
      cancelButtonText: '取消',
      inputPlaceholder: 'https://...',
    })
    applyCommand('link', value)
  } catch {}
}
</script>

<style lang="scss" scoped>
.rich-text-editor-wrap {
  width: 100%;
}

.rich-toolbar {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-bottom: 0;
  border-radius: 4px 4px 0 0;
  background: #fafafa;
}

.rich-editable {
  min-height: 180px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 0 0 4px 4px;
  outline: none;
  line-height: 1.7;

  :deep(img) {
    max-width: 100%;
    height: auto;
  }
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
