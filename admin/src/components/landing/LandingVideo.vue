<template>
  <div class="landing-video">
    <video
      v-if="url"
      :src="url"
      :poster="poster"
      :autoplay="autoplay"
      :loop="loop"
      controls
      class="video-player"
    />
    <div v-else class="video-placeholder">
      <el-icon :size="32"><VideoCamera /></el-icon>
      <span>视频（请选择视频）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoCamera } from '@element-plus/icons-vue'

defineProps<{
  url?: string
  poster?: string
  autoplay?: boolean
  loop?: boolean
}>()
</script>

<style lang="scss" scoped>
.landing-video {
  width: 100%;
  padding: 0 16px;
  box-sizing: border-box;
}

.video-player {
  width: 100%;
  border-radius: 8px;
  background: #000;
}

.video-placeholder {
  width: 100%;
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #f0f2f5;
  border-radius: 8px;
  color: #909399;
  font-size: 14px;
}
</style>
