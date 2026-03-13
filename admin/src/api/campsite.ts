import { get, post, put, patch, del as httpDel } from '@/utils/request'
import type {
  CampsiteListResponse,
  CampsiteDetail,
  CampsiteCreateRequest,
  CampsiteSearchParams,
  CampsitePricingRule,
  CampsiteStatsOverview,
  CampsiteInventoryItem,
} from '@/types/campsite'

// 营位CRUD
export function getCampsites(params: CampsiteSearchParams) {
  return get<{ data: CampsiteListResponse }>('/admin/campsites/', params)
}

export function getCampsiteDetail(id: number) {
  return get<{ data: CampsiteDetail }>(`/admin/campsites/${id}`)
}

export function createCampsite(data: CampsiteCreateRequest) {
  return post<{ data: { id: number; name: string } }>('/admin/campsites/', data)
}

export function updateCampsite(id: number, data: Partial<CampsiteCreateRequest>) {
  return put<{ data: { id: number; name: string } }>(`/admin/campsites/${id}`, data)
}

export function deleteCampsite(id: number) {
  return httpDel(`/admin/campsites/${id}`)
}

export function updateCampsiteStatus(id: number, status: string) {
  return patch(`/admin/campsites/${id}/status`, { status })
}

// 库存管理
export function getCampsiteInventory(id: number, params: { date_start: string; date_end: string }) {
  return get<{ data: CampsiteInventoryItem[] }>(`/admin/campsites/${id}/inventory`, params)
}

export function batchOpenCampsiteInventory(id: number, data: { start_date: string; end_date: string; total_stock: number }) {
  return post<{ data: { created_count: number } }>(`/admin/campsites/${id}/inventory/batch`, data)
}

// 定价规则
export function getCampsitePricingRules(id: number) {
  return get<{ data: CampsitePricingRule[] }>(`/admin/campsites/${id}/pricing-rules`)
}

export function createCampsitePricingRule(id: number, data: Partial<CampsitePricingRule>) {
  return post(`/admin/campsites/${id}/pricing-rules`, data)
}

export function updateCampsitePricingRule(id: number, ruleId: number, data: Partial<CampsitePricingRule>) {
  return put(`/admin/campsites/${id}/pricing-rules/${ruleId}`, data)
}

export function deleteCampsitePricingRule(id: number, ruleId: number) {
  return httpDel(`/admin/campsites/${id}/pricing-rules/${ruleId}`)
}

// 统计概览
export function getCampsiteStats() {
  return get<{ data: CampsiteStatsOverview }>('/admin/campsites/stats/overview')
}
