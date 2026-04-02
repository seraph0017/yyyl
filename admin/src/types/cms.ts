/** CMS 链接配置 */
export interface LinkConfig {
  type: 'page' | 'product' | 'category' | 'activity' | 'h5' | 'miniprogram' | 'none'
  target: string       // 链接目标（商品ID / URL / 页面路径等）
  title: string        // 链接显示名称
}

/** CMS 组件实例 */
export interface ComponentItem {
  id: string           // 组件唯一ID（UUID）
  type: string         // 组件类型标识
  props: Record<string, any>  // 组件属性
  style: {
    margin_top: number
    margin_bottom: number
    border_radius?: number
    background?: string
  }
}

/** CMS 页面配置JSON */
export interface CmsConfig {
  version: number
  page_settings: {
    background_color: string
    title_bar_color: string
    title_bar_text_color: string
  }
  components: ComponentItem[]
}

/** CMS 页面 */
export interface CmsPage {
  id: number
  site_id: number
  page_code: string
  page_type: 'home' | 'activity' | 'promotion' | 'custom' | 'landing'
  title: string
  description?: string
  status: 'active' | 'inactive'
  current_version_id?: number
  draft_config?: CmsConfig
  draft_updated_at?: string
  sort_order: number
  created_at: string
  updated_at: string
}

/** CMS 页面版本 */
export interface CmsPageVersion {
  id: number
  version_number: number
  config: CmsConfig            // 版本配置JSON快照
  published_by: number
  published_at: string
  remark?: string
  is_current: boolean
}

/** CMS 组件定义（注册表） */
export interface CmsComponentDef {
  id: number
  component_type: string
  name: string
  icon?: string
  default_config?: Record<string, any>
  status: string
  sort_order: number
}

/** CMS 素材 */
export interface CmsAsset {
  id: number
  file_name: string
  file_url: string
  file_type: 'image' | 'video'
  file_size: number
  width?: number
  height?: number
  uploaded_by: number
  created_at: string
}

/** 编辑锁信息 */
export interface LockInfo {
  admin_id: number
  admin_name: string
  locked_at: string
}

/** 预览信息 */
export interface PreviewInfo {
  preview_token: string
  preview_url: string
  expires_at: string
}

/** 组件面板分组 */
export interface ComponentGroup {
  label: string
  components: {
    type: string
    name: string
    icon: string
    defaultProps: Record<string, any>
  }[]
}

/** ====== 各组件 Props 类型定义 ====== */

/** 轮播图组件属性 */
export interface BannerPropsConfig {
  images: Array<{
    url: string          // 图片地址
    link: LinkConfig     // 点击链接配置
  }>
  interval: number       // 轮播间隔（秒），默认 5
  indicator_style: 'dot' | 'number' | 'none'  // 指示器样式
  autoplay: boolean      // 是否自动播放，默认 true
  border_radius: number  // 圆角，默认 0
}

/** 图片组件属性 */
export interface ImagePropsConfig {
  url: string            // 图片地址
  link: LinkConfig       // 点击链接配置
  mode: 'aspectFill' | 'aspectFit' | 'widthFix'  // 图片裁剪模式
  width: string          // 宽度，默认 '100%'
  height?: string        // 高度，不设则自适应
}

/** 图文卡片组件属性 */
export interface ImageTextPropsConfig {
  layout: 'left-right' | 'right-left' | 'top-bottom'  // 排版方向
  image_url: string      // 图片地址
  title: string          // 标题文字
  description: string    // 描述文字
  link: LinkConfig       // 点击链接配置
  title_color: string    // 标题颜色，默认 '#333333'
  desc_color: string     // 描述颜色，默认 '#999999'
}

/** 快捷导航组件属性 */
export interface NavPropsConfig {
  items: Array<{
    icon: string         // 图标图片地址
    label: string        // 导航文字
    link: LinkConfig     // 点击链接配置
  }>
  columns: 4 | 5        // 每行列数，默认 4
  show_label: boolean    // 是否显示文字，默认 true
}

/** 公告栏组件属性 */
export interface NoticePropsConfig {
  texts: string[]         // 公告文字列表
  speed: number           // 滚动速度（px/s），默认 50
  background_color: string // 背景色，默认 '#FFF9E6'
  text_color: string      // 文字颜色，默认 '#FF6600'
  icon: string            // 左侧图标URL，可选
}

/** 商品列表组件属性 */
export interface ProductListPropsConfig {
  source: 'manual' | 'category' | 'tag'  // 商品来源
  product_ids?: number[]   // 手动选择的商品ID列表
  category_id?: number     // 按分类筛选
  tag?: string             // 按标签筛选
  count: number            // 展示数量，默认 6
  layout: 'list' | 'grid'  // 布局模式
  columns: 2 | 3           // 网格列数（仅 grid 模式），默认 2
}

/** 优惠券组件属性 */
export interface CouponPropsConfig {
  coupon_ids: number[]     // 优惠券ID列表
  layout: 'horizontal' | 'vertical'  // 布局样式，默认 'horizontal'
}

/** 富文本组件属性 */
export interface RichTextPropsConfig {
  content: string          // HTML 内容（后端 nh3 sanitize，前端 DOMPurify 渲染）
}

/** 间距组件属性 */
export interface SpacerPropsConfig {
  height: number           // 高度（px），默认 20，范围 1-200
}

/** 分割线组件属性 */
export interface DividerPropsConfig {
  style: 'solid' | 'dashed'  // 线条样式
  color: string              // 颜色，默认 '#EEEEEE'
  margin: number             // 左右边距（px），默认 16
}

/** 视频组件属性 */
export interface VideoPropsConfig {
  url: string              // 视频地址
  poster: string           // 封面图
  autoplay: boolean        // 自动播放，默认 false
  loop: boolean            // 循环播放，默认 false
}
