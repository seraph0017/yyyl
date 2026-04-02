<template>
  <div class="landing-renderer" :style="{ backgroundColor: config.page_settings.background_color }">
    <template v-for="comp in config.components" :key="comp.id">
      <component
        v-if="getLandingComponent(comp.type)"
        :is="getLandingComponent(comp.type)"
        v-bind="comp.props"
        :style="{
          marginTop: comp.style.margin_top + 'px',
          marginBottom: comp.style.margin_bottom + 'px',
        }"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import type { CmsConfig } from '@/types/cms'
import LandingBanner from './LandingBanner.vue'
import LandingImage from './LandingImage.vue'
import LandingImageText from './LandingImageText.vue'
import LandingRichText from './LandingRichText.vue'
import LandingVideo from './LandingVideo.vue'
import LandingNav from './LandingNav.vue'
import LandingSpacer from './LandingSpacer.vue'
import LandingDivider from './LandingDivider.vue'

defineProps<{
  config: CmsConfig
}>()

const componentMap: Record<string, any> = {
  banner: LandingBanner,
  image: LandingImage,
  image_text: LandingImageText,
  rich_text: LandingRichText,
  video: LandingVideo,
  nav: LandingNav,
  spacer: LandingSpacer,
  divider: LandingDivider,
}

function getLandingComponent(type: string) {
  return componentMap[type] || null
}
</script>

<style lang="scss" scoped>
.landing-renderer {
  width: 100%;
  min-height: 200px;
}
</style>
