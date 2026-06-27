import { del, get, post, put } from '@/utils/request'
import type {
  CustomerServiceAskLogResponse,
  CustomerServiceAskLogSearchParams,
  CustomerServiceAskResult,
  CustomerServiceKnowledgeArticle,
  CustomerServiceKnowledgePayload,
  CustomerServiceKnowledgeResponse,
  CustomerServiceKnowledgeSearchParams,
} from '@/types/customer-service-ai'

export function getKnowledgeArticles(params: CustomerServiceKnowledgeSearchParams) {
  return get<{ data: CustomerServiceKnowledgeResponse }>('/admin/customer-service/knowledge', params)
}

export function createKnowledgeArticle(data: CustomerServiceKnowledgePayload) {
  return post<{ data: CustomerServiceKnowledgeArticle }>('/admin/customer-service/knowledge', data)
}

export function updateKnowledgeArticle(id: number, data: Partial<CustomerServiceKnowledgePayload>) {
  return put<{ data: CustomerServiceKnowledgeArticle }>(`/admin/customer-service/knowledge/${id}`, data)
}

export function deleteKnowledgeArticle(id: number) {
  return del(`/admin/customer-service/knowledge/${id}`)
}

export function uploadKnowledgeFile(file: File, data: { title?: string; status?: string } = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (data.title) formData.append('title', data.title)
  if (data.status) formData.append('status', data.status)
  return post<{ data: CustomerServiceKnowledgeArticle }>('/admin/customer-service/knowledge/upload', formData, {
    headers: { 'Content-Type': undefined },
  })
}

export function askCustomerServiceKnowledge(question: string) {
  return post<{ data: CustomerServiceAskResult }>('/admin/customer-service/ask', { question })
}

export function getCustomerServiceAskLogs(params: CustomerServiceAskLogSearchParams) {
  return get<{ data: CustomerServiceAskLogResponse }>('/admin/customer-service/ask-logs', params)
}
