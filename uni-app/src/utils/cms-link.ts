/**
 * CMS 超链接跳转工具
 * 统一处理 7 种链接类型的跳转逻辑
 */
import type { CmsLink } from '@/types/cms'

/** tabBar 页面路径列表（switchTab 判断） */
const TAB_BAR_PAGES = [
  '/pages/index/index',
  '/pages/category/index',
  '/pages/cart/index',
  '/pages/order/index',
  '/pages/mine/index',
]

/**
 * 判断路径是否为 tabBar 页面
 */
function isTabBarPage(path: string): boolean {
  const cleanPath = path.split('?')[0]
  return TAB_BAR_PAGES.includes(cleanPath)
}

/**
 * 处理 CMS 链接跳转
 * @param link CMS 链接配置对象
 */
export function handleCmsLink(link: CmsLink): void {
  if (!link || link.type === 'none' || !link.target) {
    return
  }

  switch (link.type) {
    case 'page':
      handlePageLink(link.target)
      break

    case 'product':
      handleProductLink(link.target)
      break

    case 'category':
      handleCategoryLink(link.target)
      break

    case 'activity':
      handleActivityLink(link.target)
      break

    case 'h5':
      handleH5Link(link.target)
      break

    case 'miniprogram':
      handleMiniprogramLink(link.target, link.path)
      break

    default:
      console.warn(`[cms-link] 未知链接类型: ${link.type}`)
  }
}

/**
 * page — 小程序内部页面跳转
 * target 为完整页面路径，如 "/pages/product-detail/index?id=123"
 *
 * 判断逻辑：
 * - 如果是 tabBar 页面 → switchTab（switchTab 不支持带参数，自动去掉 query）
 * - 否则 → navigateTo
 * - navigateTo 失败（页面栈满10层）→ 降级 redirectTo
 */
function handlePageLink(target: string): void {
  if (isTabBarPage(target)) {
    uni.switchTab({ url: target.split('?')[0] })
  } else {
    uni.navigateTo({
      url: target,
      fail: () => {
        // 页面栈满时降级为 redirectTo
        uni.redirectTo({ url: target })
      },
    })
  }
}

/**
 * product — 商品详情页
 * target 为商品 ID，自动拼接详情页路径
 */
function handleProductLink(target: string): void {
  const url = `/pages/product-detail/index?id=${target}`
  uni.navigateTo({
    url,
    fail: () => {
      uni.redirectTo({ url })
    },
  })
}

/**
 * category — 商品分类页
 * target 为分类 key（如 "daily_camping"），跳转到分类页并传递筛选参数
 *
 * 注意：分类页 `/pages/category/index` 是 tabBar 页面，
 *       switchTab 不支持传参，需通过全局事件总线传递 category_key
 */
function handleCategoryLink(target: string): void {
  // 通过全局事件总线传递分类参数
  uni.$emit('cms:category-switch', { category_key: target })
  uni.switchTab({ url: '/pages/category/index' })
}

/**
 * activity — CMS 装修活动页
 * target 为 page_code，跳转到 CMS 通用页面容器
 */
function handleActivityLink(target: string): void {
  const url = `/pages/cms-page/index?page_code=${target}`
  uni.navigateTo({
    url,
    fail: () => {
      uni.redirectTo({ url })
    },
  })
}

/**
 * h5 — 外部 H5 链接
 * target 为完整 URL，通过 web-view 打开
 *
 * 注意：
 * - 微信小程序 web-view 要求域名在小程序后台配置业务域名白名单
 * - 复用 game-webview 页面，通过 title 参数动态设置导航栏标题
 */
function handleH5Link(target: string): void {
  // 校验 URL 格式
  if (!target.startsWith('http://') && !target.startsWith('https://')) {
    console.warn(`[cms-link] 无效的 H5 链接: ${target}`)
    uni.showToast({ title: '链接无效', icon: 'none' })
    return
  }

  // 复用 game-webview 页面，通过 title 参数动态设置导航栏标题
  // 后续如需更语义化可新增 pages-sub/common/webview/index 通用 webview 页面
  const url = `/pages-sub/product/game-webview/index?url=${encodeURIComponent(target)}&title=${encodeURIComponent('详情')}`
  uni.navigateTo({
    url,
    fail: () => {
      uni.redirectTo({ url })
    },
  })
}

/**
 * miniprogram — 其他小程序跳转
 * target 为目标小程序 appId，path 为小程序内路径
 *
 * 注意：微信小程序需在 app.json 或后台配置 navigateToMiniProgramAppIdList
 */
function handleMiniprogramLink(appId: string, path?: string): void {
  // #ifdef MP-WEIXIN
  ;(uni as any).navigateToMiniProgram({
    appId,
    path: path || '',
    fail: () => {
      uni.showToast({ title: '跳转失败，请稍后重试', icon: 'none' })
    },
  })
  // #endif

  // #ifdef H5
  uni.showToast({ title: '请在微信小程序中打开', icon: 'none' })
  // #endif
}
