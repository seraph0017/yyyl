// 营地地图管理 API
import { get, post, put, del } from '@/utils/request'
import type { CampMap, CampMapCreate, CampMapZoneCreate } from '@/types'

/** 地图列表（分页） */
export function getCampMaps(params?: object) {
  return get<{ code: number; data: { list: CampMap[]; pagination: { total: number } } }>('/admin/camp-maps', params)
}

/** 创建地图 */
export function createCampMap(data: CampMapCreate) {
  return post<{ code: number; data: CampMap }>('/admin/camp-maps', data)
}

/** 更新地图 */
export function updateCampMap(id: number, data: Partial<CampMapCreate>) {
  return put<{ code: number; data: CampMap }>(`/admin/camp-maps/${id}`, data)
}

/** 删除地图 */
export function deleteCampMap(id: number) {
  return del(`/admin/camp-maps/${id}`)
}

/** 创建区域 */
export function createCampMapZone(mapId: number, data: CampMapZoneCreate) {
  return post(`/admin/camp-maps/${mapId}/zones`, data)
}

/** 更新区域 */
export function updateCampMapZone(zoneId: number, data: Partial<CampMapZoneCreate>) {
  return put(`/admin/camp-maps/zones/${zoneId}`, data)
}

/** 删除区域 */
export function deleteCampMapZone(zoneId: number) {
  return del(`/admin/camp-maps/zones/${zoneId}`)
}
