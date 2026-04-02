<template>
  <el-form label-width="80px" size="small">
    <!-- 图片选择 -->
    <el-form-item label="图片">
      <div class="image-picker" @click="assetVisible = true">
        <img v-if="localProps.url" :src="localProps.url" class="image-picker__preview" />
        <div v-else class="image-picker__placeholder">
          <el-icon :size="24"><Plus /></el-icon>
          <span>选择图片</span>
        </div>
      </div>
    </el-form-item>

    <!-- 链接选择器 -->
    <el-form-item label="点击链接">
      <el-button link type="primary" @click="linkVisible = true">
        {{ localProps.link?.title || '设置链接' }}
      </el-button>
    </el-form-item>

    <!-- 裁剪模式 -->
    <el-form-item label="裁剪模式">
      <el-select v-model="localProps.mode" @change="emitChange">
        <el-option label="填充裁剪" value="aspectFill" />
        <el-option label="等比缩放" value="aspectFit" />
        <el-option label="宽度适应" value="widthFix" />
      </el-select>
    </el-form-item>

    <!-- 宽度 -->
    <el-form-item label="宽度">
      <el-input v-model="localProps.width" placeholder="100%" @blur="emitChange" />
    </el-form-item>

    <!-- 高度 -->
    <el-form-item label="高度">
      <el-input v-model="localProps.height" placeholder="自适应" @blur="emitChange" />
    </el-form-item>

    <AssetLibrary v-model:visible="assetVisible" file-type="image" @select="onAssetSelect" />
    <LinkPicker v-model="localProps.link" v-model:visible="linkVisible" @update:modelValue="emitChange" />
  </el-form>
</template>

<script setup lang="ts">
import { reactive, watch, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import type { ImagePropsConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'
import LinkPicker from '../LinkPicker.vue'

const props = defineProps<{ modelValue: ImagePropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: ImagePropsConfig): void }>()

const localProps = reactive<ImagePropsConfig>({
  url: '',
  link: { type: 'none', target: '', title: '' },
  mode: 'widthFix',
  width: '100%',
  height: undefined,
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
    localProps.url = assets[0].file_url
    emitChange()
  }
  assetVisible.value = false
}
</script>

<style lang="scss" scoped>
.image-picker {
  width: 100%;
  height: 120px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fafafa;

  &:hover {
    border-color: var(--color-primary, #2d4a3e);
  }

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
