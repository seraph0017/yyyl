/**
 * CMS 组件注册表
 * type → Vue Component 的映射
 * 新增组件类型时在此处注册即可
 *
 * 不使用动态 import()，因为小程序不支持动态导入
 * 所有组件在构建时静态注册
 */
import type { Component } from 'vue'
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

export const componentRegistry: Record<string, Component> = {
  banner: CmsBanner,
  image: CmsImage,
  image_text: CmsImageText,
  notice: CmsNotice,
  nav: CmsNav,
  product_list: CmsProductList,
  coupon: CmsCoupon,
  rich_text: CmsRichText,
  spacer: CmsSpacer,
  divider: CmsDivider,
  video: CmsVideo,
}

/** 已注册的组件类型列表（用于校验） */
export const registeredTypes = Object.keys(componentRegistry)
