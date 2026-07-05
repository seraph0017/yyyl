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

    <el-form-item label="图片热区">
      <div class="hotspot-editor">
        <div class="form-tip">在图片上拖拽圈选区域，再为该区域设置链接；热区优先于整图链接。</div>
        <div
          ref="hotspotCanvasRef"
          class="hotspot-canvas"
          @mousedown="handleHotspotMouseDown"
          @mousemove="handleHotspotMouseMove"
          @mouseup="handleHotspotMouseUp"
          @mouseleave="handleHotspotMouseUp"
        >
          <img v-if="localProps.url" :src="localProps.url" class="hotspot-canvas__image" draggable="false" />
          <div v-else class="hotspot-canvas__placeholder">请先选择图片</div>
          <button
            v-for="(hotspot, index) in localProps.hotspots"
            :key="index"
            type="button"
            class="hotspot-box"
            :style="hotspotStyle(hotspot)"
            @click.stop="editHotspot(hotspot)"
          >
            {{ hotspot.title || hotspot.link?.title || `热区${index + 1}` }}
          </button>
          <div v-if="draftHotspot" class="hotspot-box hotspot-box--draft" :style="hotspotStyle(draftHotspot)"></div>
        </div>
        <div class="hotspot-list" v-if="localProps.hotspots.length">
          <div v-for="(hotspot, index) in localProps.hotspots" :key="index" class="hotspot-list__item">
            <span>{{ hotspot.title || hotspot.link?.title || `热区${index + 1}` }}</span>
            <el-button link type="primary" @click="editHotspot(hotspot)">设置链接</el-button>
            <el-button link type="danger" @click="removeHotspot(index)">删除</el-button>
          </div>
        </div>
      </div>
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
    <LinkPicker
      v-if="activeHotspot"
      v-model="activeHotspot.link"
      v-model:visible="hotspotLinkVisible"
      @update:modelValue="emitHotspotLinkChange"
    />
  </el-form>
</template>

<script setup lang="ts">
import { reactive, watch, ref } from 'vue'
import { Plus, Link, Close } from '@element-plus/icons-vue'
import type { ImageHotspotConfig, ImagePropsConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'
import LinkPicker from '../LinkPicker.vue'

const props = defineProps<{ modelValue: ImagePropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: ImagePropsConfig): void }>()

const localProps = reactive<ImagePropsConfig>({
  url: '',
  link: { type: 'none', target: '', title: '' },
  hotspots: [],
  mode: 'widthFix',
  width: '100%',
  height: undefined,
})

const assetVisible = ref(false)
const linkVisible = ref(false)
const hotspotLinkVisible = ref(false)
const hotspotCanvasRef = ref<HTMLElement>()
const activeHotspot = ref<ImageHotspotConfig | null>(null)
const draftHotspot = ref<ImageHotspotConfig | null>(null)
const dragStart = ref<{ x: number; y: number } | null>(null)

watch(() => props.modelValue, (val) => {
  if (val) Object.assign(localProps, { ...val, hotspots: val.hotspots || [] })
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}

function onAssetSelect(assets: CmsAsset[]) {
  const asset = assets[0]
  if (asset) {
    localProps.url = asset.file_url
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

function getCanvasPoint(event: MouseEvent) {
  const rect = hotspotCanvasRef.value?.getBoundingClientRect()
  if (!rect || rect.width <= 0 || rect.height <= 0) return null
  const x = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100))
  const y = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100))
  return { x, y }
}

function handleHotspotMouseDown(event: MouseEvent) {
  if (!localProps.url) return
  const point = getCanvasPoint(event)
  if (!point) return
  dragStart.value = point
  draftHotspot.value = {
    x: point.x,
    y: point.y,
    width: 0,
    height: 0,
    title: '',
    link: { type: 'none', target: '', title: '' },
  }
}

function handleHotspotMouseMove(event: MouseEvent) {
  if (!dragStart.value || !draftHotspot.value) return
  const point = getCanvasPoint(event)
  if (!point) return
  const x = Math.min(dragStart.value.x, point.x)
  const y = Math.min(dragStart.value.y, point.y)
  draftHotspot.value = {
    ...draftHotspot.value,
    x,
    y,
    width: Math.abs(point.x - dragStart.value.x),
    height: Math.abs(point.y - dragStart.value.y),
  }
}

function handleHotspotMouseUp() {
  if (!dragStart.value || !draftHotspot.value) return
  const hotspot = draftHotspot.value
  dragStart.value = null
  draftHotspot.value = null
  if (hotspot.width < 2 || hotspot.height < 2) return
  localProps.hotspots.push({
    ...hotspot,
    width: Number(hotspot.width.toFixed(2)),
    height: Number(hotspot.height.toFixed(2)),
    x: Number(hotspot.x.toFixed(2)),
    y: Number(hotspot.y.toFixed(2)),
  })
  const created = localProps.hotspots[localProps.hotspots.length - 1]
  if (created) {
    activeHotspot.value = created
    hotspotLinkVisible.value = true
  }
  emitChange()
}

function hotspotStyle(hotspot: ImageHotspotConfig) {
  return {
    left: `${hotspot.x}%`,
    top: `${hotspot.y}%`,
    width: `${hotspot.width}%`,
    height: `${hotspot.height}%`,
  }
}

function editHotspot(hotspot: ImageHotspotConfig) {
  activeHotspot.value = hotspot
  hotspotLinkVisible.value = true
}

function emitHotspotLinkChange() {
  emitChange()
}

function removeHotspot(index: number) {
  localProps.hotspots.splice(index, 1)
  emitChange()
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

.form-tip {
  margin-bottom: 8px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

.hotspot-editor {
  width: 100%;
}

.hotspot-canvas {
  position: relative;
  width: 100%;
  min-height: 140px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  background: #fafafa;
  user-select: none;

  &__image {
    display: block;
    width: 100%;
    max-height: 260px;
    object-fit: contain;
    pointer-events: none;
  }

  &__placeholder {
    height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c0c4cc;
    font-size: 12px;
  }
}

.hotspot-box {
  position: absolute;
  border: 2px solid var(--color-primary, #2d4a3e);
  background: rgba(45, 74, 62, 0.18);
  color: #fff;
  font-size: 12px;
  line-height: 1.2;
  padding: 2px 4px;
  cursor: pointer;
  overflow: hidden;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);

  &--draft {
    border-style: dashed;
    pointer-events: none;
  }
}

.hotspot-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;

  &__item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;

    span {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}
</style>
