<template>
  <view class="page-index">
    <!-- CMS 动态渲染模式 -->
    <template v-if="renderMode === 'cms'">
      <!-- 保留原有品牌头部（搜索框等不由 CMS 控制的固定元素） -->
      <view class="hero-header">
        <view class="hero-header__bg" />
        <view class="hero-header__content">
          <view class="hero-header__top">
            <view class="hero-header__brand">
              <text class="hero-header__logo">{{ site.logoEmoji }}</text>
              <view class="hero-header__title">
                <text class="hero-header__name">{{ site.brandName }}</text>
                <text class="hero-header__slogan">{{ site.slogan }}</text>
              </view>
            </view>
          </view>
          <!-- 搜索框 -->
          <view class="search-bar" @tap="onSearchTap">
            <text class="search-bar__icon">🔍</text>
            <text class="search-bar__text">搜索营位、活动、装备...</text>
          </view>
        </view>
      </view>

      <!-- CMS 渲染引擎 -->
      <CmsRenderer :config="pageConfig" />
    </template>

    <!-- 内置默认首页（L3 降级） -->
    <template v-else-if="renderMode === 'default'">
      <!-- 品牌头部 -->
      <view class="hero-header">
        <view class="hero-header__bg" />
        <view class="hero-header__content">
          <view class="hero-header__top">
            <view class="hero-header__brand">
              <text class="hero-header__logo">{{ site.logoEmoji }}</text>
              <view class="hero-header__title">
                <text class="hero-header__name">{{ site.brandName }}</text>
                <text class="hero-header__slogan">{{ site.slogan }}</text>
              </view>
            </view>
          </view>
          <view class="search-bar" @tap="onSearchTap">
            <text class="search-bar__icon">🔍</text>
            <text class="search-bar__text">搜索营位、活动、装备...</text>
          </view>
        </view>
      </view>

      <DefaultHomePage ref="defaultHomeRef" />
    </template>

    <!-- 加载骨架屏 -->
    <template v-else>
      <view class="hero-header">
        <view class="hero-header__bg" />
        <view class="hero-header__content">
          <view class="hero-header__top">
            <view class="hero-header__brand">
              <text class="hero-header__logo">{{ site.logoEmoji }}</text>
              <view class="hero-header__title">
                <text class="hero-header__name">{{ site.brandName }}</text>
                <text class="hero-header__slogan">{{ site.slogan }}</text>
              </view>
            </view>
          </view>
          <view class="search-bar">
            <text class="search-bar__icon">🔍</text>
            <text class="search-bar__text">搜索营位、活动、装备...</text>
          </view>
        </view>
      </view>
      <HomePageSkeleton />
    </template>

    <view class="safe-bottom" style="height: 40rpx" />
  </view>
</template>

<script setup lang="ts">
/**
 * 首页 — CMS 动态渲染 + 三级降级
 * L1: CMS API 配置 → 动态渲染最新内容
 * L2: 本地缓存 → 渲染上次缓存的内容
 * L3: 内置默认首页 → 硬编码版本保证基本可用
 */
import { ref, onMounted } from 'vue'
import { onLoad, onPullDownRefresh, onShareAppMessage } from '@dcloudio/uni-app'
import CmsRenderer from '@/components/cms/CmsRenderer.vue'
import DefaultHomePage from '@/components/default-home-page/index.vue'
import HomePageSkeleton from './components/HomePageSkeleton.vue'
import { getCmsPage, checkCmsPageVersion } from '@/api/cms'
import { getCmsPageCache, setCmsPageCache } from '@/api/cms'
import type { CmsPageConfig } from '@/types/cms'
import { currentSite } from '@/config/sites'

const site = currentSite

type RenderMode = 'loading' | 'cms' | 'default'

const renderMode = ref<RenderMode>('loading')
const pageConfig = ref<CmsPageConfig | null>(null)
const previewToken = ref<string | undefined>(undefined)
const cachedVersion = ref<number>(0)
const defaultHomeRef = ref<InstanceType<typeof DefaultHomePage> | null>(null)

onLoad((options) => {
  previewToken.value = options?.preview_token
})

