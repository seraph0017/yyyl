/**
 * CMS 动态页面渲染引擎 — 类型定义
 * 所有组件的 props 均严格类型化
 */

/** CMS 链接配置 */
export interface CmsLink {
  /** 链接类型 */
  type: 'page' | 'product' | 'category' | 'activity' | 'h5' | 'miniprogram' | 'none'
  /** 跳转目标：页面路径 / 商品ID / 分类ID / page_code / URL / appId */
  target: string
  /** 链接标题（用于展示和调试） */
  title?: string
  /** 小程序跳转附加路径（仅 type=miniprogram） */
  path?: string
}

/** 组件通用样式 */
export interface CmsComponentStyle {
  margin_top?: number
  margin_bottom?: number
  padding_top?: number
  padding_bottom?: number
  padding_left?: number
  padding_right?: number
  background?: string
  border_radius?: number
}

/** Banner 轮播图 props */
export interface CmsBannerProps {
  images: Array<{
    url: string
    link: CmsLink
  }>
  /** 轮播间隔（秒），默认 5 */
  interval?: number
  /** 指示器样式：dot / number / none */
  indicator_style?: 'dot' | 'number' | 'none'
}

/** 图片区块 props */
export interface CmsImageProps {
  images: Array<{
    url: string
    link: CmsLink
  }>
  /** 布局模式 */
  layout: 'single' | 'two-column' | 'three-column' | 'four-grid'
}

/** 图文卡片 props */
export interface CmsImageTextProps {
  image: string
  title: string
  subtitle?: string
  description?: string
  link: CmsLink
  /** 布局方向 */
  layout?: 'horizontal' | 'vertical'
}

/** 公告栏 props */
export interface CmsNoticeProps {
  notices: Array<{
    text: string
    link?: CmsLink
  }>
  /** 滚动速度（px/s），默认 50 */
  speed?: number
  /** 背景色，默认使用主题 accent-bg */
  background_color?: string
  /** 左侧图标 URL 或 emoji */
  icon?: string
}

/** 快捷导航 props */
export interface CmsNavProps {
  columns: 3 | 4 | 5
  items: Array<{
    icon: string
    name: string
    link: CmsLink
  }>
}

/** 商品列表 props */
export interface CmsProductListProps {
  /** 商品来源 */
  source: 'manual' | 'category' | 'tag'
  /** 手动选择的商品 ID 列表 */
  product_ids?: number[]
  /** 按分类筛选（category_key） */
  category_key?: string
  /** 按标签筛选 */
  tag?: string
  /** 展示数量，默认 6 */
  count?: number
  /** 布局模式 */
  layout?: 'list' | 'grid'
}

/** 优惠券区块 props */
export interface CmsCouponProps {
  coupon_ids: number[]
  /** 布局样式 */
  layout?: 'horizontal' | 'vertical'
}

/** 富文本 props */
export interface CmsRichTextProps {
  /** HTML 内容（已经过后端 nh3 sanitize） */
  content: string
}

/** 间距 props */
export interface CmsSpacerProps {
  /** 高度（rpx） */
  height: number
}

/** 分割线 props */
export interface CmsDividerProps {
  /** 线型 */
  line_style: 'solid' | 'dashed'
  /** 线颜色 */
  color?: string
  /** 左右边距（rpx） */
  margin_horizontal?: number
}

/** 视频区块 props */
export interface CmsVideoProps {
  /** 视频 URL */
  url: string
  /** 封面图 */
  poster?: string
  /** 自动播放 */
  autoplay?: boolean
  /** 循环播放 */
  loop?: boolean
}

/** 组件类型枚举 */
export type CmsComponentType =
  | 'banner'
  | 'image'
  | 'image_text'
  | 'notice'
  | 'nav'
  | 'product_list'
  | 'coupon'
  | 'rich_text'
  | 'spacer'
  | 'divider'
  | 'video'

/** 组件类型 → Props 类型映射 */
export interface CmsPropsMap {
  banner: CmsBannerProps
  image: CmsImageProps
  image_text: CmsImageTextProps
  notice: CmsNoticeProps
  nav: CmsNavProps
  product_list: CmsProductListProps
  coupon: CmsCouponProps
  rich_text: CmsRichTextProps
  spacer: CmsSpacerProps
  divider: CmsDividerProps
  video: CmsVideoProps
}

/** 单个组件配置 */
export interface CmsComponentConfig<T extends CmsComponentType = CmsComponentType> {
  id: string
  type: T
  props: CmsPropsMap[T]
  style?: CmsComponentStyle
}

/** 页面设置 */
export interface CmsPageSettings {
  background_color?: string
  title_bar_color?: string
  title_bar_text_color?: string
}

/** 页面配置 JSON（对应后端 draft_config / version config） */
export interface CmsPageConfig {
  version: number
  page_settings: CmsPageSettings
  components: CmsComponentConfig[]
}

/** C端页面配置 API 响应 data */
export interface CmsPageResponse {
  page_code: string
  title: string
  /** 版本号，用于与本地缓存对比 */
  version: number
  config: CmsPageConfig
  updated_at: string
}

/** 本地缓存结构 */
export interface CmsPageCache {
  version: number
  config: CmsPageConfig
  title: string
  cached_at: number
}
