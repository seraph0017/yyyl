import { get, post, put } from '@/utils/request'
import type { Order, OrderSearchParams, PaginatedResponse } from '@/types'

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

// 退票审批队列
export function getRefundQueue(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<Order> }>('/admin/orders', { ...params, status: 'refunding' })
}
