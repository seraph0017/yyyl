import { ElMessageBox } from 'element-plus'
import { post } from '@/utils/request'

interface ConfirmResponse {
  data: {
    confirm_token: string
    action: string
    verified: boolean
  }
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value)
  }
  if (Array.isArray(value)) {
    return `[${value.map(item => stableStringify(item)).join(',')}]`
  }
  const record = value as Record<string, unknown>
  const keys = Object.keys(record).sort()
  return `{${keys
    .map(key => `${JSON.stringify(key)}:${stableStringify(record[key])}`)
    .join(',')}}`
}

function normalizeJsonPayload(value: unknown): unknown {
  return JSON.parse(JSON.stringify(value ?? {}) || '{}')
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
  return Array.from(new Uint8Array(digest))
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('')
}

export async function requestHighRiskConfirm(
  action: string,
  message: string,
  payload?: unknown,
): Promise<string> {
  const password = await ElMessageBox.prompt(message, '高风险操作确认', {
    confirmButtonText: '确认执行',
    cancelButtonText: '取消',
    inputType: 'password',
    inputPlaceholder: '请输入超级管理员操作密码',
    inputPattern: /^.{1,}$/,
    inputErrorMessage: '请输入操作密码',
    type: 'warning',
  })

  const request_hash = await sha256Hex(stableStringify(normalizeJsonPayload(payload)))
  const res = await post<ConfirmResponse>('/admin/confirm/verify-password', {
    password: password.value,
    action,
    request_hash,
  })
  return res.data.confirm_token
}
