import { get, post, put } from '@/utils/request'
import type {
  InventoryPool,
  InventoryBatchPayload,
  InventoryBatchResponse,
  InventoryCalendarQuery,
  InventoryCalendarResponse,
  InventoryPoolAdjustPayload,
  InventoryPoolAdjustResponse,
  InventoryPoolBinding,
  InventoryPoolBindingPayload,
  InventoryPoolListResponse,
  InventoryPoolPayload,
  InventoryPoolSearchParams,
} from '@/types/inventory-pool'

function confirmHeaders(confirmToken: string) {
  return { headers: { 'X-Confirm-Token': confirmToken } }
}

function serializeArrayParams(params: Record<string, unknown>) {
  const search = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach(item => {
        if (item !== undefined && item !== null && item !== '') {
          search.append(key, String(item))
        }
      })
      return
    }
    search.append(key, String(value))
  })
  return search.toString()
}

export function getInventoryPools(params: InventoryPoolSearchParams) {
  return get<{ data: InventoryPoolListResponse }>('/admin/inventory-pools', params)
}

export function createInventoryPool(data: InventoryPoolPayload, confirmToken: string) {
  return post<{ data: InventoryPool }>('/admin/inventory-pools', data, confirmHeaders(confirmToken))
}

export function updateInventoryPool(id: number, data: Partial<InventoryPoolPayload>, confirmToken: string) {
  return put<{ data: InventoryPool }>(`/admin/inventory-pools/${id}`, data, confirmHeaders(confirmToken))
}

export function getInventoryPoolBindings(poolId: number) {
  return get<{ data: InventoryPoolBinding[] }>(`/admin/inventory-pools/${poolId}/bindings`)
}

export function createInventoryPoolBinding(poolId: number, data: InventoryPoolBindingPayload, confirmToken: string) {
  return post<{ data: InventoryPoolBinding }>(`/admin/inventory-pools/${poolId}/bindings`, data, confirmHeaders(confirmToken))
}

export function updateInventoryPoolBinding(bindingId: number, data: Partial<InventoryPoolBindingPayload>, confirmToken: string) {
  return put<{ data: InventoryPoolBinding }>(`/admin/inventory-pool-bindings/${bindingId}`, data, confirmHeaders(confirmToken))
}

export function getInventoryCalendar(params: InventoryCalendarQuery) {
  return get<{ data: InventoryCalendarResponse }>('/admin/inventory/calendar', params, {
    paramsSerializer: { serialize: serializeArrayParams },
  })
}

export function batchUpdateInventoryCalendar(data: InventoryBatchPayload, confirmToken: string) {
  return post<{ data: InventoryBatchResponse }>('/admin/inventory/batch-upsert', data, confirmHeaders(confirmToken))
}

export function adjustInventoryPool(id: number, data: InventoryPoolAdjustPayload, confirmToken: string) {
  return post<{ data: InventoryPoolAdjustResponse }>(`/admin/inventory-pools/${id}/adjust`, data, confirmHeaders(confirmToken))
}
