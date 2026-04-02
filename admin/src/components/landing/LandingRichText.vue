<template>
  <div class="landing-rich-text" v-html="safeHtml" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'

const props = defineProps<{
  content?: string
}>()

// XSS 防护
const safeHtml = computed(() => DOMPurify.sanitize(props.content || ''))
</script>

<style lang="scss" scoped>
.landing-rich-text {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  word-break: break-word;

  :deep(img) {
    max-width: 100%;
    height: auto;
  }

  :deep(a) {
    color: var(--color-primary, #2d4a3e);
    text-decoration: underline;
  }

  :deep(h1, h2, h3, h4) {
    margin: 0.8em 0 0.4em;
  }

  :deep(p) {
    margin: 0.4em 0;
  }
}
</style>
