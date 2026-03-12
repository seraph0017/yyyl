import { get } from '@/utils/request'
import type { RealtimeData, TrendData, SalesRankingItem, MemberStats, HeatmapItem, FinanceSummary, CategoryRevenue } from '@/types'

export function getRealtimeData() {
  return get<{ data: RealtimeData }>('/admin/dashboard/realtime')
}

export function getTrends(params?: { days?: number }) {
  return get<{ data: TrendData }>('/admin/dashboard/trends', params)
}

export function getSalesRanking(params?: { sort_by?: 'sales_count' | 'sales_amount' }) {
  return get<{ data: SalesRankingItem[] }>('/admin/dashboard/sales-ranking', params)
}

export function getMemberStats() {
  return get<{ data: MemberStats }>('/admin/dashboard/member-stats')
}

export function getHeatmap(params?: { start_date?: string; end_date?: string }) {
  return get<{ data: HeatmapItem[] }>('/admin/dashboard/heatmap', params)
}

export function getFinanceSummary() {
  return get<{ data: FinanceSummary }>('/admin/dashboard/finance-summary')
}

export function getCategoryRevenue() {
  return get<{ data: CategoryRevenue[] }>('/admin/dashboard/category-revenue')
}
