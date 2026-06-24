/**
 * 二维码来源归因与 tabBar 分类参数缓存
 */

import { getStorage, removeStorage, setStorage } from '@/utils/storage'
import type { QrcodeAttribution, QrcodeResolveResponse } from '@/types/qrcode'

const QRCODE_ATTRIBUTION_KEY = 'qrcode_attribution'
const PENDING_CATEGORY_KEY = 'pending_category_key'
const DEFAULT_ATTRIBUTION_TTL_SECONDS = 86400

export function saveQrcodeAttribution(data: QrcodeResolveResponse): void {
  setStorage<QrcodeAttribution>(
    QRCODE_ATTRIBUTION_KEY,
    {
      source_qrcode_id: data.qr_code_id,
      source_channel: data.channel,
      source_scanned_at: new Date().toISOString(),
      target_type: data.target_type,
      target_key: data.target_key,
    },
    data.attribution_ttl_seconds || DEFAULT_ATTRIBUTION_TTL_SECONDS,
  )
}

export function getQrcodeAttribution(): QrcodeAttribution | null {
  return getStorage<QrcodeAttribution>(QRCODE_ATTRIBUTION_KEY)
}

export function clearQrcodeAttribution(): void {
  removeStorage(QRCODE_ATTRIBUTION_KEY)
}

export function savePendingCategoryKey(categoryKey: string): void {
  setStorage(PENDING_CATEGORY_KEY, categoryKey, 300)
}

export function consumePendingCategoryKey(): string | null {
  const categoryKey = getStorage<string>(PENDING_CATEGORY_KEY)
  removeStorage(PENDING_CATEGORY_KEY)
  return categoryKey
}

export function appendAttributionPayload(payload: Record<string, unknown>): void {
  const attribution = getQrcodeAttribution()
  if (!attribution) return
  payload.source_qrcode_id = attribution.source_qrcode_id
  payload.source_channel = attribution.source_channel
  payload.source_scanned_at = attribution.source_scanned_at
}
