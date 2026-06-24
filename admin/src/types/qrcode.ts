import type { PaginationParams } from '@/types'

export type QrcodeTargetType = 'category' | 'product' | 'activity_product' | 'activity_page' | 'custom_page'
export type QrcodeStatus = 'active' | 'inactive'

export interface Qrcode {
  id: number
  site_id: number
  target_type: QrcodeTargetType
  target_key: string
  title: string
  path: string
  scene: string
  short_code: string
  channel: string
  image_url?: string | null
  status: QrcodeStatus
  generated_by?: number | null
  generated_at?: string | null
  last_used_at?: string | null
  usage_count: number
  created_at: string
  updated_at: string
}

export interface QrcodeCreateRequest {
  target_type: QrcodeTargetType
  target_key: string
  title: string
  channel?: string
}

export interface QrcodeSearchParams extends PaginationParams {
  target_type?: QrcodeTargetType
  channel?: string
  status?: QrcodeStatus
}
