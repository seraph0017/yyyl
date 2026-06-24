/**
 * 小程序码解析 API
 */

import { get } from '@/utils/request'
import type { QrcodeResolveResponse } from '@/types/qrcode'

export function resolveQrcode(scene: string) {
  return get<QrcodeResolveResponse>(
    '/qrcodes/resolve',
    { scene },
    { needAuth: false, showError: false },
  )
}
