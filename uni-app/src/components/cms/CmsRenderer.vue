<template>
  <view
    class="cms-renderer"
    :style="{ backgroundColor: config?.page_settings?.background_color || '' }"
  >
    <template v-for="comp in validComponents" :key="comp.id">
      <view
        class="cms-component-wrapper"
        :style="buildWrapperStyle(comp.style)"
      >
        <!-- uni-app 不支持 <component :is>，使用 v-if 条件渲染 -->
        <!-- data 使用 as any 因为 v-if 已确保类型匹配，但 TS 无法推断 -->
        <CmsBanner v-if="comp.type === 'banner'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsImage v-else-if="comp.type === 'image'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsImageText v-else-if="comp.type === 'image_text'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsNotice v-else-if="comp.type === 'notice'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsNav v-else-if="comp.type === 'nav'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsProductList v-else-if="comp.type === 'product_list'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsCoupon v-else-if="comp.type === 'coupon'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsRichText v-else-if="comp.type === 'rich_text'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
        <CmsSpacer v-else-if="comp.type === 'spacer'" :data="(comp.props as any)" :component-style="comp.style" />
        <CmsDivider v-else-if="comp.type === 'divider'" :data="(comp.props as any)" :component-style="comp.style" />
        <CmsVideo v-else-if="comp.type === 'video'" :data="(comp.props as any)" :component-style="comp.style" @link-tap="onLinkTap" />
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
/**
 * CMS 渲染引擎主组件
 * 1. 接收 CmsPageConfig 配置 JSON
 * 2. 应用 page_settings（背景色等）
 * 3. 遍历 components 数组，通过 v-if 条件渲染对应组件
 * 4. 为每个组件传递 props 和 style
 * 5. 遇到未知组件类型时静默跳过（console.warn 记录）
 * 6. 单个组件渲染异常时不影响其他组件
 *
 * 注：uni-app 小程序不支持 <component :is> 动态组件，因此使用 v-if 链
 */
import { computed, onErrorCaptured } from 'vue'
import type { CmsPageConfig, CmsComponentStyle, CmsLink } from '@/types/cms'
import { handleCmsLink } from '@/utils/cms-link'
import { registeredTypes } from './registry'
import CmsBanner from './CmsBanner.vue'
import CmsImage from './CmsImage.vue'
import CmsImageText from './CmsImageText.vue'
import CmsNotice from './CmsNotice.vue'
import CmsNav from './CmsNav.vue'
import CmsProductList from './CmsProductList.vue'
import CmsCoupon from './CmsCoupon.vue'
import CmsRichText from './CmsRichText.vue'
import CmsSpacer from './CmsSpacer.vue'
import CmsDivider from './CmsDivider.vue'
import CmsVideo from './CmsVideo.vue'

interface Props {
  config: CmsPageConfig | null
}

const props = defineProps<Props>()

/**
 * 组件级错误边界
 * 捕获子组件渲染异常，防止单个组件错误导致整个 CmsRenderer 白屏
 * 返回 false 阻止错误继续向上冒泡
 */
onErrorCaptured((err, instance, info) => {
  console.warn(`[CmsRenderer] 组件渲染异常:`, {
    error: err,
    component: instance?.$options?.name || '未知组件',
    info,
  })
  // 返回 false 阻止错误向上传播，保证其他组件正常渲染
  return false
})

/** 过滤掉未知组件类型，保证只渲染已注册的组件 */
const validComponents = computed(() => {
  if (!props.config?.components) return []
  return props.config.components.filter((comp) => {
    if (registeredTypes.includes(comp.type)) return true
    console.warn(`[CmsRenderer] 未知组件类型: ${comp.type}，已跳过`)
    return false
  })
})

/** 构建组件外层容器样式 */
function buildWrapperStyle(style?: CmsComponentStyle): Record<string, string> {
  if (!style) return {}
  const result: Record<string, string> = {}
  if (style.margin_top != null) result.marginTop = `${style.margin_top}rpx`
  if (style.margin_bottom != null) result.marginBottom = `${style.margin_bottom}rpx`
  if (style.padding_top != null) result.paddingTop = `${style.padding_top}rpx`
  if (style.padding_bottom != null) result.paddingBottom = `${style.padding_bottom}rpx`
  if (style.padding_left != null) result.paddingLeft = `${style.padding_left}rpx`
  if (style.padding_right != null) result.paddingRight = `${style.padding_right}rpx`
  if (style.background) result.background = style.background
  if (style.border_radius != null) result.borderRadius = `${style.border_radius}rpx`
  return result
}

/** 统一处理组件内的链接点击 */
function onLinkTap(link: CmsLink) {
  handleCmsLink(link)
}
</script>

<style lang="scss" scoped>
.cms-renderer {
  min-height: 100vh;
  width: 100%;
}

.cms-component-wrapper {
  width: 100%;
  overflow: hidden;
}
</style>
