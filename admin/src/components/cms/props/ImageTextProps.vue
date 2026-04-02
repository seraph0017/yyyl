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
      <div class="link-display" @click="linkVisible = true">
        <template v-if="localProps.link && localProps.link.type !== 'none'">
          <el-tag size="small" type="success">{{ linkTypeLabel(localProps.link.type) }}</el-tag>
          <span class="link-display__text">{{ localProps.link.title || localProps.link.target || '已设置' }}</span>
          <el-button link type="danger" size="small" @click.stop="clearLink">
            <el-icon><Close /></el-icon>
          </el-button>
        </template>
        <el-button v-else link type="primary">
          <el-icon><Link /></el-icon>设置链接
        </el-button>
      </div>
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
import { Plus, Link, Close } from '@element-plus/icons-vue'
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

const linkTypeMap: Record<string, string> = {
  product: '商品', page: '页面', category: '分类',
  activity: '活动页', h5: 'H5链接', miniprogram: '小程序', none: '无',
}

function linkTypeLabel(type: string) {
  return linkTypeMap[type] || type
}

function clearLink() {
  localProps.link = { type: 'none', target: '', title: '' }
  emitChange()
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

.link-display {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;

  &:hover {
    background: var(--el-fill-color-lighter, #f5f7fa);
  }

  &__text {
    flex: 1;
    font-size: 12px;
    color: var(--el-text-color-regular);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
