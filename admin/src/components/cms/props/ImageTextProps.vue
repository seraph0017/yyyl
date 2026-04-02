<template>
  <el-form label-width="80px" size="small">
    <!-- 排版方向 -->
    <el-form-item label="排版方向">
      <el-radio-group v-model="localProps.layout" @change="emitChange">
        <el-radio-button value="left-right">左图右文</el-radio-button>
        <el-radio-button value="right-left">右图左文</el-radio-button>
        <el-radio-button value="top-bottom">上图下文</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <!-- 图片选择 -->
    <el-form-item label="图片">
      <div class="image-picker" @click="assetVisible = true">
        <img v-if="localProps.image_url" :src="localProps.image_url" class="image-picker__preview" />
        <div v-else class="image-picker__placeholder">
          <el-icon :size="20"><Plus /></el-icon>
          <span>选择图片</span>
        </div>
      </div>
    </el-form-item>

    <!-- 标题 -->
    <el-form-item label="标题">
      <el-input v-model="localProps.title" @blur="emitChange" />
    </el-form-item>

    <!-- 描述 -->
    <el-form-item label="描述">
      <el-input v-model="localProps.description" type="textarea" :rows="2" @blur="emitChange" />
    </el-form-item>

    <!-- 链接 -->
    <el-form-item label="点击链接">
      <el-button link type="primary" @click="linkVisible = true">
        {{ localProps.link?.title || '设置链接' }}
      </el-button>
    </el-form-item>

    <!-- 标题颜色 -->
    <el-form-item label="标题颜色">
      <el-color-picker v-model="localProps.title_color" @change="emitChange" />
    </el-form-item>

    <!-- 描述颜色 -->
    <el-form-item label="描述颜色">
      <el-color-picker v-model="localProps.desc_color" @change="emitChange" />
    </el-form-item>

    <AssetLibrary v-model:visible="assetVisible" file-type="image" @select="onAssetSelect" />
    <LinkPicker v-model="localProps.link" v-model:visible="linkVisible" @update:modelValue="emitChange" />
  </el-form>
</template>

<script setup lang="ts">
import { reactive, watch, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import type { ImageTextPropsConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'
import LinkPicker from '../LinkPicker.vue'

const props = defineProps<{ modelValue: ImageTextPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: ImageTextPropsConfig): void }>()

const localProps = reactive<ImageTextPropsConfig>({
  layout: 'left-right',
  image_url: '',
  title: '',
  description: '',
  link: { type: 'none', target: '', title: '' },
  title_color: '#333333',
  desc_color: '#999999',
})

const assetVisible = ref(false)
const linkVisible = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) Object.assign(localProps, val)
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}

function onAssetSelect(assets: CmsAsset[]) {
  if (assets.length > 0) {
    localProps.image_url = assets[0].file_url
    emitChange()
  }
  assetVisible.value = false
}
</script>

<style lang="scss" scoped>
.image-picker {
  width: 100%;
  height: 80px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fafafa;

  &:hover { border-color: var(--color-primary, #2d4a3e); }

  &__preview {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  &__placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    color: #c0c4cc;
    font-size: 12px;
  }
}
</style>
