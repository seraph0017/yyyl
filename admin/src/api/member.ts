import { get, post, put } from '@/utils/request'
import type {
  MemberInfo, MemberSearchParams, AnnualCardConfig, TimesCardConfig,
  TimesConsumptionRule, ActivationCode, PointsExchangeConfig, PaginatedResponse
} from '@/types'

// 会员
export function getMembers(params: MemberSearchParams) {
  return get<{ data: PaginatedResponse<MemberInfo> }>('/admin/members', params)
}

export function getMemberDetail(userId: number) {
  return get<{ data: MemberInfo }>(`/admin/members/${userId}`)
}

export function adjustPoints(userId: number, data: { points: number; reason: string }) {
  return post(`/admin/members/${userId}/points-adjust`, data)
}

// 年卡配置
export function getAnnualCardConfigs() {
  return get<{ data: AnnualCardConfig[] }>('/admin/annual-card-configs')
}

export function createAnnualCardConfig(data: Partial<AnnualCardConfig>) {
  return post('/admin/annual-card-configs', data)
}

export function updateAnnualCardConfig(id: number, data: Partial<AnnualCardConfig>) {
  return put(`/admin/annual-card-configs/${id}`, data)
}

export function getAnnualCards(params?: { page?: number; page_size?: number; status?: string }) {
  return get<{ data: PaginatedResponse<any> }>('/admin/annual-cards', params)
}

// 积分兑换
export function getPointsExchangeConfigs() {
  return get<{ data: PointsExchangeConfig[] }>('/admin/points-exchange-configs')
}

export function createPointsExchangeConfig(data: Partial<PointsExchangeConfig>) {
  return post('/admin/points-exchange-configs', data)
}

export function updatePointsExchangeConfig(id: number, data: Partial<PointsExchangeConfig>) {
  return put(`/admin/points-exchange-configs/${id}`, data)
}

// 次数卡
export function getTimesCardConfigs() {
  return get<{ data: TimesCardConfig[] }>('/admin/times-card-configs')
}

export function createTimesCardConfig(data: Partial<TimesCardConfig>) {
  return post('/admin/times-card-configs', data)
}

export function updateTimesCardConfig(id: number, data: Partial<TimesCardConfig>) {
  return put(`/admin/times-card-configs/${id}`, data)
}

export function getConsumptionRules(configId: number) {
  return get<{ data: TimesConsumptionRule[] }>(`/admin/times-card-configs/${configId}/consumption-rules`)
}

export function updateConsumptionRules(configId: number, data: { rules: Partial<TimesConsumptionRule>[] }) {
  return post(`/admin/times-card-configs/${configId}/consumption-rules`, data)
}

// 激活码
export function generateActivationCodes(data: { config_id: number; count: number; batch_no?: string }) {
  return post('/admin/activation-codes/generate', data)
}

export function getActivationCodes(params?: { page?: number; page_size?: number; batch_no?: string; status?: string }) {
  return get<{ data: PaginatedResponse<ActivationCode> }>('/admin/activation-codes', params)
}

export function exportActivationCodes(params?: { batch_no?: string; status?: string }) {
  return post('/admin/activation-codes/export', params, { responseType: 'blob' })
}

export function getTimesCards(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<any> }>('/admin/times-cards', params)
}

export function adjustTimesCard(cardId: number, data: { adjust_times: number; reason: string }) {
  return put(`/admin/times-cards/${cardId}/adjust`, data)
}
