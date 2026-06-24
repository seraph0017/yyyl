import { get, patch, post } from '@/utils/request'
import type { PaginatedResponse } from '@/types'
import type { Qrcode, QrcodeCreateRequest, QrcodeSearchParams } from '@/types/qrcode'

export function getQrcodes(params: QrcodeSearchParams) {
  return get<{ data: PaginatedResponse<Qrcode> }>('/admin/qrcodes', params)
}

export function createQrcode(data: QrcodeCreateRequest) {
  return post<{ data: Qrcode }>('/admin/qrcodes', data)
}

export function updateQrcodeStatus(id: number, status: 'active' | 'inactive') {
  return patch<{ data: Qrcode }>(`/admin/qrcodes/${id}/status`, { status })
}

export function regenerateQrcode(id: number) {
  return post<{ data: Qrcode }>(`/admin/qrcodes/${id}/regenerate`)
}

export function createCmsPageQrcode(pageId: number) {
  return post<{ data: Qrcode }>(`/admin/cms/pages/${pageId}/qrcode`)
}

export function downloadQrcode(id: number) {
  return get(`/admin/qrcodes/${id}/download`, undefined, { responseType: 'blob' })
}
