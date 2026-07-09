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

export function getEnterpriseWechatRobots() {
  return get<{ data: EnterpriseWechatRobot[] }>('/admin/enterprise-wechat/robots')
}

export function createEnterpriseWechatRobot(data: EnterpriseWechatRobotPayload) {
  return post<{ data: EnterpriseWechatRobot }>('/admin/enterprise-wechat/robots', data)
}

export function updateEnterpriseWechatRobot(id: number, data: Partial<EnterpriseWechatRobotPayload>) {
  return put<{ data: EnterpriseWechatRobot }>(`/admin/enterprise-wechat/robots/${id}`, data)
}

export function testSendEnterpriseWechatRobot(id: number, data: EnterpriseWechatRobotTestPayload) {
  return post<{ data: EnterpriseWechatRobotTestResult }>(`/admin/enterprise-wechat/robots/${id}/test-send`, data)
}

export function askSendEnterpriseWechatRobotKnowledge(id: number, data: EnterpriseWechatKnowledgeAskPayload) {
  return post<{ data: EnterpriseWechatKnowledgeAskResult }>(`/admin/enterprise-wechat/robots/${id}/knowledge-ask-send`, data)
}

export function getEnterpriseWechatRobotLogs(id: number, params: EnterpriseWechatRobotLogSearchParams) {
  return get<{ data: EnterpriseWechatRobotLogResponse }>(`/admin/enterprise-wechat/robots/${id}/logs`, params)
}
