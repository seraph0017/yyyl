import { get, post, put, del } from '@/utils/request'
import type { PaginatedResponse } from '@/types'
import type {
  CmsPage, CmsPageVersion, CmsComponentDef, CmsAsset,
  CmsConfig, PreviewInfo
} from '@/types/cms'

// ==================== 页面管理 ====================

export function getCmsPages(params: { page?: number; page_size?: number; page_type?: string }) {
  return get<{ data: PaginatedResponse<CmsPage> }>('/admin/cms/pages', params)
}

export function getCmsPageDetail(id: number) {
  return get<{ data: CmsPage }>(`/admin/cms/pages/${id}`)
}

export function createCmsPage(data: {
  page_code: string; page_type: string; title: string; description?: string; status?: string
}) {
  return post<{ data: CmsPage }>('/admin/cms/pages', data)
}

export function updateCmsPage(id: number, data: Partial<CmsPage>) {
  return put<{ data: CmsPage }>(`/admin/cms/pages/${id}`, data)
}

export function deleteCmsPage(id: number) {
  return del(`/admin/cms/pages/${id}`)
}

// ==================== 草稿 ====================

export function saveCmsDraft(id: number, data: { config: CmsConfig; draft_updated_at?: string }) {
  return put<{ data: CmsPage }>(`/admin/cms/pages/${id}/draft`, data)
}

// ==================== 重置 ====================

export function resetCmsPage(id: number) {
  return post(`/admin/cms/pages/${id}/reset`)
}

// ==================== 发布/回滚 ====================

export function publishCmsPage(id: number, data?: { remark?: string }) {
  return post<{ data: { version_id: number; version_number: number; published_at: string } }>(
    `/admin/cms/pages/${id}/publish`, data || {}
  )
}

export function getCmsVersions(id: number) {
  return get<{ data: CmsPageVersion[] }>(`/admin/cms/pages/${id}/versions`)
}

export function rollbackCmsPage(id: number, data: { version_id: number }) {
  return post(`/admin/cms/pages/${id}/rollback`, data)
}

// ==================== 预览 ====================

export function createCmsPreview(id: number) {
  return post<{ data: PreviewInfo }>(`/admin/cms/pages/${id}/preview`)
}

// ==================== 编辑锁 ====================

export function acquireCmsLock(id: number) {
  return post(`/admin/cms/pages/${id}/lock`)
}

export function releaseCmsLock(id: number) {
  return del(`/admin/cms/pages/${id}/lock`)
}

// ==================== 组件 ====================

export function getCmsComponents() {
  return get<{ data: CmsComponentDef[] }>('/admin/cms/components')
}

export function createCmsComponent(data: {
  component_type: string; name: string; icon?: string; default_config?: Record<string, any>
}) {
  return post<{ data: CmsComponentDef }>('/admin/cms/components', data)
}

// ==================== 素材 ====================

export function getCmsAssets(params: { page?: number; page_size?: number; file_type?: string }) {
  return get<{ data: PaginatedResponse<CmsAsset> }>('/admin/cms/assets', params)
}

export function uploadCmsAsset(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<{ data: CmsAsset }>('/admin/cms/assets/upload', formData)
}

export function deleteCmsAsset(id: number, force?: boolean) {
  return del(`/admin/cms/assets/${id}`, { params: { force } })
}

// ==================== 宣传页（公开） ====================

export function getLandingPage(siteId?: number) {
  return get<{ data: { page_code: string; title: string; version: number; config: CmsConfig; updated_at: string } | null }>(
    '/cms/landing', { site_id: siteId || 1 }
  )
}
