/**
 * CMS 页面配置 API 接口封装
 * 包含页面配置获取、版本检查、本地缓存管理
 */

import { get } from '@/utils/request'
import { getStorage, setStorage, removeStorage } from '@/utils/storage'
import type { CmsPageResponse, CmsPageCache } from '@/types/cms'

/** 缓存 key 前缀 */
const CMS_PAGE_CACHE_PREFIX = 'cms_page_config:'
/** 缓存过期时间（秒） — 10分钟 */
const CMS_CACHE_EXPIRE_SECONDS = 600

/**
 * 获取已发布的页面配置（C端公开接口）
 * 无需登录认证（needAuth: false）
 */
export function getCmsPage(pageCode: string, previewToken?: string) {
  return get<CmsPageResponse>(
    `/cms/pages/${pageCode}`,
    previewToken ? { preview_token: previewToken } : undefined,
    { needAuth: false, showError: false },
  )
}

/**
 * 检查页面版本是否有更新
 */
export function checkCmsPageVersion(pageCode: string, currentVersion: number) {
  return get<{ has_update: boolean; version: number }>(
    `/cms/pages/${pageCode}/check`,
    { version: currentVersion },
    { needAuth: false, showError: false },
  )
}

/**
 * 读取页面缓存
 */
export function getCmsPageCache(pageCode: string): CmsPageCache | null {
  return getStorage<CmsPageCache>(`${CMS_PAGE_CACHE_PREFIX}${pageCode}`)
}

/**
 * 写入页面缓存
 */
export function setCmsPageCache(pageCode: string, data: CmsPageResponse): void {
  const cache: CmsPageCache = {
    version: data.version,
    config: data.config,
    title: data.title,
    cached_at: Date.now(),
  }
  setStorage(`${CMS_PAGE_CACHE_PREFIX}${pageCode}`, cache, CMS_CACHE_EXPIRE_SECONDS)
}

/**
 * 清除指定页面缓存
 */
export function removeCmsPageCache(pageCode: string): void {
  removeStorage(`${CMS_PAGE_CACHE_PREFIX}${pageCode}`)
}
