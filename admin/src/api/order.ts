import { get, post, put } from '@/utils/request'
import type {
  Order,
  OrderSearchParams,
  PaginatedResponse,
  RefundCreatePayload,
  RefundRecord,
  TemporaryOrderCodePayResult,
  TemporaryOrderCreatePayload,
  TemporaryOrderCreateResult,
} from '@/types'
import type { OrderExportTask } from '@/types/order-export'

type OrderExportPayload = { filters: Record<string, any>; file_format: 'csv' | 'xlsx'; include_sensitive: boolean }

function confirmHeaders(confirmToken?: string) {
  return confirmToken ? { headers: { 'X-Confirm-Token': confirmToken } } : undefined
}

export function getOrders(params: OrderSearchParams) {
  return get<{ data: PaginatedResponse<Order> }>('/admin/orders', params)
}

export function getOrderDetail(id: number) {
  return get<{ data: Order }>(`/admin/orders/${id}`)
}

export function approveRefund(orderId: number, data: { approved: boolean; reason?: string }) {
  return post(`/admin/orders/${orderId}/refund/approve`, data)
}

export function partialRefund(orderId: number, data: { item_ids: number[]; reason: string }) {
  return post(`/admin/orders/${orderId}/partial-refund`, data)
}

export function getOrderItems(orderId: number) {
  return get(`/orders/${orderId}/items`)
}

export function createTemporaryOrder(data: TemporaryOrderCreatePayload) {
  return post<{ data: TemporaryOrderCreateResult }>('/admin/orders/temporary', data)
}

export function queryTemporaryCodePay(sessionId: number) {
  return post<{ data: TemporaryOrderCodePayResult }>(`/admin/orders/temporary/${sessionId}/query-codepay`, {})
}

export function createOrderExport(data: OrderExportPayload, confirmToken?: string) {
  return post<{ data: OrderExportTask }>('/admin/orders/export', data, confirmHeaders(confirmToken))
}

export function getOrderExportTasks(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<OrderExportTask> }>('/admin/orders/export-tasks', params)
}

export function downloadOrderExportTask(taskId: number) {
  return get(`/admin/orders/export-tasks/${taskId}/download`, undefined, { responseType: 'blob' })
}

export function settleOrder(orderId: number) {
  return post(`/admin/orders/${orderId}/settle`, {})
}

export function createRefund(orderId: number, data: RefundCreatePayload) {
  return post<{ data: RefundRecord }>(`/admin/orders/${orderId}/refunds`, data)
}

export function getOrderRefunds(orderId: number) {
  return get<{ data: RefundRecord[] }>(`/admin/orders/${orderId}/refunds`)
}

export function approveRefundRecord(refundId: number) {
  return post<{ data: RefundRecord }>(`/admin/refunds/${refundId}/approve`, {})
}

export function rejectRefundRecord(refundId: number, reason: string) {
  return post<{ data: RefundRecord }>(`/admin/refunds/${refundId}/reject`, { reason })
}

// 退票审批队列
export function getRefundQueue(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<RefundRecord> }>('/admin/refunds', { ...params, status: 'pending' })
}
