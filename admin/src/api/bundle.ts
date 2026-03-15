// 搭配组合管理 API
import { get, post, put, del } from '@/utils/request'
import type { BundleConfig, BundleConfigCreate, BundleStats } from '@/types'

/** 搭配组合列表（分页） */
export function getBundleConfigs(params: object) {
  return get<{ code: number; data: { list: BundleConfig[]; pagination: { total: number } } }>('/admin/bundle-configs', params)
}

/** 创建搭配组合 */
export function createBundleConfig(data: BundleConfigCreate) {
  return post<{ code: number; data: BundleConfig }>('/admin/bundle-configs', data)
}

/** 更新搭配组合 */
export function updateBundleConfig(id: number, data: Partial<BundleConfigCreate>) {
  return put<{ code: number; data: BundleConfig }>(`/admin/bundle-configs/${id}`, data)
}

/** 删除搭配组合 */
export function deleteBundleConfig(id: number) {
  return del(`/admin/bundle-configs/${id}`)
}

/** 搭配统计 */
export function getBundleStats(params?: object) {
  return get<{ code: number; data: BundleStats }>('/admin/reports/bundle-stats', params)
}
