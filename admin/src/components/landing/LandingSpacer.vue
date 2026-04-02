<template>
  <div class="landing-spacer" :style="{ height: (height || 20) + 'px' }" />
</template>

<script setup lang="ts">
defineProps<{
  height?: number
}>()
</script>

<style lang="scss" scoped>
.landing-spacer {
  width: 100%;
}
</style>
