/**
 * 小程序码解析与归因类型
 */

export type QrcodeTargetType =
  | 'category'
  | 'product'
  | 'activity_product'
  | 'activity_page'
  | 'custom_page'

export interface QrcodeResolveResponse {
  qr_code_id: number
  target_type: QrcodeTargetType
  target_key: string
  title: string
  path: string
  channel: string
  status: 'active' | 'inactive'
  attribution_ttl_seconds: number
}

export interface QrcodeAttribution {
  source_qrcode_id: number
  source_channel: string
  source_scanned_at: string
  target_type: QrcodeTargetType
  target_key: string
}
