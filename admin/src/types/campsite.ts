// 营位管理 — TypeScript 类型定义

import type { PaginationParams } from '@/types'

// 营位类型
export type CampsiteType = 'daily_camping' | 'event_camping'

// 营位状态
export type CampsiteStatus = 'on_sale' | 'off_sale' | 'draft'

// 日照类型
export type SunExposure = 'sunny' | 'shaded' | 'mixed'

// 营位扩展属性
export interface CampsiteExtension {
  area: string | null
  position_name: string | null
  has_electricity: boolean
  has_platform: boolean
  sun_exposure: SunExposure | null
  max_persons: number | null
  event_start_date: string | null
  event_end_date: string | null
}

// 库存概况（7天汇总）
export interface CampsiteStockSummary {
  total_7d: number
  booked_7d: number
  available_7d: number
}

// 营位列表项
export interface CampsiteListItem {
  id: number
  name: string
  type: CampsiteType
  type_label: string
  status: CampsiteStatus
  base_price: string
  booking_mode: string
  sort_order: number
  images: Array<{ url: string; type?: string }>
  created_at: string | null
  updated_at: string | null
  // 营位属性
  area: string | null
  position_name: string | null
  has_electricity: boolean
  has_platform: boolean
  sun_exposure: SunExposure | null
  max_persons: number | null
  event_start_date: string | null
  event_end_date: string | null
  // 库存概况
  stock_summary: CampsiteStockSummary
}

// 营位列表响应
export interface CampsiteListResponse {
  items: CampsiteListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  areas: string[]
}

// 定价规则
export interface CampsitePricingRule {
  id: number
  rule_type: 'date_type' | 'custom_date'
  date_type: string | null
  custom_date: string | null
  price: string
  priority: number
}

// 优惠规则
export interface CampsiteDiscountRule {
  id: number
  name: string
  rule_type: string
  conditions: Record<string, any>
  discount_value: string
  discount_type: 'percentage' | 'fixed'
  status: 'active' | 'inactive'
}

// 营位详情
export interface CampsiteDetail {
  id: number
  name: string
  type: CampsiteType
  status: CampsiteStatus
  description: string
  base_price: string
  booking_mode: string
  images: Array<{ url: string; type?: string }>
  sort_order: number
  require_identity: boolean
  require_disclaimer: boolean
  identity_mode: string | null
  identity_fields: any
  is_seckill: boolean
  seckill_start_time: string | null
  normal_payment_timeout: number
  seckill_payment_timeout: number
  refund_deadline_type: string
  refund_deadline_value: number
  require_camping_ticket: boolean
  created_at: string | null
  updated_at: string | null
  ext_camping: CampsiteExtension | null
  pricing_rules: CampsitePricingRule[]
  discount_rules: CampsiteDiscountRule[]
}

// 创建营位请求
export interface CampsiteCreateRequest {
  name: string
  type: CampsiteType
  description?: string
  base_price: number
  booking_mode?: string
  images?: Array<{ url: string; type?: string }>
  sort_order?: number
  require_identity?: boolean
  require_disclaimer?: boolean
  identity_mode?: string
  is_seckill?: boolean
  seckill_start_time?: string
  normal_payment_timeout?: number
  seckill_payment_timeout?: number
  refund_deadline_type?: string
  refund_deadline_value?: number
  status?: CampsiteStatus
  ext_camping?: Partial<CampsiteExtension>
}

// 搜索参数
export interface CampsiteSearchParams extends PaginationParams {
  keyword?: string
  campsite_type?: CampsiteType
  area?: string
  status?: CampsiteStatus
  has_electricity?: boolean
  has_platform?: boolean
}

// 库存项
export interface CampsiteInventoryItem {
  id: number
  date: string
  total_stock: number
  locked_stock: number
  sold_stock: number
  available: number
  status: 'open' | 'closed'
}

// 统计概览
export interface CampsiteTypeStats {
  total: number
  on_sale: number
  off_sale: number
  draft: number
}

export interface CampsiteStatsOverview {
  total_campsites: number
  on_sale: number
  type_stats: {
    daily_camping: CampsiteTypeStats
    event_camping: CampsiteTypeStats
  }
  today_inventory: {
    total: number
    available: number
    sold: number
    occupancy_rate: number
  }
}
