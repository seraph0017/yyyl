import { get, post, put, del } from '@/utils/request'
import type {
  Product, ProductCreateRequest, ProductSearchParams,
  PricingRule, DiscountRule, Inventory, InventoryUpdateRequest, InventoryBatchRequest,
  PaginatedResponse, CalendarQuery, CalendarItem
} from '@/types'

// 商品CRUD
export function getProducts(params: ProductSearchParams) {
  return get<{ data: PaginatedResponse<Product> }>('/admin/products', params)
}

export function getProductDetail(id: number) {
  return get<{ data: Product }>(`/products/${id}`)
}

export function createProduct(data: ProductCreateRequest) {
  return post<{ data: Product }>('/admin/products', data)
}

export function updateProduct(id: number, data: Partial<ProductCreateRequest>) {
  return put<{ data: Product }>(`/admin/products/${id}`, data)
}

export function deleteProduct(id: number) {
  return del(`/admin/products/${id}`)
}

export function updateProductStatus(id: number, status: string) {
  return put(`/admin/products/${id}/status`, { status })
}

// 定价规则
export function getPricingRules(productId: number) {
  return get<{ data: PricingRule[] }>(`/admin/products/${productId}/pricing-rules`)
}

export function createPricingRule(productId: number, data: Partial<PricingRule>) {
  return post(`/admin/products/${productId}/pricing-rules`, data)
}

export function updatePricingRule(productId: number, ruleId: number, data: Partial<PricingRule>) {
  return put(`/admin/products/${productId}/pricing-rules/${ruleId}`, data)
}

export function deletePricingRule(productId: number, ruleId: number) {
  return del(`/admin/products/${productId}/pricing-rules/${ruleId}`)
}

// 优惠规则
export function getDiscountRules(productId: number) {
  return get<{ data: DiscountRule[] }>(`/admin/products/${productId}/discount-rules`)
}

export function createDiscountRule(productId: number, data: Partial<DiscountRule>) {
  return post(`/admin/products/${productId}/discount-rules`, data)
}

export function updateDiscountRule(productId: number, ruleId: number, data: Partial<DiscountRule>) {
  return put(`/admin/products/${productId}/discount-rules/${ruleId}`, data)
}

export function deleteDiscountRule(productId: number, ruleId: number) {
  return del(`/admin/products/${productId}/discount-rules/${ruleId}`)
}

// 库存管理
export function getInventoryList(params: { product_id?: number; start_date?: string; end_date?: string; page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<Inventory> }>('/admin/inventory', params)
}

export function updateInventory(id: number, data: InventoryUpdateRequest) {
  return put(`/admin/inventory/${id}`, data)
}

export function batchOpenInventory(data: InventoryBatchRequest) {
  return post('/admin/inventory/batch-open', data)
}

// 营地日历
export function getCalendarData(params: CalendarQuery) {
  return get<{ data: CalendarItem[] }>('/admin/calendar', params)
}
