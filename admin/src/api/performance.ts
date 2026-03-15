// 绩效管理 API
import { get, post, put } from '@/utils/request'
import type { PerformanceConfig, PerformanceRecord, PerformanceRanking } from '@/types'

export function getPerformanceConfigs() {
  return get<{ code: number; data: PerformanceConfig[] }>('/admin/performance/configs')
}

export function updatePerformanceConfigs(data: { configs: Partial<PerformanceConfig>[] }) {
  return put('/admin/performance/configs', data)
}

export function getPerformanceRecords(params: object) {
  return get<{ code: number; data: { list: PerformanceRecord[]; pagination: { total: number } } }>('/admin/performance/records', params)
}

export function getPerformanceRanking(params: object) {
  return get<{ code: number; data: PerformanceRanking[] }>('/admin/performance/ranking', params)
}

export function triggerCalculation(data: { period_type: string; period_start: string; period_end: string }) {
  return post('/admin/performance/calculate', data)
}

export function exportPerformance(params: object) {
  return post('/admin/performance/export', params)
}
