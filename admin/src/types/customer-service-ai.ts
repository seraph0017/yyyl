import type { PaginatedResponse, PaginationParams } from '@/types'

export type CustomerServiceKnowledgeStatus = 'draft' | 'published' | 'archived'
export type CustomerServiceKnowledgeFormat = 'markdown' | 'text'
export type CustomerServiceKnowledgeSourceType = 'manual' | 'faq' | 'txt' | 'md' | 'pdf' | 'docx'
export type CustomerServiceAskChannel = 'miniapp' | 'admin_preview' | 'enterprise_wechat'
export type CustomerServiceFeedback = 'helpful' | 'unhelpful'

export interface CustomerServiceKnowledgeArticle {
  id: number
  site_id: number
  title: string
  content: string
  content_format: CustomerServiceKnowledgeFormat
  source_type: CustomerServiceKnowledgeSourceType
  source_name?: string | null
  keywords: string[]
  status: CustomerServiceKnowledgeStatus
  published_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface CustomerServiceKnowledgePayload {
  title: string
  content: string
  content_format: CustomerServiceKnowledgeFormat
  source_type: CustomerServiceKnowledgeSourceType
  source_name?: string | null
  keywords: string[]
  status: CustomerServiceKnowledgeStatus
}

export interface CustomerServiceKnowledgeSearchParams extends PaginationParams {
  keyword?: string
  status?: CustomerServiceKnowledgeStatus
}

export interface CustomerServiceKnowledgeSource {
  id: number
  title: string
  source_type: CustomerServiceKnowledgeSourceType
  source_name?: string | null
}

export interface CustomerServiceAskResult {
  answer: string
  sources: CustomerServiceKnowledgeSource[]
  matched_article_ids: number[]
  confidence: number
  needs_human: boolean
  log_id: number
}

export interface CustomerServiceAskLog {
  id: number
  site_id: number
  channel: CustomerServiceAskChannel
  user_id?: number | null
  admin_id?: number | null
  question: string
  answer: string
  matched_article_ids: number[]
  source_refs: CustomerServiceKnowledgeSource[]
  confidence: number
  needs_human: boolean
  feedback?: CustomerServiceFeedback | null
  feedback_comment?: string | null
  created_at: string
}

export interface CustomerServiceAskLogSearchParams extends PaginationParams {
  channel?: CustomerServiceAskChannel
  needs_human?: boolean
}

export type CustomerServiceKnowledgeResponse = PaginatedResponse<CustomerServiceKnowledgeArticle>
export type CustomerServiceAskLogResponse = PaginatedResponse<CustomerServiceAskLog>
