/**
 * 营地配置中心
 * 根据构建时环境变量 VITE_SITE_CODE 决定当前营地的品牌信息、主题色等
 */

export interface SiteConfig {
  /** 营地ID (对应后端 site_id) */
  id: number
  /** 营地代号 */
  code: string
  /** 营地全称 */
  name: string
  /** 品牌名（简称） */
  brandName: string
  /** Slogan */
  slogan: string
  /** 分享标题 */
  shareTitle: string
  /** 分享兜底标题 */
  shareDefaultTitle: string
  /** Logo Emoji（占位用） */
  logoEmoji: string
  /** 主题色 */
  primaryColor: string
  primaryLight: string
  primaryLighter: string
  primaryBg: string
  /** 背景色 */
  bgColor: string
  /** 头部渐变起始色 */
  headerGradientStart: string
  headerGradientEnd: string
  /** 联系电话 */
  phone: string
  /** 地址 */
  address: string
  /** 经纬度 */
  location: { lat: number; lng: number }
}

const SITES: Record<string, SiteConfig> = {
  xijiao: {
    id: 1,
    code: 'xijiao',
    name: '一月一露·西郊林场',
    brandName: '一月一露',
    slogan: '享受户外生活',
    shareTitle: '一月一露·西郊林场 享受户外生活',
    shareDefaultTitle: '一月一露露营',
    logoEmoji: '🏕️',
    primaryColor: '#2d4a3e',
    primaryLight: '#3d6b5a',
    primaryLighter: '#6b9b8a',
    primaryBg: 'rgba(45, 74, 62, 0.06)',
    bgColor: '#faf6f0',
    headerGradientStart: '#2d4a3e',
    headerGradientEnd: '#3d6b5a',
    phone: '',
    address: '',
    location: { lat: 31.2, lng: 121.3 },
  },
  dalonggu: {
    id: 2,
    code: 'dalonggu',
    name: '一月一露·大聋谷',
    brandName: '一月一露',
    slogan: '仰望星空',
    shareTitle: '一月一露·大聋谷 仰望星空',
    shareDefaultTitle: '一月一露露营',
    logoEmoji: '⛺',
    primaryColor: '#2a3d52',
    primaryLight: '#4a7a9a',
    primaryLighter: '#7ab0c8',
    primaryBg: 'rgba(42, 61, 82, 0.06)',
    bgColor: '#f5f2ee',
    headerGradientStart: '#2a3d52',
    headerGradientEnd: '#4a7a9a',
    phone: '',
    address: '',
    location: { lat: 30.2, lng: 120.1 },
  },
}

/** 当前营地配置（构建时确定） */
const siteCode = import.meta.env.VITE_SITE_CODE || 'xijiao'
export const currentSite: SiteConfig = SITES[siteCode] || SITES.xijiao

/** 导出便捷别名，兼容原 brandConfig 用法 */
export const brandConfig = {
  name: currentSite.brandName,
  slogan: currentSite.slogan,
  shareTitle: currentSite.shareTitle,
  shareDefaultTitle: currentSite.shareDefaultTitle,
  logoEmoji: currentSite.logoEmoji,
}

export default currentSite
