<template>
  <el-form label-width="80px" size="small">
    <!-- 视频选择 -->
    <el-form-item label="视频">
      <div class="video-picker" @click="videoAssetVisible = true">
        <template v-if="localProps.url">
          <video :src="localProps.url" class="video-preview" />
          <div class="video-overlay">点击更换</div>
        </template>
        <div v-else class="video-placeholder">
          <el-icon :size="24"><VideoCamera /></el-icon>
          <span>选择视频</span>
        </div>
      </div>
    </el-form-item>

    <!-- 封面图 -->
    <el-form-item label="封面图">
      <div class="image-picker-small" @click="posterAssetVisible = true">
        <img v-if="localProps.poster" :src="localProps.poster" />
        <el-icon v-else><Plus /></el-icon>
      </div>
      <el-button v-if="localProps.poster" link type="danger" size="small" @click="localProps.poster = ''; emitChange()">
        清除
      </el-button>
    </el-form-item>

    <!-- 自动播放 -->
    <el-form-item label="自动播放">
      <el-switch v-model="localProps.autoplay" @change="emitChange" />
    </el-form-item>

    <!-- 循环播放 -->
    <el-form-item label="循环播放">
      <el-switch v-model="localProps.loop" @change="emitChange" />
    </el-form-item>

    <AssetLibrary v-model:visible="videoAssetVisible" file-type="video" @select="onVideoSelect" />
    <AssetLibrary v-model:visible="posterAssetVisible" file-type="image" @select="onPosterSelect" />
  </el-form>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { VideoCamera, Plus } from '@element-plus/icons-vue'
import type { VideoPropsConfig, CmsAsset } from '@/types/cms'
import AssetLibrary from '../AssetLibrary.vue'

const props = defineProps<{ modelValue: VideoPropsConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: VideoPropsConfig): void }>()

const localProps = reactive<VideoPropsConfig>({
  url: '',
  poster: '',
  autoplay: false,
  loop: false,
})

const videoAssetVisible = ref(false)
const posterAssetVisible = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) Object.assign(localProps, val)
}, { immediate: true, deep: true })

function emitChange() {
  emit('update:modelValue', { ...localProps })
}

function onVideoSelect(assets: CmsAsset[]) {
  if (assets.length > 0) {
    localProps.url = assets[0].file_url
    emitChange()
  }
  videoAssetVisible.value = false
}

function onPosterSelect(assets: CmsAsset[]) {
  if (assets.length > 0) {
    localProps.poster = assets[0].file_url
    emitChange()
  }
  posterAssetVisible.value = false
}
</script>

<style lang="scss" scoped>
.video-picker {
  width: 100%;
  height: 120px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  background: #fafafa;

  &:hover { border-color: var(--color-primary); }
}

.video-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px;
  background: rgba(0,0,0,0.5);
  color: #fff;
  font-size: 12px;
  text-align: center;
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #c0c4cc;
  font-size: 12px;
}

.image-picker-small {
  width: 60px;
  height: 40px;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #fafafa;

  &:hover { border-color: var(--color-primary); }

  img { width: 100%; height: 100%; object-fit: cover; }
  .el-icon { color: #c0c4cc; }
}
</style>
