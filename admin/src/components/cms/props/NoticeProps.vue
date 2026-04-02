<template>
  <el-form label-width="80px" size="small">
    <!-- 公告文字列表 -->
    <el-form-item label="公告内容">
      <div class="notice-texts">
        <div v-for="(text, index) in localTexts" :key="index" class="notice-text-item">
          <el-input v-model="localTexts[index]" placeholder="输入公告内容" @blur="emitChange" />
          <el-button :icon="Delete" link type="danger" @click="removeText(index)" />
        </div>
        <el-button type="primary" link @click="addText">
          <el-icon><Plus /></el-icon>添加公告
        </el-button>
      </div>
    </el-form-item>

    <!-- 滚动速度 -->
    <el-form-item label="滚动速度">
      <el-slider v-model="localProps.speed" :min="10" :max="200" :step="10" @change="emitChange" />
      <span class="unit-text">{{ localProps.speed }} px/s</span>
    </el-form-item>

    <!-- 背景色 -->
    <el-form-item label="背景色">
      <el-color-picker v-model="localProps.background_color" @change="emitChange" />
    </el-form-item>

    <!-- 文字颜色 -->
    <el-form-item label="文字颜色">
      <el-color-picker v-model="localProps.text_color" @change="emitChange" />
    </el-form-item>

    <!-- 图标 -->
    <el-form-item label="左侧图标">
      <div class="icon-picker" @click="assetVisible = true">
        <img v-if="localProps.icon" :src="localProps.icon" class="icon-preview" />
        <span v-else class="icon-placeholder">选择图标</span>
      </div>
      <el-button v-if="localProps.icon" link type="danger" size="small" @click="localProps.icon = ''; emitChange()">
        清除
      </el-button>
    </el-form-item>

    <AssetLibrary v-model:visible="assetVisible" file-type="image" @select="onAssetSelect" />
  </el-form>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'
import type { NoticePropsConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'

const props = defineProps<{ modelValue: NoticePropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: NoticePropsConfig): void }>()

const localProps = reactive<NoticePropsConfig>({
  texts: [''],
  speed: 50,
  background_color: '#FFF9E6',
  text_color: '#FF6600',
  icon: '',
})

const localTexts = ref<string[]>([''])
const assetVisible = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    Object.assign(localProps, val)
    localTexts.value = [...(val.texts || [''])]
  }
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps, texts: [...localTexts.value] })
}

function addText() {
  localTexts.value.push('')
  emitChange()
}

function removeText(index: number) {
  localTexts.value.splice(index, 1)
  if (localTexts.value.length === 0) localTexts.value.push('')
  emitChange()
}

function onAssetSelect(assets: CmsAsset[]) {
  if (assets.length > 0) {
    localProps.icon = assets[0].file_url
    emitChange()
  }
  assetVisible.value = false
}
</script>

<style lang="scss" scoped>
.notice-texts {
  width: 100%;
}

.notice-text-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.unit-text {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.icon-picker {
  width: 40px;
  height: 40px;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;

  &:hover { border-color: var(--color-primary); }
}

.icon-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.icon-placeholder {
  font-size: 10px;
  color: #c0c4cc;
}
</style>
