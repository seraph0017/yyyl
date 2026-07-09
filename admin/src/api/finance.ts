import { get, post } from '@/utils/request'
import type {
  FinanceOverview,
  FinanceSettlement,
  FinanceTransaction,
  PaginatedResponse,
  SettlementSearchParams,
  TransactionSearchParams,
} from '@/types'

function withConfirmToken(confirmToken?: string) {
  return confirmToken ? { headers: { 'X-Confirm-Token': confirmToken } } : undefined
}

export function getFinanceOverview() {
  return get<{ data: FinanceOverview }>('/admin/finance/overview')
}

export function getTransactions(params: TransactionSearchParams) {
  return get<{ data: PaginatedResponse<FinanceTransaction> }>('/admin/finance/transactions', params)
}

export function processWithdraw(data: { amount: number; bank_account?: string; remark?: string }, confirmToken?: string) {
  return post('/admin/finance/withdraw', data, withConfirmToken(confirmToken))
}

export function getDepositRecords(params?: { page?: number; page_size?: number }) {
  return get<{ data: PaginatedResponse<any> }>('/admin/finance/deposits', params)
}

export function refundDeposit(depositId: number, data: { return_amount: number; remark?: string }, confirmToken?: string) {
  return post(`/admin/finance/deposits/${depositId}/refund`, data, withConfirmToken(confirmToken))
}

export function getSettlements(params: SettlementSearchParams) {
  return get<{ data: PaginatedResponse<FinanceSettlement> }>('/admin/finance/settlements', params)
}
