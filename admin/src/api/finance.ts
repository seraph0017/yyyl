import { get, post } from '@/utils/request'
import type { FinanceOverview, FinanceTransaction, TransactionSearchParams, PaginatedResponse } from '@/types'

export function getFinanceOverview() {
  return get<{ data: FinanceOverview }>('/admin/finance/overview')
}

export function getTransactions(params: TransactionSearchParams) {
  return get<{ data: PaginatedResponse<FinanceTransaction> }>('/admin/finance/transactions', params)
}

export function processWithdraw(data: { amount: number; account_info: string }) {
  return post('/admin/finance/withdraw', data)
}

export function getDepositRecords(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<any> }>('/admin/finance/deposits', params)
}

export function refundDeposit(depositId: number, data: { amount: number; reason: string }) {
  return post(`/admin/finance/deposits/${depositId}/refund`, data)
}
