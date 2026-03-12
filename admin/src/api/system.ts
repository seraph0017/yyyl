import { get, post, put, del } from '@/utils/request'
import type {
  StaffMember, Permission, OperationLog, OperationLogSearchParams,
  FaqCategory, FaqItem, PageConfig, NotificationTemplate,
  NotificationRecord, NotificationStats, SalesReportParams, SalesReportData, PaginatedResponse
} from '@/types'

// 员工管理
export function getStaffList(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<StaffMember> }>('/admin/staff', params)
}

export function createStaff(data: { phone: string; real_name: string; role_id: number; password?: string }) {
  return post('/admin/staff', data)
}

export function updateStaff(id: number, data: Partial<StaffMember & { role_id: number }>) {
  return put(`/admin/staff/${id}`, data)
}

export function deleteStaff(id: number) {
  return del(`/admin/staff/${id}`)
}

// 角色与权限
export function getRoles() {
  return get<{ data: any[] }>('/admin/roles')
}

export function getRolePermissions(roleId: number) {
  return get<{ data: Permission[] }>(`/admin/roles/${roleId}/permissions`)
}

export function updateRolePermissions(roleId: number, data: { permission_ids: number[] }) {
  return put(`/admin/roles/${roleId}/permissions`, data)
}

// 操作日志
export function getOperationLogs(params: OperationLogSearchParams) {
  return get<{ data: PaginatedResponse<OperationLog> }>('/admin/operation-logs', params)
}

export function getOperationLogDetail(id: number) {
  return get<{ data: OperationLog }>(`/admin/operation-logs/${id}`)
}

// FAQ管理
export function getFaqCategories() {
  return get<{ data: FaqCategory[] }>('/admin/faq/categories')
}

export function createFaqCategory(data: Partial<FaqCategory>) {
  return post('/admin/faq/categories', data)
}

export function updateFaqCategory(id: number, data: Partial<FaqCategory>) {
  return put(`/admin/faq/categories/${id}`, data)
}

export function deleteFaqCategory(id: number) {
  return del(`/admin/faq/categories/${id}`)
}

export function getFaqItems(params?: { page?: number; page_size?: number; category_id?: number }) {
  return get<{ data: PaginatedResponse<FaqItem> }>('/admin/faq/items', params)
}

export function createFaqItem(data: Partial<FaqItem>) {
  return post('/admin/faq/items', data)
}

export function updateFaqItem(id: number, data: Partial<FaqItem>) {
  return put(`/admin/faq/items/${id}`, data)
}

export function deleteFaqItem(id: number) {
  return del(`/admin/faq/items/${id}`)
}

// 客服配置
export function updateCustomerServiceConfig(data: { phone: string; wechat: string; work_hours: string }) {
  return put('/admin/customer-service/config', data)
}

// 页面配置
export function getPageConfigs() {
  return get<{ data: PageConfig[] }>('/admin/page-configs')
}

export function getPageConfig(pageKey: string) {
  return get<{ data: PageConfig }>(`/admin/page-configs/${pageKey}`)
}

export function updatePageConfig(pageKey: string, data: Record<string, any>) {
  return put(`/admin/page-configs/${pageKey}`, data)
}

// 系统设置
export function getSettings() {
  return get<{ data: Record<string, any> }>('/admin/settings')
}

export function updateSettings(data: Record<string, any>) {
  return put('/admin/settings', data)
}

// 免责声明
export function getDisclaimerTemplates() {
  return get<{ data: any[] }>('/admin/disclaimer-templates')
}

export function updateDisclaimerTemplate(id: number, data: { content: string }) {
  return put(`/admin/disclaimer-templates/${id}`, data)
}

// 通知管理
export function getNotificationTemplates() {
  return get<{ data: NotificationTemplate[] }>('/admin/notifications/templates')
}

export function updateNotificationTemplate(id: number, data: Partial<NotificationTemplate>) {
  return put(`/admin/notifications/templates/${id}`, data)
}

export function getNotificationRecords(params?: { page?: number; page_size?: number; template_key?: string; status?: string }) {
  return get<{ data: PaginatedResponse<NotificationRecord> }>('/admin/notifications/records', params)
}

export function getNotificationStats() {
  return get<{ data: NotificationStats }>('/admin/notifications/stats')
}

// 数据报表
export function getSalesReport(params: SalesReportParams) {
  return get<{ data: SalesReportData }>('/admin/reports/sales', params)
}

export function getUserReport(params: { start_date: string; end_date: string }) {
  return get<{ data: any }>('/admin/reports/users', params)
}

export function getProductReport(params: { start_date: string; end_date: string; sort_by?: string; category?: string }) {
  return get<{ data: any }>('/admin/reports/products', params)
}

export function exportReport(data: { type: string; params: Record<string, any> }) {
  return post('/admin/reports/export', data, { responseType: 'blob' })
}

// 二次确认
export function verifyConfirmCode(data: { action: string; code: string }) {
  return post('/admin/confirm/verify-code', data)
}

export function verifyOperationPassword(data: { action: string; password: string }) {
  return post('/admin/confirm/verify-password', data)
}