onMounted(() => {
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
  const PAGE_CODE = 'home'

  // 预览模式 — 直接请求，不走缓存
  if (previewToken.value) {
    try {
      const data = await getCmsPage(PAGE_CODE, previewToken.value)
      pageConfig.value = data.config
      renderMode.value = 'cms'
      applyNavigationBarColor(data.config)
    } catch {
      console.warn('[首页] 预览模式加载失败，降级到默认首页')
      renderMode.value = 'default'
    }
    return
  }

  // 1. 尝试读取本地缓存
  const cache = getCmsPageCache(PAGE_CODE)
  if (cache) {
    pageConfig.value = cache.config
    cachedVersion.value = cache.version
    renderMode.value = 'cms'
    // 应用缓存中的导航栏颜色
    applyNavigationBarColor(cache.config)
  }

  // 2. 静默刷新 — 有缓存时先调用轻量 check 接口判断是否有更新，无缓存时直接拉取完整配置
  try {
    if (cache) {
      // 有缓存：先用 check 接口判断版本，避免每次传输完整配置 JSON
      const checkResult = await checkCmsPageVersion(PAGE_CODE, cachedVersion.value)
      if (!checkResult.has_update) {
        // 版本未变化，跳过完整请求
        return
      }
    }
    // 有更新或无缓存：请求完整配置
    const data = await getCmsPage(PAGE_CODE)
    pageConfig.value = data.config
    renderMode.value = 'cms'
    setCmsPageCache(PAGE_CODE, data)
    cachedVersion.value = data.version
    // 动态更新导航栏标题
    if (data.title) {
      uni.setNavigationBarTitle({ title: data.title })
    }
    // 应用导航栏颜色设置
    applyNavigationBarColor(data.config)
  } catch (err) {
    console.warn('[首页] CMS 配置加载失败:', err)
    // 无缓存时降级到默认首页
    if (!cache) {
      renderMode.value = 'default'
    }
    // 有缓存时保持缓存渲染（已在上方设置）
  }
}

function onSearchTap() {
  uni.navigateTo({ url: '/pages/category/index?search=1' })
}

onPullDownRefresh(async () => {
  if (renderMode.value === 'default' && defaultHomeRef.value) {
    await defaultHomeRef.value.refresh()
  } else {
    await loadPageConfig()
  }
  uni.stopPullDownRefresh()
})

onShareAppMessage(() => ({
  title: site.shareTitle,
  path: '/pages/index/index',
}))
</script>

<style lang="scss" scoped>
.page-index {
  min-height: 100vh;
  background-color: var(--color-bg);
}

/* ========== 沉浸式品牌头部 ========== */
.hero-header {
  position: relative;
  padding: 0 0 32rpx;
  overflow: hidden;

  &__bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 380rpx;
    background: linear-gradient(
      165deg,
      var(--color-primary-dark) 0%,
      var(--color-primary) 35%,
      var(--color-primary-light) 70%,
      var(--color-bg) 100%
    );

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      background:
        radial-gradient(ellipse 80% 50% at 70% 20%, rgba(200, 168, 114, 0.12) 0%, transparent 60%),
        radial-gradient(circle at 15% 90%, rgba(255, 255, 255, 0.06) 0%, transparent 40%);
    }
  }

  &__content {
    position: relative;
    z-index: 1;
    padding: 24rpx 36rpx;
    padding-top: calc(env(safe-area-inset-top, 0px) + 20rpx);
  }

  &__top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28rpx;
  }

  &__brand {
    display: flex;
    align-items: center;
  }

  &__logo {
    font-size: 56rpx;
    margin-right: 16rpx;
    filter: drop-shadow(0 2rpx 4rpx rgba(0, 0, 0, 0.2));
  }

  &__title {
    display: flex;
    flex-direction: column;
  }

  &__name {
    font-size: var(--font-size-xxl);
    font-weight: 800;
    color: var(--color-text-white);
    letter-spacing: 6rpx;
    text-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.15);
  }

  &__slogan {
    font-size: var(--font-size-xs);
    color: rgba(255, 254, 250, 0.7);
    margin-top: 4rpx;
    letter-spacing: 3rpx;
    font-weight: 300;
  }
}

/* ========== 搜索框 — 磨砂玻璃 ========== */
.search-bar {
  display: flex;
  align-items: center;
  height: 76rpx;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 1rpx solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-round);
  padding: 0 28rpx;
  transition: var(--transition-base);

  &:active {
    background: rgba(255, 255, 255, 0.25);
  }

  &__icon {
    font-size: 28rpx;
    margin-right: 12rpx;
    opacity: 0.9;
  }

  &__text {
    font-size: var(--font-size-sm);
    color: rgba(255, 255, 255, 0.6);
    letter-spacing: 1rpx;
  }
}
</style>
