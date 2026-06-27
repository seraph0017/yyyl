import type { PaginatedResponse, PaginationParams } from '@/types'

export type EnterpriseWechatRobotStatus = 'active' | 'inactive'
export type EnterpriseWechatRobotSendStatus = 'success' | 'failed'

export interface EnterpriseWechatRobot {
  id: number
  site_id: number
  name: string
  has_webhook_url: boolean
  has_secret: boolean
  status: EnterpriseWechatRobotStatus
  created_by?: number | null
  updated_by?: number | null
  created_at?: string
  updated_at?: string
}

export interface EnterpriseWechatRobotPayload {
  name: string
  webhook_url?: string
  secret?: string
  status: EnterpriseWechatRobotStatus
}

export interface EnterpriseWechatRobotTestPayload {
  content: string
  mentioned_mobile_list?: string[]
}

export interface EnterpriseWechatRobotTestResult {
  log_id: number
}

export interface EnterpriseWechatKnowledgeAskPayload {
  question: string
  mentioned_mobile_list?: string[]
}

export interface EnterpriseWechatKnowledgeAskResult {
  answer: string
  sources: Array<{
    id: number
    title: string
    source_type: string
    source_name?: string | null
  }>
  matched_article_ids: number[]
  confidence: number
  needs_human: boolean
  ask_log_id: number
  robot_log_id: number
}

export interface EnterpriseWechatRobotLog {
  id: number
  robot_config_id: number
  site_id: number
  message_type: string
  request_payload: Record<string, any>
  response_code?: number | null
  response_body?: Record<string, any> | null
  send_status: EnterpriseWechatRobotSendStatus
  error_message?: string | null
  created_at: string
}

export interface EnterpriseWechatRobotLogSearchParams extends PaginationParams {
  send_status?: EnterpriseWechatRobotSendStatus
}

export type EnterpriseWechatRobotLogResponse = PaginatedResponse<EnterpriseWechatRobotLog>
