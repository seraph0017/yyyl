// 报销管理 API
import { get, post, put } from '@/utils/request'
import type { ExpenseType, ExpenseRequest, ExpenseStats } from '@/types'

// 报销类型
export function getExpenseTypes() {
  return get<{ code: number; data: ExpenseType[] }>('/admin/expense-types')
}

export function createExpenseType(data: { name: string; description?: string; sort_order?: number }) {
  return post('/admin/expense-types', data)
}

export function updateExpenseType(id: number, data: Partial<ExpenseType>) {
  return put(`/admin/expense-types/${id}`, data)
}

// 报销单
export function getExpenses(params: object) {
  return get<{ code: number; data: { list: ExpenseRequest[]; pagination: { total: number } } }>('/admin/expenses', params)
}

export function getExpenseDetail(id: number) {
  return get<{ code: number; data: ExpenseRequest }>(`/admin/expenses/${id}`)
}

export function createExpense(data: object) {
  return post<{ code: number; data: ExpenseRequest }>('/admin/expenses', data)
}

export function approveExpense(id: number, data: { approved: boolean; review_remark?: string }) {
  return post(`/admin/expenses/${id}/approve`, data)
}

export function markExpensePaid(id: number) {
  return post(`/admin/expenses/${id}/mark-paid`)
}

export function getExpenseStats(params?: object) {
  return get<{ code: number; data: ExpenseStats }>('/admin/expenses/stats', params)
}
