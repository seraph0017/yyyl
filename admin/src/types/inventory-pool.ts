import type { PaginationParams } from '@/types'

export type InventoryPoolStatus = 'active' | 'inactive'
export type InventoryPoolType = 'generic' | 'campsite' | 'activity' | 'rental' | 'bundle'
export type InventoryPoolBindingStatus = 'active' | 'inactive'
export type InventoryPoolBindingTargetType = 'product' | 'sku' | 'unsupported'
export type InventorySource = 'inventory' | 'inventory_pool'
export type InventoryCalendarSourceFilter = 'all' | InventorySource
export type InventoryBatchMode = 'set_total' | 'adjust_total' | 'open' | 'close'
export type InventoryPoolAdjustMode = 'set_total' | 'adjust_total' | 'set_status'

export interface InventoryPool {
  id: number
  site_id: number
  pool_code: string
  name: string
  pool_type: InventoryPoolType
  total: number
  available: number
  locked: number
  sold: number
  binding_count: number
  status: InventoryPoolStatus
  created_at?: string
  updated_at?: string
}

export interface InventoryPoolListResponse {
  items: InventoryPool[]
  total: number
  page: number
  page_size: number
}

export interface InventoryPoolSearchParams extends PaginationParams {
  keyword?: string
  status?: InventoryPoolStatus
}

export interface InventoryPoolPayload {
  pool_code?: string
  name: string
  pool_type: InventoryPoolType
  total?: number
  available?: number
  locked?: number
  sold?: number
  status: InventoryPoolStatus
}

export interface InventoryPoolBinding {
  id: number
  inventory_pool_id: number
  site_id: number
  product_id?: number | null
  sku_id?: number | null
  activity_session_id?: number | null
  rental_asset_id?: number | null
  target_type: InventoryPoolBindingTargetType
  target_id?: number | null
  target_name?: string | null
  priority: number
  status: InventoryPoolBindingStatus
  created_at?: string
  updated_at?: string
}

export interface InventoryPoolBindingPayload {
  product_id?: number | null
  sku_id?: number | null
  priority: number
  status: InventoryPoolBindingStatus
}

export interface InventoryCalendarQuery {
  date_start: string
  date_end: string
  product_ids?: number[]
  product_type?: string
  sku_ids?: number[]
  time_slot?: string
  inventory_source?: InventoryCalendarSourceFilter
  include_missing?: boolean
}

export interface InventoryCalendarRow {
  product_id: number
  product_name: string
  sku_id?: number | null
  sku_code?: string | null
  sku_name?: string | null
  time_slot?: string | null
  inventory_source: InventorySource
  inventory_pool_id?: number | null
  inventory_pool_code?: string | null
  inventory_pool_name?: string | null
}

export interface InventoryCalendarCell {
  date: string
  date_type: string
  product_id: number
  product_name: string
  sku_id?: number | null
  sku_code?: string | null
  sku_name?: string | null
  time_slot?: string | null
  price: number
  inventory_source: InventorySource
  inventory_id?: number | null
  inventory_pool_id?: number | null
  inventory_pool_code?: string | null
  inventory_pool_name?: string | null
  total: number
  available: number
  locked: number
  sold: number
  status: 'open' | 'closed'
  editable: boolean
  edit_reason?: string | null
}

export interface InventoryCalendarResponse {
  date_start: string
  date_end: string
  rows: InventoryCalendarRow[]
  cells: InventoryCalendarCell[]
}

export interface InventoryBatchPayload {
  product_ids?: number[]
  sku_ids?: number[]
  date_start?: string
  date_end?: string
  dates?: string[]
  weekdays?: number[]
  time_slot?: string | null
  mode: InventoryBatchMode
  total?: number
  delta?: number
  status?: 'open' | 'closed'
  create_missing?: boolean
  remark?: string
}

export interface InventoryBatchResponse {
  matched_count: number
  created_count: number
  updated_count: number
  skipped_count: number
  errors: Array<{ product_id: number; sku_id?: number | null; date: string; message: string }>
}

export interface InventoryPoolAdjustPayload {
  mode: InventoryPoolAdjustMode
  total?: number
  delta?: number
  status?: InventoryPoolStatus
  remark?: string
}

export interface InventoryPoolAdjustResponse {
  pool: InventoryPool
  before: Pick<InventoryPool, 'total' | 'available' | 'locked' | 'sold' | 'status'>
  after: Pick<InventoryPool, 'total' | 'available' | 'locked' | 'sold' | 'status'>
}
