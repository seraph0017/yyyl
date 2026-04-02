<template>
  <el-form label-width="80px" size="small">
    <!-- 轮播图片列表 -->
    <el-form-item label="图片列表">
      <draggable
        v-model="localImages"
        item-key="url"
        handle=".img-drag-handle"
        class="banner-image-list"
        @change="onImagesChange"
      >
        <template #item="{ element, index }">
          <div class="banner-image-item">
            <div class="img-drag-handle">⠿</div>
            <div class="img-preview" @click="openAssetLibrary(index)">
              <img v-if="element.url" :src="element.url" />
              <el-icon v-else :size="24"><Plus /></el-icon>
            </div>
            <div class="img-actions">
              <div class="link-display" @click="openLinkPicker(index)">
                <template v-if="element.link && element.link.type !== 'none'">
                  <el-tag size="small" type="success">{{ linkTypeLabel(element.link.type) }}</el-tag>
                  <span class="link-text">{{ element.link.title || element.link.target || '已设置' }}</span>
                </template>
                <span v-else class="link-placeholder">
                  <el-icon><Link /></el-icon>设置链接
                </span>
              </div>
              <el-button link type="danger" size="small" @click="removeImage(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </template>
      </draggable>
      <el-button type="primary" link @click="addImage">
        <el-icon><Plus /></el-icon>添加图片
      </el-button>
    </el-form-item>

    <!-- 轮播间隔 -->
    <el-form-item label="轮播间隔">
      <el-input-number v-model="localProps.interval" :min="1" :max="30" :step="1" />
      <span class="unit-text">秒</span>
    </el-form-item>

    <!-- 指示器样式 -->
    <el-form-item label="指示器">
      <el-radio-group v-model="localProps.indicator_style" @change="emitChange">
        <el-radio-button value="dot">圆点</el-radio-button>
        <el-radio-button value="number">数字</el-radio-button>
        <el-radio-button value="none">无</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <!-- 自动播放 -->
    <el-form-item label="自动播放">
      <el-switch v-model="localProps.autoplay" @change="emitChange" />
    </el-form-item>

    <!-- 圆角 -->
    <el-form-item label="圆角">
      <el-slider v-model="localProps.border_radius" :min="0" :max="30" @change="emitChange" />
    </el-form-item>

    <!-- 素材库弹窗 -->
    <AssetLibrary
      v-model:visible="assetVisible"
      file-type="image"
      @select="onAssetSelect"
    />

    <!-- 链接选择器弹窗 -->
    <LinkPicker
      v-model="currentLink"
      v-model:visible="linkVisible"
      @update:modelValue="onLinkChange"
    />
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import draggable from 'vuedraggable'
import { Plus, Delete, Link } from '@element-plus/icons-vue'
import type { BannerPropsConfig, LinkConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'
import LinkPicker from '../LinkPicker.vue'

const props = defineProps<{
  modelValue: BannerPropsConfig
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: BannerPropsConfig): void
}>()

const localProps = reactive<BannerPropsConfig>({
  images: [],
  interval: 5,
  indicator_style: 'dot',
  autoplay: true,
  border_radius: 0,
})

const localImages = ref<BannerPropsConfig['images']>([])

// 同步 props
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      Object.assign(localProps, val)
      localImages.value = [...(val.images || [])]
    }
  },
  { immediate: true, deep: true }
)

function emitChange() {
  emit('update:modelValue', { ...localProps, images: [...localImages.value] })
}

// ---- 图片管理 ----
function addImage() {
  localImages.value.push({
    url: '',
    link: { type: 'none', target: '', title: '' },
  })
  emitChange()
}

function removeImage(index: number) {
  localImages.value.splice(index, 1)
  emitChange()
}

function onImagesChange() {
  emitChange()
}

// ---- 素材库 ----
const assetVisible = ref(false)
const editingImageIndex = ref(-1)

function openAssetLibrary(index: number) {
  editingImageIndex.value = index
  assetVisible.value = true
}

function onAssetSelect(assets: CmsAsset[]) {
  if (assets.length > 0 && editingImageIndex.value >= 0) {
    localImages.value[editingImageIndex.value].url = assets[0].file_url
    emitChange()
  }
  assetVisible.value = false
}

// ---- 链接选择器 ----
const linkVisible = ref(false)
const editingLinkIndex = ref(-1)
const currentLink = ref<LinkConfig>({ type: 'none', target: '', title: '' })

function openLinkPicker(index: number) {
  editingLinkIndex.value = index
  currentLink.value = { ...(localImages.value[index].link || { type: 'none', target: '', title: '' }) }
  linkVisible.value = true
}

function onLinkChange(link: LinkConfig) {
  if (editingLinkIndex.value >= 0) {
    localImages.value[editingLinkIndex.value].link = { ...link }
    emitChange()
  }
}

const linkTypeMap: Record<string, string> = {
  product: '商品', page: '页面', category: '分类',
  activity: '活动页', h5: 'H5链接', miniprogram: '小程序', none: '无',
}

function linkTypeLabel(type: string) {
  return linkTypeMap[type] || type
}
</script>

<style lang="scss" scoped>
.banner-image-list {
  width: 100%;
}

.banner-image-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.img-drag-handle {
  cursor: grab;
  color: #909399;
  font-size: 14px;
}

.img-preview {
  width: 60px;
  height: 40px;
  border-radius: 4px;
  border: 1px dashed #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
  background: #fff;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .el-icon {
    color: #c0c4cc;
  }
}

.img-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.link-display {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 12px;

  &:hover {
    background: var(--el-fill-color-lighter, #f0f2f5);
  }
}

.link-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-text-color-regular);
}

.link-placeholder {
  display: flex;
  align-items: center;
  gap: 2px;
  color: var(--el-color-primary);
}

.unit-text {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
