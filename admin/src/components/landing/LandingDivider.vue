<template>
  <div
    class="landing-divider"
    :style="{
      margin: `0 ${(margin || 16)}px`,
      borderTopStyle: dividerStyle,
      borderTopColor: color || '#EEEEEE',
    }"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  style?: 'solid' | 'dashed'
  color?: string
  margin?: number
}>()

const dividerStyle = computed(() => props.style || 'solid')
</script>

<style lang="scss" scoped>
.landing-divider {
  border-top-width: 1px;
}
</style>
