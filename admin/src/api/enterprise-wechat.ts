import { get, post, put } from '@/utils/request'
import type {
  EnterpriseWechatRobot,
  EnterpriseWechatRobotLogResponse,
  EnterpriseWechatRobotLogSearchParams,
  EnterpriseWechatRobotPayload,
  EnterpriseWechatKnowledgeAskPayload,
  EnterpriseWechatKnowledgeAskResult,
  EnterpriseWechatRobotTestPayload,
  EnterpriseWechatRobotTestResult,
} from '@/types/enterprise-wechat'

function confirmHeaders(confirmToken: string) {
  return { headers: { 'X-Confirm-Token': confirmToken } }
}

export function getEnterpriseWechatRobots() {
  return get<{ data: EnterpriseWechatRobot[] }>('/admin/enterprise-wechat/robots')
}

export function createEnterpriseWechatRobot(data: EnterpriseWechatRobotPayload, confirmToken: string) {
  return post<{ data: EnterpriseWechatRobot }>('/admin/enterprise-wechat/robots', data, confirmHeaders(confirmToken))
}

export function updateEnterpriseWechatRobot(id: number, data: Partial<EnterpriseWechatRobotPayload>, confirmToken: string) {
  return put<{ data: EnterpriseWechatRobot }>(`/admin/enterprise-wechat/robots/${id}`, data, confirmHeaders(confirmToken))
}

export function testSendEnterpriseWechatRobot(id: number, data: EnterpriseWechatRobotTestPayload, confirmToken: string) {
  return post<{ data: EnterpriseWechatRobotTestResult }>(`/admin/enterprise-wechat/robots/${id}/test-send`, data, confirmHeaders(confirmToken))
}

export function askSendEnterpriseWechatRobotKnowledge(id: number, data: EnterpriseWechatKnowledgeAskPayload, confirmToken: string) {
  return post<{ data: EnterpriseWechatKnowledgeAskResult }>(`/admin/enterprise-wechat/robots/${id}/knowledge-ask-send`, data, confirmHeaders(confirmToken))
}

export function getEnterpriseWechatRobotLogs(id: number, params: EnterpriseWechatRobotLogSearchParams) {
  return get<{ data: EnterpriseWechatRobotLogResponse }>(`/admin/enterprise-wechat/robots/${id}/logs`, params)
}
