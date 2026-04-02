<template>
  <view class="cms-page">
    <!-- 加载中 -->
    <view v-if="loading" class="cms-page__loading">
      <view class="cms-page__skeleton" v-for="i in 5" :key="i">
        <view class="skeleton-block" :style="{ height: (i % 2 === 0 ? 200 : 300) + 'rpx' }" />
      </view>
    </view>

    <!-- CMS 渲染 -->
    <CmsRenderer v-else-if="pageConfig" :config="pageConfig" />

    <!-- 加载失败 -->
    <view v-else class="cms-page__error">
      <view class="cms-page__error-icon">
        <text>📄</text>
      </view>
      <text class="cms-page__error-title">页面加载失败</text>
      <text class="cms-page__error-desc">请检查网络后重试</text>
      <view class="cms-page__retry" @tap="loadPageConfig">
        <text>点击重试</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 通用页面容器
 * 通过 page_code 参数加载任意 CMS 配置页面（活动页、促销页等）
 * 支持预览模式（preview_token 参数）
 */
import { ref } from 'vue'
import { onLoad, onPullDownRefresh, onShareAppMessage } from '@dcloudio/uni-app'
import CmsRenderer from '@/components/cms/CmsRenderer.vue'
import { getCmsPage, checkCmsPageVersion } from '@/api/cms'
import { getCmsPageCache, setCmsPageCache } from '@/api/cms'
import type { CmsPageConfig } from '@/types/cms'
import { currentSite } from '@/config/sites'

const pageCode = ref('')
const pageTitle = ref('')
const previewToken = ref<string | undefined>(undefined)
const pageConfig = ref<CmsPageConfig | null>(null)
const loading = ref(true)
const cachedVersion = ref<number>(0)

onLoad((options) => {
  pageCode.value = options?.page_code || ''
  previewToken.value = options?.preview_token

  if (!pageCode.value) {
    loading.value = false
    return
  }

  loadPageConfig()
})

/** 应用 page_settings 中的导航栏颜色配置 */
function applyNavigationBarColor(config: CmsPageConfig | null) {
  const settings = config?.page_settings
  if (settings?.title_bar_color) {
    uni.setNavigationBarColor({
      frontColor: settings.title_bar_text_color === '#000000' ? '#000000' : '#ffffff',
      backgroundColor: settings.title_bar_color,
      animation: { duration: 300, timingFunc: 'easeIn' },
    })
  }
}

async function loadPageConfig() {
  loading.value = true

  // 预览模式
  if (previewToken.value) {
    try {
      const data = await getCmsPage(pageCode.value, previewToken.value)
      pageConfig.value = data.config
      if (data.title) {
        pageTitle.value = data.title
        uni.setNavigationBarTitle({ title: data.title })
      }
      applyNavigationBarColor(data.config)
    } catch {
      pageConfig.value = null
    }
    loading.value = false
    return
  }

  // 先尝试缓存
  const cache = getCmsPageCache(pageCode.value)
  if (cache) {
    pageConfig.value = cache.config
    cachedVersion.value = cache.version
    if (cache.title) {
      pageTitle.value = cache.title
      uni.setNavigationBarTitle({ title: cache.title })
    }
    applyNavigationBarColor(cache.config)
    loading.value = false
  }

  // 静默刷新 — 有缓存时先调用轻量 check 接口，无缓存时直接拉取完整配置
  try {
    if (cache) {
      const checkResult = await checkCmsPageVersion(pageCode.value, cachedVersion.value)
      if (!checkResult.has_update) {
        // 版本未变化，跳过完整请求
        return
      }
    }
    // 有更新或无缓存：请求完整配置
    const data = await getCmsPage(pageCode.value)
    pageConfig.value = data.config
    cachedVersion.value = data.version
    setCmsPageCache(pageCode.value, data)
    if (data.title) {
      pageTitle.value = data.title
      uni.setNavigationBarTitle({ title: data.title })
    }
    applyNavigationBarColor(data.config)
  } catch (err) {
    console.warn(`[CmsPage] 页面 ${pageCode.value} 加载失败:`, err)
    if (!cache) {
      pageConfig.value = null
    }
  }
  loading.value = false
}

onPullDownRefresh(async () => {
  await loadPageConfig()
  uni.stopPullDownRefresh()
})

// CMS 通用页面分享支持
onShareAppMessage(() => ({
  title: pageTitle.value || currentSite.shareTitle,
  path: `/pages/cms-page/index?page_code=${pageCode.value}`,
}))
</script>

<style lang="scss" scoped>
.cms-page {
  min-height: 100vh;
  background-color: var(--color-bg);

  &__loading {
    padding: var(--spacing-lg);
  }

  &__skeleton .skeleton-block {
    background: linear-gradient(110deg, var(--color-bg-light) 0%, var(--color-bg-warm) 50%, var(--color-bg-light) 100%);
    background-size: 300% 100%;
    animation: shimmer 2s infinite;
    border-radius: var(--radius-lg);
    margin-bottom: var(--spacing-md);
  }

  &__error {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 200rpx;
  }

  &__error-icon {
    font-size: 80rpx;
    margin-bottom: 24rpx;
  }

  &__error-title {
    font-size: var(--font-size-lg);
    color: var(--color-text);
    font-weight: 600;
    margin-bottom: 12rpx;
  }

  &__error-desc {
    font-size: var(--font-size-sm);
    color: var(--color-text-placeholder);
  }

  &__retry {
    margin-top: 32rpx;
    padding: 16rpx 48rpx;
    background: var(--color-primary);
    border-radius: var(--radius-round);
    color: var(--color-text-white);
    font-size: var(--font-size-base);

    &:active {
      opacity: 0.85;
    }
  }
}

@keyframes shimmer {
  0% { background-position: 300% 0; }
  100% { background-position: -300% 0; }
}
</style>
