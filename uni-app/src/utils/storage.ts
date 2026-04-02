/**
 * 本地存储工具封装
 * - 类型安全的存取
 * - 过期时间支持
 * - 错误处理
 */

interface StorageItem<T> {
  value: T
  expireAt: number | null
}

/**
 * 设置存储（支持过期时间）
 */
export function setStorage<T>(key: string, value: T, expireSeconds?: number): void {
  const item: StorageItem<T> = {
    value,
    expireAt: expireSeconds ? Date.now() + expireSeconds * 1000 : null,
  }

  try {
    uni.setStorageSync(key, JSON.stringify(item))
  } catch (e) {
    console.error(`[Storage] Set "${key}" failed:`, e)
  }
}

/**
 * 获取存储
 */
export function getStorage<T>(key: string, defaultValue: T | null = null): T | null {
  try {
    const raw = uni.getStorageSync(key)
    if (!raw) return defaultValue

    const item: StorageItem<T> = JSON.parse(raw)

    if (item.expireAt && Date.now() > item.expireAt) {
      uni.removeStorageSync(key)
      return defaultValue
    }

    return item.value
  } catch {
    try {
      const raw = uni.getStorageSync(key)
      return (raw as T) || defaultValue
    } catch {
      return defaultValue
    }
  }
}

/**
 * 移除存储
 */
export function removeStorage(key: string): void {
  try {
    uni.removeStorageSync(key)
  } catch (e) {
    console.error(`[Storage] Remove "${key}" failed:`, e)
  }
}

/**
 * 清除所有存储
 */
export function clearStorage(): void {
  try {
    uni.clearStorageSync()
  } catch (e) {
    console.error('[Storage] Clear failed:', e)
  }
}

/**
 * 存储键常量
 */
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_INFO: 'user_info',
  SEARCH_HISTORY: 'search_history',
  CART_BADGE: 'cart_badge_count',
  LAST_LOCATION: 'last_location',
  CMS_PAGE_PREFIX: 'cms_page_config:',
} as const
